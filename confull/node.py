from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Dict, Iterator, Optional, Set
from threading import Lock

class ConfigNode(MutableMapping):
    """轻量级包装，使嵌套 dict 支持属性 / 下标方式访问，并在变更时通知管理器。"""

    # 避免与内部属性/方法冲突的保留关键字
    _RESERVED: Set[str] = {
        "has_top_level_key", "_trigger_save",
        "_data", "_manager", "_parent", "_key_in_parent", "_lock",
    }

    def __init__(self, data: Optional[Dict[str, Any]] = None, *, manager=None, parent: Optional["ConfigNode"] = None, key_in_parent: Optional[str] = None):
        self._data: Dict[str, Any] = data or {}
        self._manager = manager  # weak reference to Config
        self._parent = parent
        self._key_in_parent = key_in_parent
        self._lock = Lock()

    # -----------------------------------------------------
    # 基础属性
    # -----------------------------------------------------
    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    @data.setter
    def data(self, value: Dict[str, Any]):
        self._data = value
        self._trigger_save()

    # -----------------------------------------------------
    # MutableMapping 接口实现
    # -----------------------------------------------------
    def __setitem__(self, key: str, value: Any):
        if key in self._RESERVED:
            raise AttributeError(f"Cannot set reserved keyword '{key}' as a config item.")
        if isinstance(value, dict):
            value = ConfigNode(value, manager=self._manager, parent=self, key_in_parent=key)
        self._data[key] = value
        self._trigger_save()

    def __delitem__(self, key: str):
        if key in self._data:
            del self._data[key]
            self._trigger_save()
        else:
            raise KeyError(key)

    def __getitem__(self, key: str) -> Any:
        # 支持点路径访问："a.b.c"
        if "." in key:
            keys = key.split(".")
            node: Any = self
            for k in keys:
                if isinstance(node, ConfigNode):
                    node = node._data.get(k)
                elif isinstance(node, dict):
                    node = node.get(k)
                else:
                    raise KeyError(key)
                if node is None:
                    raise KeyError(key)
            if isinstance(node, dict):
                return ConfigNode(node, manager=self._manager)
            return node

        # 单层键
        value = self._data[key]
        if isinstance(value, dict):
            # 确保返回的节点与父节点共享同一个 manager
            node = ConfigNode(value, manager=self._manager, parent=self, key_in_parent=key)
            self._data[key] = node # 将 dict 替换为节点，以便后续修改能正确冒泡
            return node
        return value

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    # -----------------------------------------------------
    # 属性方式访问
    # -----------------------------------------------------
    def has_top_level_key(self, key: str) -> bool:
        return key in self._data and key not in self._RESERVED

    def __getattr__(self, key: str):
        if key in self._RESERVED:
            raise AttributeError(key)

        # 若不存在则自动创建子节点，实现链式赋值 autovivification
        if key not in self._data:
            self.__setitem__(key, {}) # 使用 __setitem__ 来创建，确保能触发保存
        return self.__getitem__(key)

    def __setattr__(self, key: str, value: Any):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __delattr__(self, key: str):
        if key.startswith("_"):
            super().__delattr__(key)
        else:
            self.__delitem__(key)

    # -----------------------------------------------------
    def _expand(self) -> Dict[str, Any]:
        """内部递归展开为原生 dict。"""
        result: Dict[str, Any] = {}
        for k, v in self._data.items():
            if isinstance(v, ConfigNode):
                result[k] = v._expand()
            else:
                result[k] = v
        return result

    @property
    def dict(self) -> Dict[str, Any]:
        """与 Config.dict 行为一致，返回展开后的原生 dict。"""
        return self._expand()

    def __repr__(self) -> str:  # pragma: no cover
        return f"ConfigNode({self._data!r})"

    def __str__(self) -> str:  # pragma: no cover
        """可读性更好的字符串表示，显示展开后的字典。"""
        return str(self._expand())

    # -----------------------------------------------------
    def _trigger_save(self):
        """内部方法：在数据变动时标记脏并执行自动保存。"""
        if self._manager:
            # 在多线程场景下，写入应持有顶层 Config._lock，防止并发写-写冲突
            self._manager.notify_dirty()
        # 将变更冒泡到父节点
        if self._parent:
            self._parent._trigger_save()