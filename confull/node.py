from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Dict, Iterator, Optional, Tuple

from .exceptions import ConfigKeyError, ConfigValidationError

_API_CACHE: Dict[type, frozenset] = {}

_MISSING = object()


def _api_names(cls: type) -> frozenset:
    """派生某个类占用的公开属性名。

    这些名字会被 Python 的常规属性查找命中，因此同名配置键无法用属性方式读取，
    必须由 ``[]`` 或 ``opt`` 访问。名单自动派生，杜绝手工枚举漏项。
    """
    names = _API_CACHE.get(cls)
    if names is None:
        names = frozenset(n for n in dir(cls) if not n.startswith("_"))
        _API_CACHE[cls] = names
    return names


class _DataProxy:
    """纯数据视图：不占用任何公开属性名，因此任何配置键都能用属性方式读写。

    由 :attr:`ConfigNode.opt` 返回。除双下划线方法外它没有成员，
    所以 ``cfg.opt.items`` / ``cfg.opt.save`` 一定拿到的是数据而不是接口。
    """

    __slots__ = ("_node",)

    def __init__(self, node: "ConfigNode"):
        object.__setattr__(self, "_node", node)

    def _target(self) -> "ConfigNode":
        return object.__getattribute__(self, "_node")

    @staticmethod
    def _wrap(value: Any) -> Any:
        return _DataProxy(value) if isinstance(value, ConfigNode) else value

    def __getattr__(self, key: str) -> Any:
        try:
            return self._wrap(self._target()[key])
        except ConfigKeyError:
            raise AttributeError(
                f"配置中没有键 '{key}'。可用 opt['{key}'] 或 get('{key}', default) 确认。"
            ) from None

    def __setattr__(self, key: str, value: Any) -> None:
        self._target()[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self._target()[key]
        except ConfigKeyError:
            raise AttributeError(key) from None

    def __getitem__(self, key: str) -> Any:
        return self._wrap(self._target()[key])

    def __setitem__(self, key: str, value: Any) -> None:
        self._target()[key] = value

    def __delitem__(self, key: str) -> None:
        del self._target()[key]

    def __contains__(self, key: str) -> bool:
        return key in self._target()

    def __iter__(self) -> Iterator[str]:
        return iter(self._target())

    def __len__(self) -> int:
        return len(self._target())

    def __bool__(self) -> bool:
        return bool(self._target())

    def __call__(self, key: str, default: Any = None) -> Any:
        return self._target().get(key, default)

    def __eq__(self, other: Any) -> Any:
        if isinstance(other, _DataProxy):
            other = other._target()
        return self._target() == other

    def __repr__(self) -> str:
        return repr(self._target().to_dict())


class ConfigNode(MutableMapping):
    """配置树的唯一实现：既是 dict，又支持属性与点路径访问。

    命名冲突的处理规则只有一条：

    * 属性写法（``node.key = v`` / ``set()``）遵守本层接口名，冲突即报错并指路；
    * 容器写法（``node['key']`` / ``node.opt.key`` / 批量导入）永远放行，
      因为配置文件来自外部，库无权拒绝用户书写 ``save``、``items`` 这类键名。

    因此任何键都保证可达，且遮蔽情况可由 :attr:`shadowed` 查出。
    """

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        *,
        manager: Any = None,
        parent: Optional["ConfigNode"] = None,
        key_in_parent: Optional[str] = None,
    ):
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigValidationError(
                f"配置数据必须是 dict，实际得到 {type(data).__name__}: {data!r}。"
                f"若第一个参数想传文件名，请写成 Config(file={data!r})。"
            )
        # 拷贝一层，避免把调用方的 dict 变成库的内部状态；嵌套部分由 _adopt 递归接管。
        self._data: Dict[str, Any] = {}
        self._manager = manager
        self._parent = parent
        self._key_in_parent = key_in_parent
        for key, value in data.items():
            self._write(key, value)

    # ------------------------------------------------------------------
    # 嵌套接管
    # ------------------------------------------------------------------
    def _adopt(self, value: Any, key: str) -> Any:
        if isinstance(value, ConfigNode):
            value._manager = self._manager
            value._parent = self
            value._key_in_parent = key
            return value
        if isinstance(value, dict):
            return ConfigNode(
                value, manager=self._manager, parent=self, key_in_parent=key
            )
        return value

    # ------------------------------------------------------------------
    # dict 协议
    # ------------------------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        if not isinstance(key, str):
            raise ConfigKeyError(key, f"配置键必须是字符串，实际得到 {type(key).__name__}。")
        if "." in key:
            return self._resolve(key)
        try:
            return self._data[key]
        except KeyError:
            raise self._missing(key) from None

    def _resolve(self, path: str) -> Any:
        node: Any = self
        for part in path.split("."):
            if not isinstance(node, ConfigNode):
                raise ConfigKeyError(
                    path, f"路径 '{path}' 中 '{part}' 的上游不是可继续查找的节点。"
                )
            node = node._data.get(part, _MISSING)
            if node is _MISSING:
                raise ConfigKeyError(
                    path, f"路径 '{path}' 不存在。可用 get('{path}', default) 兜底。"
                )
        return node

    def _missing(self, key: str) -> ConfigKeyError:
        return ConfigKeyError(
            key,
            f"键 '{key}' 不存在。可用 get('{key}', default) 兜底，"
            f"或 set('{key}', value) 创建。",
        )

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise ConfigValidationError(f"配置键必须是字符串，实际得到 {type(key).__name__}。")
        if "." in key:
            # 容器写法允许点路径直接写入，与读取 / 删除保持对称。
            parent_path, _, final = key.rpartition(".")
            container = self._resolve_or_create(parent_path) if parent_path else self
            container[final] = value
            return
        self._write(key, value)

    def _resolve_or_create(self, path: str) -> "ConfigNode":
        node: ConfigNode = self
        for part in path.split("."):
            child = node._data.get(part)
            if not isinstance(child, ConfigNode):
                child = ConfigNode(
                    {}, manager=self._manager, parent=node, key_in_parent=part
                )
                node._data[part] = child
            node = child
        return node

    def _write(self, key: str, value: Any) -> None:
        manager = self._manager
        if manager is not None and getattr(manager, "_validating", True):
            manager._validate_write(self._path_of(key), value)
        self._data[key] = self._adopt(value, key)
        self._trigger_save()

    def _path_of(self, key: str) -> str:
        parts = [key]
        node: Optional[ConfigNode] = self
        while node is not None and node._key_in_parent:
            parts.append(node._key_in_parent)
            node = node._parent
        return ".".join(reversed(parts))

    def __delitem__(self, key: str) -> None:
        if "." in key:
            parent_key, _, final = key.rpartition(".")
            parent = self._resolve(parent_key) if parent_key else self
            if isinstance(parent, ConfigNode):
                del parent[final]
                return
            raise self._missing(key)
        try:
            del self._data[key]
        except KeyError:
            raise self._missing(key) from None
        self._trigger_save()

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: Any) -> bool:
        try:
            self[key]
        except (ConfigKeyError, KeyError):
            return False
        return True

    def __call__(self, key: str, default: Any = None) -> Any:
        """``cfg('a.b')`` 等价于 ``cfg.get('a.b', default)``。"""
        return self.get(key, default)

    # ------------------------------------------------------------------
    # 属性协议
    # ------------------------------------------------------------------
    def __getattr__(self, key: str) -> Any:
        # 只有常规属性查找失败才会走到这里，即 key 不在本层接口名单里。
        if key.startswith("_"):
            raise AttributeError(key)
        data = self.__dict__.get("_data", {})
        if key in data:
            return data[key]
        raise AttributeError(
            f"{type(self).__name__} 没有配置键 '{key}'。"
            f"可用 get('{key}', default) 或 opt.{key}。"
        )

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("_"):
            super().__setattr__(key, value)
            return
        if key in _api_names(type(self)):
            raise ConfigValidationError(
                f"'{key}' 与本层接口同名，属性写法无法写入。"
                f"请改用 ['{key}'] = {value!r} 或 opt.{key} = {value!r}。"
            )
        self[key] = value

    def __delattr__(self, key: str) -> None:
        if key.startswith("_"):
            super().__delattr__(key)
            return
        if key not in self._data:
            extra = "（它是接口名，不是配置键）" if key in _api_names(type(self)) else ""
            raise AttributeError(f"没有配置键 '{key}'{extra}。")
        del self._data[key]
        self._trigger_save()

    # ------------------------------------------------------------------
    # 冲突可见性
    # ------------------------------------------------------------------
    @property
    def opt(self) -> _DataProxy:
        """返回不带任何接口名的纯数据视图，用于读写与接口同名的配置键。"""
        return _DataProxy(self)

    @property
    def shadowed(self) -> Tuple[str, ...]:
        """本层被接口名遮蔽、因此属性访问拿不到数据的配置键。"""
        api = _api_names(type(self))
        return tuple(key for key in self._data if key in api)

    @property
    def reserved(self) -> Tuple[str, ...]:
        """本层不能用作属性写入的配置键名（即全部公开接口名）。"""
        return tuple(sorted(_api_names(type(self))))

    def find_shadowed(self) -> Dict[str, Tuple[str, ...]]:
        """递归收集整棵配置树里被遮蔽的键，返回 {点路径: (键, ...)}。"""
        result: Dict[str, Tuple[str, ...]] = {}
        shadowed = self.shadowed
        if shadowed:
            result["."] = shadowed
        for key, value in self._data.items():
            if isinstance(value, ConfigNode):
                for sub_key, sub_shadowed in value.find_shadowed().items():
                    prefix = key if sub_key == "." else f"{key}.{sub_key}"
                    result[prefix] = sub_shadowed
        return result

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------
    def _expand(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in self._data.items():
            result[key] = value._expand() if isinstance(value, ConfigNode) else value
        return result

    def to_dict(self) -> Dict[str, Any]:
        """展开为原生 dict（逐层新建，改动它不影响配置）。"""
        return self._expand()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"

    def __str__(self) -> str:
        return str(self._expand())

    # ------------------------------------------------------------------
    # 运算符
    # ------------------------------------------------------------------
    def __or__(self, other: Any) -> Dict[str, Any]:
        if isinstance(other, (ConfigNode, dict)):
            result = self._expand()
            result.update(other.to_dict() if isinstance(other, ConfigNode) else other)
            return result
        return NotImplemented

    def __ror__(self, other: Any) -> Dict[str, Any]:
        if isinstance(other, dict):
            result = other.copy()
            result.update(self._expand())
            return result
        return NotImplemented

    def __ior__(self, other: Any) -> "ConfigNode":
        if isinstance(other, ConfigNode):
            merged = other._expand()
        elif isinstance(other, dict):
            merged = other
        else:
            return NotImplemented
        for key, value in merged.items():
            self[key] = value
        return self

    # ------------------------------------------------------------------
    def _trigger_save(self) -> None:
        """变更通知：冒泡到父节点，并最终交给顶层管理器落盘。"""
        if self._manager is not None:
            self._manager.notify_dirty()
        if self._parent is not None:
            self._parent._trigger_save()
