# confull

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [En](https://github.com/zisull/confull/blob/main/doc/README-en.md)

## 一、概述

`confull` 是多格式配置管理工具，支持在 `dict` 与 `ini`、`xml`、`json`、`toml`、`yaml` 等格式之间进行读写操作，并能自动保存配置。它提供了便捷的接口来管理配置数据，还可根据需求切换配置文件和格式。

### 安装

在命令行中运行以下命令来安装 `confull`：

```cmd
pip install confull
```

## 二、类和方法说明

### 1. `Config` 类

该类是配置管理器的核心，负责配置数据的读写、保存等操作。

#### 初始化方法 `__init__`

```python
def __init__(self, data: dict = None, file: str = "config", way: str = "toml", replace: bool = False,
             auto_save: bool = True, backup: bool = False):
```

- 参数说明

  ：

  - `data`：初始配置数据，类型为 `dict`，默认为 `None`。
  - `file`：配置文件名（可无扩展名），默认为 `"config"`。若指定的目录不存在，会自动创建。
  - `way`：配置文件格式，支持 `json`、`toml`、`yaml`、`ini`、`xml`，默认为 `"toml"`。
  - `replace`：是否覆盖已有配置文件，布尔值，默认为 `False`。
  - `auto_save`：是否自动保存，布尔值，默认为 `True`。
  - `backup`：是否备份原配置文件，布尔值，默认为 `False`。

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

## 三、使用示例

```python
from confull import Config

# 1. 初始化配置管理器
# 使用默认参数初始化
cc = Config()

# 使用自定义参数初始化
initial_data = {'app': {'name': 'MyApp', 'version': '1.0'}}
cc = Config(data=initial_data, file='custom_config', way='json', replace=False, auto_save=True, backup=True)

# 2. 基本读写操作
# 使用点号路径写入配置项
cc.write('database.host', 'localhost')

# 使用点号路径读取配置项
host = cc.read('database.host')
print(f"Database host (using read method): {host}")

# 使用属性方式写入配置项
cc.database.port = 5432
# 使用属性方式读取配置项
port = cc.database.port
print(f"Database port (using attribute access): {port}")

# 使用字典方式写入配置项
cc['database.user'] = 'admin'
# 使用字典方式读取配置项
user = cc['database.user']
print(f"Database user (using dict access): {user}")

# 3. 批量更新配置项
new_data = {'app': {'name': 'NewApp', 'version': '2.0'}, 'new_key': 'new_value'}
cc.update(new_data)
print("Updated config:", cc.dict)

# 4. 保存和另存配置文件
# 保存配置文件
cc.save()

# 另存为指定文件和格式
cc.save_to_file(file='backup_config', way='yaml')

# 5. 删除配置项和清空配置
# 删除配置项
cc.del_key('database.host')
del cc.database.port
del cc['database.user']

# 清空配置并删除文件
cc.del_clean()

# 6. 切换配置文件或格式
cc.load(file='new_config', way='toml')

# 7. 标记配置已更改并手动保存
cc.mark_dirty()
cc.save()

# 8. 使用上下文管理器
with Config(data={'example': 'value'}, file='context_config', way='toml') as config:
    config.write('example', 'new_value')
    # 离开上下文时自动保存

# 9. 使用 __del__ 魔法函数
temp_config = Config(data={'test': 'data'}, file='del_test', way='json')
# 当 temp_config 对象被销毁时，若 auto_save 为 True，会自动保存配置
del temp_config

# 10. 使用 dict 属性批量设置和获取配置数据
cc = Config()
cc.dict = {'location': 'Beijing', 'books': {'quantity': 100, 'price': 10.5}, 'students': {'quantity': 1000, 'age': 20}}
print("Config data using dict property:", cc.dict)

# 11. 使用强制覆写模式
dic_ = {'school': 'pass'}
cc = Config(data=dic_)
cc.write('school.university', 'University', overwrite_mode=True)  # overwrite_mode=True 强制覆写，但会导致原路径被删除
print("Config after forced overwrite:", cc.dict)

# 12. 检查配置项是否存在
print("Does 'school' exist in cc?", 'school' in cc)

# 13. 遍历配置项
for key in cc:
    print(f"Key: {key}, Value: {cc[key]}")

# 14. 获取配置项数量
print("Number of configuration items:", len(cc))

# 15. 使用 __call__ 方法
value = cc('school.university')
print(f"Value of 'school.university' using __call__: {value}")

# 16. 检查配置是否非空
print("Is cc non-empty?", bool(cc))

# 17. 使用 pop 方法删除并返回指定键的值
cc = Config(data={'a': 1, 'b': 2})
popped_value = cc.pop('a')
print(f"Popped value: {popped_value}, Remaining config: {cc.dict}")

# 18. 使用 clear 方法清空配置数据
cc.clear()
print("Config after clear:", cc.dict)

# 19. 使用 get 方法安全地获取配置项
default_value = cc.get('non_existent_key', 'default')
print(f"Value of non-existent key using get: {default_value}")
```

四、注意事项

- 当使用 `write`、`update`、`set_data`、`del_key` 等方法修改配置数据时，若 `auto_save` 为 `True`，会自动保存配置文件。
- 若配置文件格式不支持，会抛出 `ValueError` 异常。
- 在使用 `INIConfigHandler` 保存配置时，若数据不是嵌套字典，会将其包装在一个默认的 `'默认'` 节中。

## 尾语

作者水平有限，尽可能简化配置文件的读写流程，让使用者可以用一种更加直观、便捷的方式去操作配置信息。

2024 年 11 月 19 日 zisull@qq.com
