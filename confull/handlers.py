from __future__ import annotations

import configparser
import importlib
import xml.etree.ElementTree as ElementTree
from typing import Any, Dict, IO, Type

import orjson

from .formats import Format

__all__ = [
    "ConfigHandler",
    "JSONConfigHandler",
    "TOMLConfigHandler",
    "YAMLConfigHandler",
    "INIConfigHandler",
    "XMLConfigHandler",
    "ConfigHandlerFactory",
]


class ConfigHandler:
    """配置文件处理器基类。"""

    mode = "t"  # "t" for text, "b" for binary

    def load(self, file: IO) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def save(self, data: Dict[str, Any], file: IO):  # pragma: no cover
        raise NotImplementedError


def _require(module_name: str):
    """按需导入可选格式依赖，缺失时给出可操作的提示。"""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(
            f"读写该格式需要 '{module_name}'，请先安装：pip install 'confull[{module_name}]'"
        ) from exc


class JSONConfigHandler(ConfigHandler):
    """JSON 格式处理器"""

    mode = "b"

    def load(self, file: IO) -> Dict[str, Any]:
        return orjson.loads(file.read())

    def save(self, data: Dict[str, Any], file: IO):
        file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))  # type: ignore[arg-type]


class TOMLConfigHandler(ConfigHandler):
    """TOML 格式处理器"""

    def load(self, file: IO) -> Dict[str, Any]:
        return _require("toml").load(file)

    def save(self, data: Dict[str, Any], file: IO):
        file.write(_require("toml").dumps(data))  # type: ignore[arg-type]


class YAMLConfigHandler(ConfigHandler):
    """YAML 格式处理器"""

    def load(self, file: IO) -> Dict[str, Any]:
        return _require("yaml").safe_load(file) or {}

    def save(self, data: Dict[str, Any], file: IO):
        _require("yaml").safe_dump(data, file, allow_unicode=True, sort_keys=False)


class INIConfigHandler(ConfigHandler):
    """INI 格式处理器 - 支持嵌套结构（点路径存储）"""

    def load(self, file: IO) -> Dict[str, Any]:
        parser = configparser.ConfigParser()
        parser.read_file(file)
        
        result = {}
        defaults = parser.defaults()
        for section in parser.sections():
            section_data = {}
            # items() 会带上 DEFAULT 段的键，那些值在顶层单独存放，这里跳过。
            for key, value in parser.items(section):
                if key not in defaults:
                    self._set_nested(section_data, key, value)
            result[section] = section_data
        
        # 处理 DEFAULT section（独立存储）
        if parser.defaults():
            default_data = {}
            for key, value in parser.defaults().items():
                self._set_nested(default_data, key, value)
            result['DEFAULT'] = default_data
        
        return result

    def save(self, data: Dict[str, Any], file: IO):
        parser = configparser.ConfigParser()
        default_storage: Dict[str, str] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # 普通 section，展平嵌套结构为点路径
                flat = self._flatten(value)
                parser[key] = {k: str(v) for k, v in flat.items()}
            else:
                # 直接量放入 DEFAULT 段
                default_storage[key] = str(value)

        if default_storage:
            parser['DEFAULT'] = default_storage

        parser.write(file)  # type: ignore[arg-type]
    
    def _flatten(self, data: Dict[str, Any], prefix: str = '') -> Dict[str, str]:
        """将嵌套 dict 展平为点路径"""
        items: Dict[str, str] = {}
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                items.update(self._flatten(value, new_key))
            else:
                items[new_key] = str(value)
        return items
    
    def _set_nested(self, data: Dict[str, Any], key: str, value: str):
        """将点路径键值对设置到嵌套 dict 中"""
        keys = key.split('.')
        d = data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value


class XMLConfigHandler(ConfigHandler):
    """XML 格式处理器"""

    mode = "b"

    def load(self, file: IO) -> Dict[str, Any]:
        tree = ElementTree.parse(file)
        return self._element_to_dict(tree.getroot())

    def save(self, data: Dict[str, Any], file: IO):
        root = self._dict_to_element("root", data)
        tree = ElementTree.ElementTree(root)
        tree.write(file, encoding="utf-8", xml_declaration=True)  # type: ignore[arg-type]

    # -------------------- helpers --------------------
    def _element_to_dict(self, element: ElementTree.Element) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for child in element:
            if len(child):
                result[child.tag] = self._element_to_dict(child)
            else:
                result[child.tag] = child.text
        return result

    def _dict_to_element(self, tag: str, data: Dict[str, Any]) -> ElementTree.Element:
        element = ElementTree.Element(tag)
        for key, value in data.items():
            if isinstance(value, dict):
                element.append(self._dict_to_element(key, value))
            else:
                child = ElementTree.SubElement(element, key)
                child.text = str(value)
        return element


class ConfigHandlerFactory:
    """根据格式返回对应 Handler"""

    _handlers: Dict[str, Type[ConfigHandler]] = {
        Format.JSON.value: JSONConfigHandler,
        Format.TOML.value: TOMLConfigHandler,
        Format.YAML.value: YAMLConfigHandler,
        Format.INI.value: INIConfigHandler,
        Format.XML.value: XMLConfigHandler,
    }

    @classmethod
    def get_handler(cls, fmt: str) -> ConfigHandler:
        try:
            handler_cls = cls._handlers[fmt]
        except KeyError as exc:
            raise ValueError(f"Unsupported format: {fmt}") from exc
        return handler_cls() 