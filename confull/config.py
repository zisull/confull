# -*- coding: utf-8 -*-
# @author: zisull@qq.com
# @date: 2024年11月19日

import atexit
import base64 as _b64
import logging
import os
import sys
import threading
import weakref
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional, Tuple, Union

import orjson

from .exceptions import (
    ConfigEncryptionError,
    ConfigError,
    ConfigIOError,
    ConfigKeyError,
    ConfigValidationError,
)
from .formats import Format
from .handlers import ConfigHandlerFactory
from .node import ConfigNode

ENCRYPT_HEADER = b"ZISULLCONFULLENC"
SALT_SIZE = 8  # 保持与 0.1.x 文件格式兼容，改动会让既有加密文件无法解析
PBKDF2_ITERATIONS = 100_000

# logger
logger = logging.getLogger(__name__)

# 需要退出时冲刷的实例。Config 是 Mapping（不可哈希），所以持有弱引用而不是 WeakSet。
_LIVE: list = []
_atexit_registered = False


def _register_for_flush(cfg: "Config") -> None:
    global _atexit_registered
    if len(_LIVE) >= 32:
        _LIVE[:] = [ref for ref in _LIVE if ref() is not None]
    _LIVE.append(weakref.ref(cfg))
    if not _atexit_registered:
        atexit.register(_flush_all)
        _atexit_registered = True


def _flush_all() -> None:
    for ref in _LIVE:
        cfg = ref()
        if cfg is None:
            continue
        try:
            cfg._flush_save()
        except Exception as exc:  # 退出阶段只报告，不抛出
            logger.warning("退出时保存 %s 失败：%s", cfg._file_path, exc)


class Config(ConfigNode):
    """多格式配置管理器，支持 dict <=> [ini, xml, json, toml, yaml] 的读写与自动保存。

    自身就是配置树的根节点（继承 ``ConfigNode``），因此顶层与嵌套层级的访问规则完全一致。
    支持密码加密保护。
    """

    def __init__(
        self,
        file_or_data: Union[str, os.PathLike, Dict[str, Any], None] = None,
        /,
        file: Union[str, os.PathLike, None] = None,
        way: str = "",
        replace: bool = False,
        auto_save: bool = True,
        pwd: Optional[str] = None,
        process_safe: bool = False,
        debounce_ms: int = 0,
        env: Optional[str] = None,
        env_prefix: str = "",
        schema: Optional[Dict[str, type]] = None,
        *,
        data: Optional[Dict[str, Any]] = None,
    ):
        """初始化配置管理器。

        第一个参数可以是文件名也可以是初始 dict，几种写法等价：
        ``Config('app.toml')``、``Config({'a': 1}, file='app.toml')``、
        ``Config('app.toml', data={'a': 1})``。

        :param file: 配置文件名（可无扩展名，可自动创建目录）
        :param way: 配置文件格式（json/toml/yaml/ini/xml）
        :param replace: 是否覆盖已有配置文件
        :param auto_save: 是否自动保存
        :param pwd: 密码字符串，用于加密配置文件
        :param process_safe: 是否进程安全（进程锁，需要 portalocker）
        :param debounce_ms: 自动保存延迟（毫秒），0 表示立即保存
        :param env: 环境名称，会自动合并 app.{env}.toml
        :param env_prefix: 环境变量前缀，会导入 {prefix}_* 覆盖配置
        :param schema: 类型校验，如 {'port': int, 'db.host': str}
        :param data: 初始配置数据（dict）
        """
        if isinstance(file_or_data, (str, os.PathLike, Path)):
            if file is not None:
                raise ConfigValidationError(
                    "文件名传了两次：第一个参数按文件名处理时不能再传 file。"
                    "请写成 Config('app.toml', data={...})。"
                )
            file = file_or_data
        elif file_or_data is not None:
            if data is not None:
                raise ConfigValidationError("初始数据传了两次：第一个参数和 data 只能选一个。")
            data = file_or_data

        self._defer = 0
        self._validating = True
        self._file_path = Path(file) if file is not None else Path("config")
        if way == "":
            ext = self._file_path.suffix.lstrip(".").lower()
            try:
                way = Format.from_str(ext).value
            except ValueError:
                way = "toml"

        self._way = self._validate_format(way)
        self._file_path = self._ensure_extension(self._file_path).resolve()

        self._auto_save = auto_save
        self._debounce_ms = max(0, debounce_ms)
        self._save_timer: Optional[threading.Timer] = None
        self._pwd = pwd
        self._process_safe = process_safe
        self._lock = RLock()
        self._handler = ConfigHandlerFactory.get_handler(self._way)
        self._observer: Optional[Any] = None
        self._schema: Dict[str, type] = dict(schema or {})
        self._salt: Optional[bytes] = None
        self._fernet: Optional[Any] = None
        self._fernet_pwd: Optional[str] = None
        self._dirty = False
        self._last_saved_mtime: Optional[int] = None

        super().__init__(None, manager=self)
        _register_for_flush(self)

        if self._file_path.exists() and not replace:
            self._load()
        else:
            if data is not None:
                if not isinstance(data, dict):
                    raise ConfigValidationError(
                        f"初始数据必须是 dict，实际得到 {type(data).__name__}。"
                    )
                self.set_data(data)
            self._dirty = True
            self.save()

        if env:
            self._load_env_config(env)
        if env_prefix:
            self.from_env(prefix=env_prefix)

        self._warn_shadowed()

    # ------------------------------------------------------------------
    # 写入校验（由 ConfigNode 回调）
    # ------------------------------------------------------------------
    def _validate_write(self, path: str, value: Any) -> None:
        if not self._schema:
            return
        expected = self._schema.get(path)
        if expected is None:
            return
        if expected is int and isinstance(value, bool):
            raise ConfigValidationError(f"键 '{path}' 期望类型 int，实际得到 bool")
        if not isinstance(value, expected):
            name = getattr(expected, "__name__", str(expected))
            raise ConfigValidationError(
                f"键 '{path}' 期望类型 {name}，实际得到 {type(value).__name__}"
            )

    # ------------------------------------------------------------------
    # 冲突可见性
    # ------------------------------------------------------------------
    def _warn_shadowed(self) -> None:
        """与接口同名、属性访问拿不到的配置键：报告出来，而不是静默。

        同一批键只报一次，避免批量写入时刷屏。
        """
        reported = self.__dict__.setdefault("_shadow_reported", set())
        for path, keys in self.find_shadowed().items():
            for key in keys:
                if (path, key) in reported:
                    continue
                reported.add((path, key))
                label = "顶层" if path == "." else f"'{path}' 下"
                logger.warning(
                    "%s配置键 %r 与接口同名，属性访问会得到方法本身；"
                    "请改用 ['%s'] 或 opt.%s 访问。",
                    label,
                    key,
                    key,
                    key,
                )

    # ------------------------------------------------------------------
    # 公开方法：数据与元信息导出
    # ------------------------------------------------------------------
    def to_json(self, indent: int = 2) -> str:
        """以 JSON 字符串形式返回配置数据。

        ``indent == 2`` 时走 orjson 快速路径，其它值回退标准库 ``json``。
        """
        if indent == 2:
            return orjson.dumps(self._expand(), option=orjson.OPT_INDENT_2).decode("utf-8")
        import json

        return json.dumps(self._expand(), indent=indent, ensure_ascii=False)

    def is_auto_save(self) -> bool:
        """返回当前是否开启自动保存。"""
        return self._auto_save

    def set_auto_save(self, flag: bool) -> None:
        """开启或关闭自动保存。"""
        self._auto_save = bool(flag)

    def path(self) -> str:
        """返回配置文件路径（绝对路径）。"""
        return str(self._file_path)

    def path_abs(self) -> str:
        """返回配置文件的绝对路径。"""
        return str(self._file_path.absolute())

    def __str__(self) -> str:
        return str(self._expand())

    def __repr__(self) -> str:
        return repr(self._expand())

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        """读取配置项，支持点号路径；不存在时返回 ``default``。"""
        try:
            return self[key]
        except (ConfigKeyError, KeyError):
            return default

    def set(self, key: str, value: Any, overwrite_mode: bool = False) -> "Config":
        """写入配置项，支持点号路径；语义与属性写入一致（接口同名的键会被拒绝）。

        :return: self，支持链式操作
        """
        keys = key.split(".")
        node: ConfigNode = self
        for k in keys[:-1]:
            child = node._data.get(k)
            if child is None:
                node[k] = {}
            elif not isinstance(child, ConfigNode):
                if overwrite_mode:
                    node[k] = {}
                else:
                    raise ConfigValidationError(
                        f"路径 '{k}' 已存在但不是节点；如需把它改成节点，请设置 overwrite_mode=True。"
                    )
            node = node._data[k]

        final = keys[-1]
        existing = node._data.get(final)
        if existing is not None:
            is_branch = isinstance(existing, ConfigNode)
            is_leaf = isinstance(value, (dict, ConfigNode))
            if is_branch != is_leaf and not overwrite_mode:
                raise ConfigValidationError(
                    f"路径冲突：键 '{final}' 类型不兼容；如需覆盖，请设置 overwrite_mode=True。"
                )
        # 交给本层的属性写入语义：接口同名会报错并指路，类型校验由 _validate_write 负责。
        setattr(node, final, value)
        return self

    def setdefault(self, key: str, value: Any) -> Any:
        """键不存在时写入默认值，返回最终值。"""
        if key not in self:
            self.set(key, value)
        return self.get(key)

    def first(self, *keys: str, default: Any = None) -> Any:
        """返回第一个存在且不为 None 的值。"""
        for key in keys:
            value = self.get(key)
            if value is not None:
                return value
        return default

    def require(self, key: str) -> Any:
        """获取必需的配置项，不存在或为 None 时抛出 ``ConfigValidationError``。"""
        value = self.get(key)
        if value is None:
            raise ConfigValidationError(f"必需的配置项 '{key}' 不存在或值为 None")
        return value

    def del_key(self, key: str) -> bool:
        """删除配置项，支持点号路径，并自动清理空的父节点。

        :return: 是否真的删除了东西
        """
        try:
            del self[key]
        except (ConfigKeyError, KeyError):
            return False
        self._prune_empty(key)
        return True

    def _prune_empty(self, key: str) -> None:
        parts = key.split(".")[:-1]
        while parts:
            path = ".".join(parts)
            node = self.get(path)
            if not isinstance(node, ConfigNode) or node._data:
                return
            del self[path]
            parts.pop()

    # ------------------------------------------------------------------
    # 批量操作：容器语义，永不因键名与接口同名而失败
    # ------------------------------------------------------------------
    def update(self, data: Dict[str, Any]) -> None:
        """批量更新配置项，键支持点号路径；与外部数据源对接的推荐入口。"""
        with self._deferred():
            for key, value in data.items():
                self[key] = value
        self._warn_shadowed()

    def set_data(self, data: Dict[str, Any]) -> None:
        """用 dict 完全替换配置数据。"""
        with self._deferred():
            self._replace(data)
            self._dirty = True
        self._warn_shadowed()

    def _replace(self, mapping: Optional[Dict[str, Any]]) -> None:
        self._data = {}
        for key, value in (mapping or {}).items():
            self._write(key, value)

    def merge(
        self, other: Union[Dict[str, Any], "Config"], strategy: str = "override"
    ) -> "Config":
        """合并配置。

        :param strategy: 'override' 覆盖已有值；'keep' 保留已有值；'deep' 深度合并嵌套字典
        """
        if isinstance(other, Config):
            other_data = other.to_dict()
        elif isinstance(other, dict):
            other_data = other
        else:
            raise ConfigValidationError(
                f"不支持的类型: {type(other)}，期望 dict 或 Config"
            )
        if strategy not in ("override", "keep", "deep"):
            raise ConfigValidationError(
                f"未知的合并策略: {strategy}，支持 'override'、'keep'、'deep'"
            )

        with self._deferred():
            for key, value in other_data.items():
                if strategy == "override":
                    self[key] = value
                elif strategy == "keep":
                    if key not in self:
                        self[key] = value
                elif isinstance(self._data.get(key), ConfigNode) and isinstance(value, dict):
                    self[key] = self._deep_merge_dicts(self._data[key].to_dict(), value)
                else:
                    self[key] = value
        self._warn_shadowed()
        return self

    @staticmethod
    def _deep_merge_dicts(
        dict1: Dict[str, Any], dict2: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        return result

    def diff(self, other: Union[Dict[str, Any], "Config"]) -> Dict[str, Any]:
        """比较差异，返回 {'added': ..., 'removed': ..., 'modified': ...}。"""
        if isinstance(other, Config):
            other_data = other.to_dict()
        elif isinstance(other, dict):
            other_data = other
        else:
            raise ConfigValidationError(
                f"不支持的类型: {type(other)}，期望 dict 或 Config"
            )
        return self._diff_dicts(self.to_dict(), other_data)

    def _diff_dicts(
        self, dict1: Dict[str, Any], dict2: Dict[str, Any]
    ) -> Dict[str, Any]:
        added: Dict[str, Any] = {}
        removed: Dict[str, Any] = {}
        modified: Dict[str, Any] = {}

        for key, value in dict2.items():
            if key not in dict1:
                added[key] = value
            elif isinstance(dict1[key], dict) and isinstance(value, dict):
                nested = self._diff_dicts(dict1[key], value)
                if nested["added"]:
                    added.setdefault(key, {}).update(nested["added"])
                if nested["removed"]:
                    removed.setdefault(key, {}).update(nested["removed"])
                if nested["modified"]:
                    modified.setdefault(key, {}).update(nested["modified"])
            elif dict1[key] != value:
                modified[key] = {"old": dict1[key], "new": value}

        for key, value in dict1.items():
            if key not in dict2:
                removed[key] = value

        return {"added": added, "removed": removed, "modified": modified}

    # ------------------------------------------------------------------
    # 环境变量
    # ------------------------------------------------------------------
    def to_env(
        self, prefix: str = "", uppercase: bool = True, separator: str = "__"
    ) -> Dict[str, str]:
        """导出为环境变量格式。

        前缀用单个下划线衔接（``APP_HOST``，符合惯例），嵌套层级用 ``separator``
        （默认双下划线）衔接（``APP_DB__HOST``）。这样 ``from_env`` 才能无歧义地还原：
        单下划线在环境变量里太常见，``APP_APP_NAME`` 既可能是前缀+扁平键，
        也可能是两层嵌套，只有双下划线能区分。
        """
        prefix = prefix.rstrip("_")
        result: Dict[str, str] = {}
        for path, value in self._walk_leaves():
            name = "_".join(part for part in (prefix, separator.join(path)) if part)
            result[name.upper() if uppercase else name] = str(value)
        return result

    def _walk_leaves(
        self, node: Optional[Dict[str, Any]] = None, path: Tuple[str, ...] = ()
    ):
        if node is None:
            node = self._data
        for key, value in node.items():
            sub_path = path + (key,)
            if isinstance(value, ConfigNode):
                yield from self._walk_leaves(value._data, sub_path)
            elif isinstance(value, dict):
                yield from self._walk_leaves(value, sub_path)
            else:
                yield sub_path, value

    def from_env(self, prefix: str = "", separator: str = "__") -> "Config":
        """导入环境变量（去前缀、转小写，``separator`` 还原为嵌套路径）。

        与 ``to_env`` 互逆：``APP_DB__HOST`` 还原成 ``db.host``，``APP_NAME`` 还原成扁平键 ``name``。
        """
        prefix = prefix.rstrip("_")
        with self._deferred():
            for env_key, value in os.environ.items():
                if prefix and not env_key.startswith(prefix):
                    continue
                config_key = env_key[len(prefix):].lstrip("_") if prefix else env_key
                config_key = config_key.lower()
                if separator:
                    config_key = config_key.replace(separator, ".")
                self[config_key] = value
        self._warn_shadowed()
        return self

    # ------------------------------------------------------------------
    # 批量写入上下文
    # ------------------------------------------------------------------
    @contextmanager
    def _deferred(self):
        """暂停自动落盘，退出时统一保存一次。"""
        self._defer += 1
        try:
            yield
        finally:
            self._defer -= 1
            if self._defer == 0 and self._dirty and self._auto_save:
                self._auto_save_if_needed()

    @contextmanager
    def _unvalidated(self):
        """加载磁盘内容时不套用 schema：文件内容不该让构造函数直接失败。"""
        previous, self._validating = self._validating, False
        try:
            yield
        finally:
            self._validating = previous

    @contextmanager
    def transaction(self, rollback_on_error: bool = True):
        """批量写入上下文：块内不落盘，正常退出时统一写一次盘。

        块内抛异常时默认把内存回滚到进入前的状态，并且不写盘——
        保证的是「半途而废的修改不会进文件」，不是跨进程事务（写盘本身已是原子替换）。
        传 ``rollback_on_error=False`` 可以退回「异常也照样把已有改动落盘」的行为。
        """
        snapshot = self._expand() if rollback_on_error else None
        was_dirty = self._dirty
        failed = False
        self._defer += 1
        try:
            yield self
        except BaseException:
            failed = True
            raise
        finally:
            self._defer -= 1
            if failed and snapshot is not None:
                self._defer += 1
                try:
                    with self._unvalidated():
                        self._replace(snapshot)
                except Exception:  # 回滚失败不能盖住用户的异常
                    logger.warning("事务回滚失败，内存保持当前值。")
                finally:
                    self._defer -= 1
                self._dirty = was_dirty
            elif self._defer == 0 and self._dirty and self._auto_save:
                self._auto_save_if_needed()

    def validate(self) -> None:
        """按 schema 检查当前全部配置值，包括从文件加载进来的部分。"""
        previous, self._validating = self._validating, True
        try:
            for path, value in self._walk_leaves():
                self._validate_write(".".join(path), value)
        finally:
            self._validating = previous

    # ------------------------------------------------------------------
    # 加载 / 保存
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """从文件加载配置。磁盘内容不受 schema 约束（要检查请显式调用 ``validate()``）。"""
        with self._unvalidated(), self._lock, self._process_lock(shared=True):
            with self._file_path.open("rb") as f:
                raw_data = f.read()

            if not raw_data:
                self._replace({})
                self._dirty = False
                self._last_saved_mtime = self._file_mtime()
                return

            if raw_data.startswith(ENCRYPT_HEADER):
                if not self._pwd:
                    raise ConfigEncryptionError("此文件为加密文件，请提供密码")
                loaded = self._decrypt_data(raw_data)
            else:
                read_mode = "r" + self._handler.mode
                encoding = "utf-8" if "b" not in read_mode else None
                with self._file_path.open(read_mode, encoding=encoding) as f2:
                    loaded = self._handler.load(f2)

            if not isinstance(loaded, dict):
                raise ConfigValidationError(
                    f"{self._file_path} 的内容不是键值结构（得到 {type(loaded).__name__}），"
                    f"无法作为 {self._way} 配置加载。"
                )
            self._replace(loaded)
            self._dirty = False
            self._last_saved_mtime = self._file_mtime()

    def _file_mtime(self) -> Optional[int]:
        try:
            return self._file_path.stat().st_mtime_ns
        except OSError:
            return None

    def _changed_on_disk(self) -> bool:
        """磁盘内容与内存是否已经不一致（用于区分自己写盘和外部修改）。"""
        current = self._file_mtime()
        return current is None or current != self._last_saved_mtime

    def _load_env_config(self, env: str) -> None:
        """加载环境特定配置文件（如 app.dev.toml）并合并。"""
        env_file = self._file_path.with_name(
            f"{self._file_path.stem}.{env}{self._file_path.suffix}"
        )
        if not env_file.exists():
            logger.debug("环境配置文件不存在: %s", env_file)
            return

        try:
            with self._lock, self._process_lock(shared=True):
                raw_data = env_file.read_bytes()
                if not raw_data:
                    return
                if raw_data.startswith(ENCRYPT_HEADER):
                    if not self._pwd:
                        raise ConfigEncryptionError(
                            f"环境配置文件 {env_file} 为加密文件，请提供密码"
                        )
                    env_data = self._decrypt_data(raw_data)
                else:
                    read_mode = "r" + self._handler.mode
                    encoding = "utf-8" if "b" not in read_mode else None
                    with env_file.open(read_mode, encoding=encoding) as f2:
                        env_data = self._handler.load(f2)
                self.update(env_data)
                logger.info("已加载环境配置: %s", env_file)
        except ConfigError:
            raise
        except Exception as exc:
            raise ConfigIOError(f"加载环境配置文件失败 {env_file}: {exc}") from exc

    def reload(self) -> None:
        """从磁盘重新加载，丢弃所有未保存的更改。"""
        self._load()
        logger.info("配置已从 %s 重新加载。", self._file_path)

    def load(self, file: Union[str, os.PathLike, None] = None, way: Optional[str] = None) -> None:
        """切换目标文件或格式（不读取内容；要立即生效请用 ``reload()``）。"""
        if file:
            self._file_path = Path(file).resolve()
        if way:
            self._way = self._validate_format(way)
            self._handler = ConfigHandlerFactory.get_handler(self._way)

    def mark_dirty(self) -> None:
        """标记配置已更改。"""
        self._dirty = True

    def notify_dirty(self) -> None:
        """由节点在数据变动时调用。"""
        with self._lock:
            self._dirty = True
            if self._defer or not self._auto_save:
                return
            self._auto_save_if_needed()

    def _auto_save_if_needed(self) -> None:
        if not self._auto_save:
            return
        if self._debounce_ms == 0:
            self.save()
            return
        if self._save_timer and self._save_timer.is_alive():
            self._save_timer.cancel()
        self._save_timer = threading.Timer(self._debounce_ms / 1000, self._flush_save)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _flush_save(self) -> None:
        if self._save_timer and self._save_timer.is_alive():
            self._save_timer.cancel()
        self._save_timer = None
        self.save()

    def save(self) -> None:
        """立即保存到文件（忽略去抖延迟）。"""
        if self._save_timer and self._save_timer.is_alive():
            self._save_timer.cancel()
            self._save_timer = None

        with self._lock:
            if not self._dirty:
                return
            try:
                if self._pwd and self._file_path.exists():
                    # 写前校验：既有文件若已是加密格式，必须仍能用当前密码解开，否则拒绝覆盖。
                    # 明文文件则放行，这正是「给既有明文配置加密码」的路径。
                    raw = self._file_path.read_bytes()
                    if raw.startswith(ENCRYPT_HEADER):
                        self._decrypt_data(raw)

                self._write_to_file(self._file_path, self._way)
                self._dirty = False
                self._last_saved_mtime = self._file_mtime()
                self._cleanup_lock_file()
            except ConfigError:
                self._dirty = True
                raise
            except Exception as exc:
                self._dirty = True
                logger.error("保存配置文件失败 %s: %s", self._file_path, exc)
                raise ConfigIOError(f"保存配置文件失败 {self._file_path}: {exc}") from exc

    def to_file(
        self,
        file: Union[str, os.PathLike, None] = None,
        way: Optional[str] = None,
    ) -> None:
        """另存为指定文件和/或格式。"""
        target_file = self._ensure_extension(Path(file)) if file else self._file_path
        target_way = self._validate_format(way) if way else self._way
        with self._lock:
            self._write_to_file(target_file, target_way)
            self._cleanup_lock_file()
        logger.info("配置已成功另存到 %s", target_file)

    def _write_to_file(self, target_file: Path, target_way: str) -> None:
        """写入指定文件和格式的核心逻辑：临时文件 + 原子替换。"""
        target_handler = ConfigHandlerFactory.get_handler(target_way)
        self._ensure_file_exists(file_path=target_file)

        temp_path = target_file.with_name(f"{target_file.name}.tmp")
        try:
            with self._process_lock(shared=False):
                config_data = self._expand()

                if self._pwd:
                    temp_path.write_bytes(self._encrypt_data(config_data))
                else:
                    mode = "w" + target_handler.mode
                    encoding = "utf-8" if "b" not in mode else None
                    with temp_path.open(mode, encoding=encoding) as f:
                        target_handler.save(config_data, f)
                        f.flush()
                        os.fsync(f.fileno())

                temp_path.replace(target_file)
        except Exception as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ConfigIOError(f"写入文件 {target_file} 失败: {exc}") from exc

    def _ensure_file_exists(self, file_path: Optional[Path] = None) -> None:
        path = file_path or self._file_path
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            except OSError as exc:
                raise ConfigIOError(f"创建文件 {path} 失败: {exc}") from exc

    def del_clean(self) -> bool:
        """清空所有配置并删除配置文件。"""
        with self._lock:
            if not self._file_path.exists():
                return False
            try:
                self._file_path.unlink()
            except OSError as exc:
                logger.warning("清除配置文件 %s 失败：%s", self._file_path, exc)
                return False
            if self._process_safe:
                lock_path = self._lock_path()
                if lock_path.exists():
                    try:
                        lock_path.unlink()
                    except OSError:
                        pass
            self._replace({})
            self._dirty = False
            return True

    # ------------------------------------------------------------------
    # 加密
    # ------------------------------------------------------------------
    def _derive_fernet(self, salt: bytes):
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.hashes import SHA256
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        assert self._pwd is not None
        kdf = PBKDF2HMAC(
            algorithm=SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS
        )
        key = _b64.urlsafe_b64encode(kdf.derive(self._pwd.encode()))
        return Fernet(key)

    def _fernet_for(self, salt: bytes):
        """同一个 (密码, salt) 只派生一次密钥；自动保存因此不再是每次赋值都跑一遍 PBKDF2。"""
        if (
            self._fernet is None
            or self._salt != salt
            or self._fernet_pwd != self._pwd
        ):
            self._fernet = self._derive_fernet(salt)
            self._salt = salt
            self._fernet_pwd = self._pwd
        return self._fernet

    def _encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """使用 Fernet(AES128 + HMAC) 加密配置数据。"""
        if not self._pwd:
            raise ConfigEncryptionError("加密需要提供密码。")
        if self._salt is None:
            self._salt = os.urandom(SALT_SIZE)
        cipher = self._fernet_for(self._salt)
        return ENCRYPT_HEADER + self._salt + cipher.encrypt(orjson.dumps(data))

    def _decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """解密 Fernet 数据；密码错误或内容被篡改时抛 ``ConfigEncryptionError``。"""
        if not self._pwd:
            raise ConfigEncryptionError("解密时需要提供密码。")
        if not encrypted_data.startswith(ENCRYPT_HEADER):
            # 明文文件（例如加密配置被外部编辑器重写），原样交给上层解析
            raise ConfigEncryptionError("数据缺少加密头，无法解密。")

        from cryptography.fernet import InvalidToken

        blob = encrypted_data[len(ENCRYPT_HEADER):]
        salt, ciphertext = blob[:SALT_SIZE], blob[SALT_SIZE:]
        try:
            cipher = self._fernet_for(salt)
            return orjson.loads(cipher.decrypt(ciphertext))
        except InvalidToken:
            raise ConfigEncryptionError("校验失败：密码错误或数据损坏")
        except ConfigEncryptionError:
            raise
        except Exception as exc:
            raise ConfigEncryptionError(f"解密失败: {exc}") from exc

    # ------------------------------------------------------------------
    # 格式工具
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_format(_way) -> str:
        """校验并返回合法格式名，接受 str 或 Format。"""
        if isinstance(_way, Format):
            return _way.value
        return Format.from_str(str(_way)).value

    def _ensure_extension(self, path: Path) -> Path:
        """确保文件有正确扩展名，并创建必要目录。"""
        if path.parent and not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigIOError(f"创建目录 {path.parent} 失败: {exc}") from exc
        if path.suffix == "":
            path = path.with_suffix(f".{self._way}")
        return path

    # ------------------------------------------------------------------
    # 文件变更监控
    # ------------------------------------------------------------------
    def enable_watch(self) -> None:
        """开启文件变动监听，文件被外部修改后自动 reload。需要 watchdog。"""
        if self._observer:
            return

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError as exc:
            raise ImportError(
                "文件监听需要 'watchdog'，请先安装：pip install 'confull[watch]'"
            ) from exc

        if sys.version_info >= (3, 13):
            logger.warning(
                "watchdog 在 Python 3.13+ 可能存在兼容性问题，"
                "建议升级 watchdog 或使用轮询方式监听"
            )

        class _Handler(FileSystemEventHandler):
            def __init__(self, manager: "Config"):
                self._manager = manager
                self._target_path = manager._file_path.resolve()

            def _is_target(self, src_path) -> bool:
                if isinstance(src_path, bytes):
                    try:
                        src_path = src_path.decode(errors="ignore")
                    except Exception:
                        return False
                try:
                    return Path(src_path).resolve() == self._target_path
                except Exception:
                    return str(Path(src_path).absolute()) == str(self._target_path)

            def on_modified(self, event):
                # 自己写盘也会触发事件：只有 mtime 与上次落盘不一致才说明是外部改动。
                if self._is_target(event.src_path) and self._manager._changed_on_disk():
                    self._manager._load()

            on_created = on_modified
            on_moved = on_modified

        handler = _Handler(self)
        observer = Observer()
        observer.schedule(handler, self._file_path.parent.as_posix(), recursive=False)
        observer.daemon = True
        # Observer 本身就是 threading.Thread，直接命名即可，无需占位线程。
        observer.name = f"DirWatcher-{self._file_path.name}"
        observer.start()
        self._observer = observer

    def disable_watch(self) -> None:
        """关闭文件监听。"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=1)
            self._observer = None

    def __del__(self):
        try:
            self.disable_watch()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 上下文管理器
    # ------------------------------------------------------------------
    def __enter__(self) -> "Config":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出时自动保存。"""
        self.save()

    # ------------------------------------------------------------------
    # 进程锁
    # ------------------------------------------------------------------
    def _lock_path(self) -> Path:
        return self._file_path.with_name(self._file_path.name + ".lock")

    @contextmanager
    def _process_lock(self, shared: bool = False):
        """跨进程文件锁，shared=True 使用共享锁。"""
        if not self._process_safe:
            yield
            return

        try:
            import portalocker
        except ImportError as exc:
            raise ImportError(
                "process_safe 需要 'portalocker'，请先安装：pip install 'confull[process]'"
            ) from exc

        lock_flags = portalocker.LOCK_SH if shared else portalocker.LOCK_EX
        lock_path = self._lock_path()
        if not lock_path.exists():
            lock_path.touch()
        with portalocker.Lock(str(lock_path), flags=lock_flags):
            yield

    def _cleanup_lock_file(self) -> None:
        if not self._process_safe:
            return
        lock_path = self._lock_path()
        try:
            if lock_path.exists():
                lock_path.unlink()
        except OSError:
            # 文件仍被占用时删除会失败，忽略即可
            pass
