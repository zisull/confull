from __future__ import annotations

import orjson
import toml
import yaml
import configparser
import xml.etree.ElementTree as ElementTree
from typing import Any, Dict, IO, Type

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
        return toml.load(file)

    def save(self, data: Dict[str, Any], file: IO):
        file.write(toml.dumps(data))  # type: ignore[arg-type]


class YAMLConfigHandler(ConfigHandler):
    """YAML 格式处理器"""

    def load(self, file: IO) -> Dict[str, Any]:
        return yaml.safe_load(file) or {}

    def save(self, data: Dict[str, Any], file: IO):
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


class INIConfigHandler(ConfigHandler):
    """INI 格式处理器"""

    def load(self, file: IO) -> Dict[str, Any]:
        parser = configparser.ConfigParser()
        parser.read_file(file)
        return {section: dict(parser.items(section)) for section in parser.sections()}

    def save(self, data: Dict[str, Any], file: IO):
        parser = configparser.ConfigParser()
        default_storage: Dict[str, str] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # 普通 section
                parser[key] = {k: str(v) for k, v in value.items()}
            else:
                # 直接量放入 DEFAULT 段
                default_storage[key] = str(value)

        if default_storage:
            parser['默认'] = default_storage  # type: ignore[index]

        parser.write(file)  # type: ignore[arg-type]


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