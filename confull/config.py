# -*- coding: utf-8 -*-
# @author: zisull@qq.com
# @date: 2024年11月19日

import configparser
import os
import xml.etree.ElementTree as ElementTree
from collections.abc import MutableMapping
from threading import Lock
import hashlib
import base64

import orjson
import toml
import yaml


class Config:
    """
    多格式配置管理器，支持 dict <=> [ini, xml, json, toml, yaml] 的读写与自动保存。
    支持密码加密保护。
    """

    def __init__(self, data=None, file="config", way="toml", replace=False,
                 auto_save=True, pwd=None):
        """
        初始化配置管理器。
        :param data: 初始配置数据（dict）
        :param file: 配置文件名（可无扩展名,可自动创建目录）
        :param way: 配置文件格式（json/toml/yaml/ini/xml）
        :param replace: 是否覆盖已有配置文件
        :param auto_save: 是否自动保存
        :param pwd: 密码字符串，用于加密配置文件
        """
        self._file = file
        self._way = self.validate_format(way)
        self._file = self.ensure_extension(file)  # # 调用 ensure_extension 来创建目录和添加扩展名
        self._auto_save = auto_save
        self._pwd = pwd
        self._key = self._generate_key(pwd) if pwd else None
        self._data = ConfigNode(data if data is not None else {}, manager=self)
        self._dirty = False if data is not None else True
        self._lock = Lock()
        self._handler = ConfigHandlerFactory.get_handler(self._way)

        if os.path.exists(self._file) and not replace:
            self._load()
        else:
            # 当文件不存在时，无论replace参数如何都使用data初始化
            if data is not None:
                self._data = ConfigNode(data, manager=self)
                self._dirty = True  # 强制标记需要保存
            self.save()  # 确保立即保存初始数据

    def _generate_key(self, password):
        """
        从密码生成加密密钥，使用盐值增强安全性。
        :param password: 密码字符串
        :return: 加密密钥
        """
        if not password:
            return None
        
        # 生成8字节的随机盐值
        self._salt = os.urandom(8)
        
        # 使用密码和盐值生成密钥
        return hashlib.sha256(password.encode() + self._salt).digest()

    def _encrypt_data(self, data):
        """
        简单加密数据，使用盐值增强安全性。
        :param data: 要加密的数据
        :return: 加密后的数据
        """
        if not self._key:
            return data
        
        # 将数据转换为JSON字符串
        json_data = orjson.dumps(data)
        
        # 简单异或加密
        encrypted = bytearray()
        for i, byte in enumerate(json_data):
            encrypted.append(byte ^ self._key[i % len(self._key)])
        
        # 盐值(8字节) + 加密数据
        result = self._salt + bytes(encrypted)
        
        return base64.b64encode(result)

    def _decrypt_data(self, encrypted_data):
        """
        解密数据。
        :param encrypted_data: 加密的数据
        :return: 解密后的数据
        """
        if not self._key:
            return encrypted_data
        
        try:
            # 解码base64
            data = base64.b64decode(encrypted_data)
            
            # 提取盐值
            self._salt = data[:8]
            encrypted_bytes = data[8:]
            
            # 重新生成密钥
            self._key = hashlib.sha256(self._pwd.encode() + self._salt).digest()
            
            # 解密数据
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ self._key[i % len(self._key)])
            
            return orjson.loads(bytes(decrypted))
        except Exception as e:
            print(f"解密数据失败：{e}")
            return {}

    @property
    def json(self):
        """以 JSON 字符串格式返回配置数据。"""
        return orjson.dumps(self.dict, option=orjson.OPT_INDENT_2).decode('utf-8')

    @property
    def dict(self):
        """以 dict 格式返回配置数据。"""
        return self._data.to_dict()

    @dict.setter
    def dict(self, value):
        """用 dict 批量设置配置数据。"""
        self.set_data(value)

    @property
    def auto_save(self):
        """是否自动保存。"""
        return self._auto_save

    @auto_save.setter
    def auto_save(self, value):
        """设置自动保存。"""
        self._auto_save = value



    @property
    def str(self):
        """以字符串格式返回配置数据。"""
        return str(self.dict)

    @property
    def file_path(self):
        """配置文件路径。"""
        return self._file

    @property
    def file_path_abs(self):
        """配置文件绝对路径。"""
        return os.path.abspath(self._file)

    def read(self, key, default=None):
        """
        读取配置项，支持点号路径。
        :param key: 配置项路径（如 a.b.c）
        :param default: 默认值
        """
        keys = key.split('.')
        node = self._data
        for k in keys:
            if isinstance(node, ConfigNode):
                node = node.data.get(k, None)
                if isinstance(node, dict):
                    node = ConfigNode(node, manager=self)
                elif node is None:
                    return default
            else:
                return default
        return node

    def write(self, key, value, overwrite_mode=False):
        """
        写入配置项，支持点号路径。
        :param key: 配置项路径
        :param value: 配置值
        :param overwrite_mode: 路径冲突时是否覆盖
        """
        self.mark_dirty()
        keys = key.split('.')
        node = self._data

        for k in keys[:-1]:
            if isinstance(node, ConfigNode):
                if k not in node.data or not isinstance(node.data[k], dict):
                    if overwrite_mode:
                        node[k] = {}  # 修改点
                    else:
                        raise KeyError(
                            f"Key '{k}' not found. Use overwrite_mode=True to create missing keys.")
            else:
                raise AttributeError(
                    f"Expected ConfigNode, but got {type(node)}. Use overwrite_mode=True to create missing keys.")

            node = getattr(node, k)

        # 检查最后一个键是否存在，如果存在且 overwrite_mode 为 False，则报错
        if keys[-1] in node.data and not overwrite_mode:
            raise ValueError(
                f"Key '{keys[-1]}' already exists. Use overwrite_mode=True to overwrite.")

        setattr(node, keys[-1], value)

        if self.auto_save:
            self.save()

    def del_clean(self):
        """清空所有配置并删除配置文件。"""
        self.mark_dirty()
        with self._lock:
            if os.path.exists(self._file):
                try:
                    os.remove(self._file)
                    self._data = ConfigNode({}, manager=self)
                    return True
                except OSError as e:
                    print(f"清除配置文件 {self._file} 失败：{e}")
                    return False
            else:
                return False

    def update(self, data):
        """
        批量更新配置项。
        :param data: dict，支持点号路径
        """
        self.mark_dirty()
        self._recursive_update(self._data.data, data)
        if self.auto_save:
            self.save()

    def set_data(self, data):
        """
        用 dict 完全替换配置数据。
        :param data: 新配置 dict
        """
        self.mark_dirty()
        self._data = ConfigNode(data, manager=self)
        if self.auto_save:
            self.save()

    def del_key(self, key):
        """
        删除指定配置项，支持点号路径。
        :param key: 配置项路径
        """
        self.mark_dirty()
        keys = key.split('.')
        if not keys:
            return
        node = self._data
        parent_nodes = []
        for k in keys[:-1]:
            parent_nodes.append((node, k))
            node = getattr(node, k, None)
            if node is None:
                return
        final_key = keys[-1]
        if final_key in node.data:
            del node.data[final_key]
            while parent_nodes:
                parent, key_in_parent = parent_nodes.pop()
                if not parent[key_in_parent].data:
                    del parent[key_in_parent]
                else:
                    break
            if self.auto_save:
                self.save()

    def _load(self):
        """从文件加载配置。"""
        with self._lock:
            try:
                with open(self._file, 'rb' if self._way == "json" else 'r',
                          encoding=None if self._way == "json" else 'utf-8') as f:
                    raw_data = f.read()
                    
                    # 如果设置了密码，先解密
                    if self._key:
                        raw_data = self._decrypt_data(raw_data)
                    else:
                        # 没有密码时，使用原来的方式加载
                        f.seek(0)  # 重置文件指针
                        raw_data = self._handler.load(f)
                    
                    self._data = ConfigNode(raw_data, manager=self)
            except FileNotFoundError as e:
                print(f"配置文件 {self._file} 未找到：{e}")
            except Exception as e:
                print(f"加载配置文件 {self._file} 失败：{e}")

    def load(self, file=None, way=None):
        """
        切换配置文件或格式（不自动加载内容）。
        :param file: 新文件名
        :param way: 新格式
        """
        if file:
            self._file = file
        if way:
            self._way = way.lower()
            self._handler = ConfigHandlerFactory.get_handler(self._way)

    def mark_dirty(self):
        """标记配置已更改。"""
        self._dirty = True

    def save(self):
        """保存配置到文件。"""
        with self._lock:
            if not self._dirty:
                return
            try:
                self._ensure_file_exists()
                
                # 获取配置数据
                config_data = self._data.to_dict()
                
                # 如果设置了密码，先加密
                if self._key:
                    encrypted_data = self._encrypt_data(config_data)
                    with open(self._file, 'wb') as f:
                        f.write(encrypted_data)
                else:
                    # 没有密码时，使用原来的方式保存
                    with open(self._file, 'wb' if self._way in ["json", "xml"] else 'w',
                              encoding=None if self._way in ["json", "xml"] else 'utf-8') as f:
                        self._handler.save(config_data, f)
                
                self._dirty = False
            except Exception as e:
                print(f"保存配置文件失败 {self._file}: {e}")

    def save_to_file(self, file=None, way=None):
        """
        另存为指定文件和格式。
        :param file: 目标文件
        :param way: 目标格式
        """
        # 使用局部变量来存储文件路径和格式
        target_file = self.ensure_extension(file) if file else self._file
        target_way = self.validate_format(way) if way else self._way
        target_handler = ConfigHandlerFactory.get_handler(target_way)

        # 确保文件存在
        self._ensure_file_exists()

        with self._lock:
            try:
                # 获取配置数据
                config_data = self._data.to_dict()
                
                # 如果设置了密码，先加密
                if self._key:
                    encrypted_data = self._encrypt_data(config_data)
                    with open(target_file, 'wb') as f:
                        f.write(encrypted_data)
                else:
                    # 没有密码时，使用原来的方式保存
                    with open(target_file, 'wb' if target_way == "json" else 'w',
                              encoding=None if target_way == "json" else 'utf-8') as f:
                        target_handler.save(config_data, f)

                print(f"配置已成功另存到 {target_file}")
            except Exception as e:
                print(f"另存配置文件失败 {target_file}: {e}")

    def _ensure_file_exists(self):
        """确保配置文件存在。"""
        if not os.path.exists(self._file):
            with open(self._file, 'w'):
                pass  # 创建一个空文件



    def _recursive_update(self, original, new_data):
        """
        递归更新配置，支持点号路径。
        :param original: 原始 dict
        :param new_data: 新数据 dict
        """
        for key, value in new_data.items():
            if '.' in key:
                keys = key.split('.')
                current = original
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = value
            elif isinstance(value, dict) and isinstance(original.get(key, None), dict):
                self._recursive_update(original[key], value)
            else:
                if original.get(key) != value:
                    original[key] = value
                    self.mark_dirty()

    @staticmethod
    def validate_format(_way):
        """
        校验并返回合法格式名。
        :param _way: 格式名
        """
        _way = _way.lower()
        way_list = ['json', 'toml', 'yaml', 'ini', 'xml']  # 修复：将 way_list 定义为局部变量
        if _way not in way_list:
            raise ValueError(f"Unsupported format: {_way}. Supported formats are: {', '.join(way_list)}")
        return _way

    def ensure_extension(self, file):
        """
        确保文件名有正确扩展名，并创建必要的目录。
        :param file: 文件名
        """
        # 确保目录存在
        dir_name = os.path.dirname(file)
        if dir_name and not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name)  # 递归创建目录
            except OSError as e:
                print(f"创建目录 {dir_name} 失败: {e}")
                # 目录创建失败，不继续执行，直接返回原文件名
                return file

        # 确保文件有扩展名
        if not os.path.splitext(file)[1]:
            file += f".{self._way}"
        return file

    def __str__(self):
        """str(self)"""
        return str(self.dict)

    def __repr__(self):
        """repr(self)"""
        return repr(self.dict)

    def __getattr__(self, item):
        """属性访问代理到配置数据。"""
        return getattr(self._data, item)

    def __getitem__(self, item):
        """dict 方式访问配置数据。"""
        return self._data[item]

    def __call__(self, key, value=None):
        """cc(key) 等价于 cc.read(key, value)"""
        return self.read(key, value)

    def __len__(self):
        """配置项数量。"""
        return len(self._data)

    def __iter__(self):
        """遍历配置项。"""
        return iter(self._data)

    def __contains__(self, item):
        """判断配置项是否存在。"""
        return item in self._data

    def __bool__(self):
        """配置是否非空。"""
        return bool(self._data)

    def __enter__(self):
        """上下文管理器 enter。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器 exit，自动保存。"""
        self.save()

    def __setattr__(self, key, value):
        """属性赋值代理到配置数据，内部属性用 _ 前缀。"""
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            setattr(self._data, key, value)

    def __delattr__(self, key):
        """属性删除代理到配置数据。"""
        if key.startswith('_'):
            super().__delattr__(key)
        else:
            if hasattr(self._data, key):
                delattr(self._data, key)
                self.mark_dirty()
                if self.auto_save:
                    self.save()
            else:
                raise AttributeError(f"'Config' object has no attribute '{key}'")

    def __setitem__(self, key, value):
        """
        实现字典方式赋值
        """
        keys = key.split('.')
        node = self._data
        for k in keys[:-1]:
            if k not in node.data:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self.mark_dirty()
        if self.auto_save:
            self.save()


class ConfigHandler:
    """
    配置文件处理器基类。
    """

    def load(self, file):
        """加载配置文件。"""
        raise NotImplementedError

    def save(self, data, file):
        """保存配置文件。"""
        raise NotImplementedError


class JSONConfigHandler(ConfigHandler):
    """
    JSON 配置文件处理器。
    """

    def load(self, file):
        """加载 JSON 配置。"""
        return orjson.loads(file.read())

    def save(self, data, file):
        """保存 JSON 配置。"""
        file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


class TOMLConfigHandler(ConfigHandler):
    """
    TOML 配置文件处理器。
    """

    def load(self, file):
        """加载 TOML 配置。"""
        return toml.load(file)

    def save(self, data, file):
        """保存 TOML 配置。"""
        file.write(toml.dumps(data))


class YAMLConfigHandler(ConfigHandler):
    """
    YAML 配置文件处理器。
    """

    def load(self, file):
        """加载 YAML 配置。"""
        return yaml.safe_load(file)

    def save(self, data, file):
        """保存 YAML 配置。"""
        yaml.dump(data, file, allow_unicode=True)


class INIConfigHandler(ConfigHandler):
    """
    INI 配置文件处理器。
    """

    def load(self, file):
        """加载 INI 配置。"""
        config = configparser.ConfigParser()
        config.read_file(file)
        return {s: dict(config.items(s)) for s in config.sections()}

    def save(self, data, file):
        """保存 INI 配置。"""
        config = configparser.ConfigParser()
        # 如果 data 不是嵌套字典，包装在一个默认的 section 中
        if not (data and all(isinstance(v, dict) for v in data.values())):
            data = {'默认': data}
        config.read_dict(data)
        config.write(file)


class XMLConfigHandler(ConfigHandler):
    """
    XML 配置文件处理器。
    """

    def load(self, file):
        """加载 XML 配置。"""
        tree = ElementTree.parse(file)
        root = tree.getroot()
        return self._element_to_dict(root)

    def save(self, data, file):
        """保存 XML 配置。"""
        root = self._dict_to_element('config', data)
        tree = ElementTree.ElementTree(root)
        tree.write(file, encoding='utf-8', xml_declaration=True)

    def _element_to_dict(self, element):
        """递归解析 XML 元素为 dict。"""
        data = {}
        for child in element:
            if len(child):
                data[child.tag] = self._element_to_dict(child)
            else:
                data[child.tag] = child.text
        return data

    def _dict_to_element(self, tag, data):
        """递归将 dict 转为 XML 元素。"""
        element = ElementTree.Element(tag)
        for key, value in data.items():
            if isinstance(value, dict):
                child = self._dict_to_element(key, value)
            else:
                child = ElementTree.Element(key)
                child.text = str(value)
            element.append(child)
        return element


class ConfigHandlerFactory:
    handlers = {
        'json': JSONConfigHandler(),
        'toml': TOMLConfigHandler(),
        'yaml': YAMLConfigHandler(),
        'ini': INIConfigHandler(),
        'xml': XMLConfigHandler(),  # Added XML handler
    }

    @staticmethod
    def get_handler(_format):
        handler = ConfigHandlerFactory.handlers.get(_format)
        if not handler:
            raise ValueError(f"Unsupported format: {_format}")
        return handler


class ConfigNode(MutableMapping):
    """
    配置节点，支持嵌套字典结构与自动保存。
    """

    def __init__(self, data=None, manager=None, parent=None, key_in_parent=None):
        """
        初始化配置节点。
        :param data: 节点数据（dict）
        :param manager: 顶层 Config 实例
        :param parent: 父节点
        :param key_in_parent: 在父节点中的键名
        """
        self._data = data if data is not None else {}
        self._manager = manager
        self._parent = parent
        self._key_in_parent = key_in_parent

    @property
    def data(self):
        """节点数据（dict）。"""
        return self._data

    @data.setter
    def data(self, value):
        """设置节点数据并自动保存。"""
        self._data = value
        self._trigger_save()

    def _trigger_save(self):
        """触发自动保存。"""
        if self._manager:
            self._manager.mark_dirty()
            if self._manager.auto_save:
                self._manager.save()

    def __setitem__(self, key, value):
        """设置子项并自动保存。"""
        self._data[key] = value
        self._trigger_save()

    def __delitem__(self, key):
        """删除子项并自动保存。"""
        if key in self._data:
            del self._data[key]
            self._trigger_save()
        else:
            raise KeyError(f"Key '{key}' not found.")

    def __iter__(self):
        """遍历所有子项。"""
        return iter(self._data)

    def __len__(self):
        """子项数量。"""
        return len(self._data)

    def __getattr__(self, key):
        """属性方式访问子项。"""
        if key in self._data:
            value = self._data[key]
            if isinstance(value, dict):
                return ConfigNode(value, manager=self._manager, parent=self, key_in_parent=key)
            else:
                return value
        else:
            self._data[key] = {}
            return ConfigNode(self._data[key], manager=self._manager, key_in_parent=key)

    def __setattr__(self, key, value):
        """属性方式设置子项，内部变量用 _ 前缀。"""
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._data[key] = value
            # 递归找到最顶层的 manager 并触发保存
            node = self
            while hasattr(node, '_parent') and node._parent is not None:
                node = node._parent
            if hasattr(node, '_manager') and node._manager is not None:
                node._manager.mark_dirty()
                if node._manager.auto_save:
                    node._manager.save()

    def to_dict(self):
        """递归转为 dict。"""
        return {key: (value.to_dict() if isinstance(value, ConfigNode) else value)
                for key, value in self._data.items()}

    def __repr__(self):
        """repr(self)"""
        return repr(self.to_dict())

    def __delattr__(self, key):
        """属性方式删除子项并自动保存。"""
        if key in self._data:
            del self._data[key]
            self._trigger_save()
        else:
            raise AttributeError(f"Attribute '{key}' not found.")

    def __getitem__(self, key):
        """获取子项或子节点。"""
        keys = key.split('.')
        node = self._data
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
                if node is None:
                    raise KeyError(f"Key '{key}' not found.")
            else:
                raise KeyError(f"Key '{key}' not found.")

        if isinstance(node, dict):
            return ConfigNode(node, manager=self._manager, parent=self, key_in_parent=key)
        else:
            return node


if __name__ == "__main__":
    pass
