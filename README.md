# confull

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [En](https://github.com/zisull/confull/blob/main/README-en.md)

## 目录

- [主要特性](#主要特性)
- [变更说明](#变更说明)
- [使用示例](#使用示例)
- [安装](#安装)
- [类和方法说明](#类和方法说明)

## 一、概述

`confull` 是一款多格式配置管理工具，支持在 `dict` 与 `ini`、`xml`、`json`、`toml`、`yaml` 等格式之间进行读写操作，并能自动保存配置。提供便捷的接口管理配置数据，并可根据需求灵活切换配置文件和格式。

### 主要特性

- 支持多种配置文件格式：json、toml、yaml、ini、xml
- 支持 dict <=> 配置文件的自动转换
- 支持点号路径（如 a.b.c）方式的访问和写入
- 支持自动保存
- 支持加密存储（传入 pwd 参数即可自动加密和解密配置文件）
- 线程安全
- 代码简洁，易于集成

### 变更说明

- **已移除备份功能**，简化配置管理。
- **新增加密功能**，只需传入 `pwd` 参数，即可自动加密和解密配置文件。

### 使用示例

```python
from confull import Config

# 1. 普通用法
cc = Config()
cc.write('user', 'admin')
print(cc.read('user'))  # admin

# 2. 加密用法
cc = Config(file='secure.toml', way='toml', pwd='123456')
cc.write('token', 'xyz')
print(cc.read('token'))  # xyz

# 3. 点路径写入和读取
cc.write('db.host', '127.0.0.1', overwrite_mode=True)
cc.write('db.port', 3306, overwrite_mode=True)
print(cc.read('db.host'))  # 127.0.0.1
print(cc.read('db.port'))  # 3306

# 4. dict方式批量赋值
cc.dict = {'user': 'root', 'password': 'pass'}
print(cc['user'])  # root

# 5. 属性方式赋值和读取
cc.site = 'mysite'
print(cc.site)  # mysite

# 6. 删除配置项
cc.del_key('user')
print(cc.read('user'))  # None

# 7. 批量更新
cc.update({'email': 'a@b.com', 'db.host': 'localhost'})
print(cc.read('email'))  # a@b.com
print(cc.read('db.host'))  # localhost

# 8. 清空并删除配置文件
cc.del_clean()

# 9. 另存为其他格式
cc = Config({'user': 'admin'}, file='a.toml', way='toml')
cc.save_to_file(file='a.yaml', way='yaml')
```

---

## 二、安装

在命令行中运行以下命令来安装 `confull`：

```bash
pip install orjson toml pyyaml
```

---

## 三、类和方法说明

### 1. `Config` 类

该类是配置管理器的核心，负责配置数据的读写、保存等操作。

#### 初始化方法 `__init__`

```python
def __init__(self, data: dict = None, file: str = "config", way: str = "toml", replace: bool = False,
             auto_save: bool = True, pwd: str = None):
```
- 新增参数 `pwd`，用于加密配置文件。
- 已移除参数 `backup`。

#### 属性

| 属性名          | 描述                                                   |
| --------------- | ------------------------------------------------------ |
| `json`          | 以 json 字符串格式返回配置数据。                       |
| `dict`          | 以 `dict` 格式返回配置数据，也可用于批量设置配置数据。 |
| `auto_save`     | 是否自动保存，可读写属性。                             |
| `backup`        | 是否备份原配置文件，可读写属性。                       |
| `str`           | 以字符串格式返回配置数据。                             |
| `file_path`     | 配置文件路径。                                         |
| `file_path_abs` | 配置文件绝对路径。                                     |

#### 方法

| 方法名                                                 | 描述                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------ |
| `read(key: str, default=None)`                         | 读取配置项，支持点号路径，如 `a.b.c`。若配置项不存在，返回默认值。 |
| `write(key: str, value, overwrite_mode: bool = False)` | 写入配置项，支持点号路径。若 `overwrite_mode` 为 `True`，路径冲突时会覆盖。写入后若 `auto_save` 为 `True`，则自动保存。 |
| `del_clean()`                                          | 清空所有配置并删除配置文件。                                 |
| `update(data: dict)`                                   | 批量更新配置项，支持点号路径。更新后若 `auto_save` 为 `True`，则自动保存。 |
| `set_data(data: dict)`                                 | 用 `dict` 完全替换配置数据。替换后若 `auto_save` 为 `True`，则自动保存。 |
| `del_key(key: str)`                                    | 删除指定配置项，支持点号路径。删除后若 `auto_save` 为 `True`，则自动保存。 |
| `_load()`                                              | 从文件加载配置，内部方法。                                   |
| `load(file: str = None, way: str = None)`              | 切换配置文件或格式（不自动加载内容）。                       |
| `mark_dirty()`                                         | 标记配置已更改。                                             |
| `save()`                                               | 保存配置到文件。                                             |
| `save_to_file(file: str = None, way: str = None)`      | 另存为指定文件和格式。                                       |
| `_ensure_file_exists()`                                | 确保配置文件存在，内部方法。                                 |
| `_backup_file()`                                       | 备份原配置文件，内部方法。                                   |
| `_recursive_update(original, new_data)`                | 递归更新配置，支持点号路径，内部方法。                       |
| `validate_format(_way)`                                | 校验并返回合法格式名，静态方法。                             |
| `ensure_extension(file)`                               | 确保文件名有正确扩展名。                                     |

#### 魔法方法

| 魔法方法名                                  | 描述                                                   |
| ------------------------------------------- | ------------------------------------------------------ |
| `__del__()`                                 | 对象销毁时，若 `auto_save` 为 `True`，会自动保存配置。 |
| `__getattr__(self, item)`                   | 属性访问代理到配置数据。                               |
| `__getitem__(self, item)`                   | `dict` 方式访问配置数据。                              |
| `__call__(self, key, value=None)`           | `cc(key)` 等价于 `cc.read(key, value)`。               |
| `__len__(self)`                             | 配置项数量。                                           |
| `__iter__(self)`                            | 遍历配置项。                                           |
| `__contains__(self, item)`                  | 判断配置项是否存在。                                   |
| `__bool__(self)`                            | 配置是否非空。                                         |
| `__enter__(self)`                           | 上下文管理器 `enter`。                                 |
| `__exit__(self, exc_type, exc_val, exc_tb)` | 上下文管理器 `exit`，自动保存。                        |
| `__setattr__(self, key, value)`             | 属性赋值代理到配置数据，内部属性用 `_` 前缀。          |
| `__delattr__(self, key)`                    | 属性删除代理到配置数据。                               |

---

如有建议或问题欢迎 issue/PR！