# ConfuLL

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [AI](https://github.com/zisull/confull/blob/main/doc/README-ai-zh.md)


> 一个轻量级、功能强大的多格式配置管理工具

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**ConfuLL** 让配置管理变得简单直观。它支持 dict 与 json/toml/yaml/ini/xml 之间的无缝转换，提供属性访问、点路径操作、自动保存、加密保护等丰富功能。

---

## 目录

- [安装方法](#安装方法)
- [概述](#概述)
- [特性优点](#特性优点)
- [注意事项](#注意事项)
- [常见用法举例](#常见用法举例)
- [核心方法简介](#核心方法简介)
- [详细函数用法及预期效果](#详细函数用法及预期效果)
- [高级用法及技巧](#高级用法及技巧)

---

## 安装方法

### 使用 pip 安装（推荐）

```bash
pip install confull
```

### 从源码安装

```bash
git clone https://github.com/zisull/confull.git
cd confull
pip install .
```

### 依赖说明

| 依赖包 | 版本要求 | 用途 |
|--------|----------|------|
| orjson | >=3.10 | JSON 高性能序列化 |
| toml | >=0.10 | TOML 格式支持 |
| PyYAML | >=6.0 | YAML 格式支持 |
| watchdog | >=6.0 | 文件监听（可选） |
| portalocker | >=3.0 | 进程锁（可选） |
| cryptography | >=42.0 | 加密功能（可选） |

---

## 概述

ConfuLL 是一个 Python 配置管理库，核心设计理念是**简单易用**。

### 核心概念

```python
from confull import Config

# 创建配置 - 就是这么简单
cfg = Config('app.toml')

# 像使用字典一样使用
cfg.name = "MyApp"
cfg.version = "1.0.0"

# 支持点路径访问嵌套配置
cfg.set('database.host', 'localhost')
cfg.set('database.port', 3306)

# 自动保存，无需手动调用
```

### 支持的配置格式

| 格式 | 扩展名 | 特点 |
|------|--------|------|
| TOML | .toml | 人类友好，推荐使用 |
| JSON | .json | 通用性强 |
| YAML | .yaml/.yml | 层次清晰 |
| INI | .ini | 简单配置 |
| XML | .xml | 结构化数据 |

---

## 特性优点

### 🚀 轻量简洁
- 零配置开箱即用
- 自动推断文件格式
- 自动创建目录和文件

### 💡 多种访问方式
```python
# 属性方式
cfg.name = "app"

# 字典方式
cfg['name'] = "app"

# 点路径方式
cfg.set('db.host', 'localhost')

# 链式操作
cfg.set('db.host', 'localhost').set('db.port', 3306)
```

### 🔒 安全可靠
- 线程安全（RLock）
- 进程安全可选（portalocker）
- 加密存储（Fernet + PBKDF2）
- 原子写入（临时文件替换）

### 📁 文件监听
```python
cfg = Config('config.toml')
cfg.enable_watch()  # 外部修改后自动重载
```

### 🔄 自动保存
- 默认开启自动保存
- 支持去抖延迟（防止频繁写入）
- 程序退出时确保写盘

### 🎯 键名冲突保护
```python
cfg = Config({'save': True, 'path': '/tmp'})
# cfg.save  # ❌ 会调用 save() 方法
cfg.opt.save  # ✅ 安全访问冲突键
```

---

## 注意事项

### 1. 键名冲突

以下名称为保留关键字，不能直接作为顶层配置键：

| 保留名 | 说明 |
|--------|------|
| `to_dict` | 转换为字典 |
| `to_json` | 转换为 JSON |
| `save` | 保存配置 |
| `load` | 加载配置 |
| `reload` | 重新加载 |
| `get` | 获取值 |
| `set` | 设置值 |
| `del_clean` | 清空配置 |
| `opt` | 安全访问接口 |

**解决方案：**
```python
# 使用 opt 属性访问
cfg.opt.save = True
cfg.opt.path = '/tmp'

# 或者放到子节点中
cfg.app.save = True
```

### 2. 自动保存行为

默认情况下，任何修改都会自动保存到文件。如需批量操作：

```python
# 方法1：关闭自动保存
cfg = Config('app.toml', auto_save=False)
# ... 批量操作 ...
cfg.save()  # 手动保存

# 方法2：使用上下文管理器
with Config('app.toml', auto_save=False) as cfg:
    cfg.name = "app"
    cfg.version = "1.0"
# 退出时自动保存

# 方法3：使用去抖延迟
cfg = Config('app.toml', debounce_ms=100)  # 100ms 内只保存一次
```

### 3. 加密配置

- 密码丢失将无法恢复数据
- 修改密码需要先用旧密码读取，再用新密码保存
- 加密文件被篡改会触发校验错误

### 4. 文件格式推断

```python
# 自动推断
Config('app.toml')      # TOML 格式
Config('app.json')      # JSON 格式
Config('app')           # 默认 TOML

# 显式指定（优先级更高）
Config('data.txt', way='toml')  # 使用 TOML 格式读写 .txt 文件
```

---

## 常见用法举例

### 基础用法

```python
from confull import Config

# 创建配置
cfg = Config('app.toml')

# 设置值
cfg.name = "MyApp"
cfg.version = "1.0.0"
cfg.debug = False

# 获取值
print(cfg.name)     # "MyApp"
print(cfg.version)  # "1.0.0"

# 删除值
del cfg.debug
```

### 嵌套配置

```python
# 创建嵌套结构
cfg.set('database.host', 'localhost')
cfg.set('database.port', 3306)
cfg.set('database.user', 'root')
cfg.set('database.password', 'secret')

# 访问嵌套值
print(cfg.database.host)    # "localhost"
print(cfg.get('database.port'))  # 3306

# 使用点路径删除
cfg.del_key('database.password')
```

### 批量操作

```python
# 批量更新
cfg.update({
    'app.name': 'MyApp',
    'app.version': '2.0.0',
    'debug': True
})

# 完全替换数据
cfg.set_data({
    'name': 'NewApp',
    'version': '3.0.0'
})
```

### 加密配置

```python
# 创建加密配置
cfg = Config('secure.toml', pwd='my-secret-password')
cfg.token = "abc123"
cfg.api_key = "sk-xxxx"

# 读取加密配置（需要密码）
cfg = Config('secure.toml', pwd='my-secret-password')
print(cfg.token)  # "abc123"

# 错误密码会抛出异常
cfg = Config('secure.toml', pwd='wrong')  # ConfigEncryptionError
```

### 文件监听

```python
cfg = Config('config.toml')
cfg.enable_watch()

# 当 config.toml 被外部修改时，cfg 会自动重载
# ...

cfg.disable_watch()  # 关闭监听
```

### 另存为其他格式

```python
cfg = Config('app.toml')
cfg.to_file('app.json', way='json')
cfg.to_file('app.yaml', way='yaml')
cfg.to_file('backup.txt', way='toml')
```

---

## 核心方法简介

### 读写操作

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get(key, default)` | 获取配置值 | 值或默认值 |
| `set(key, value)` | 设置配置值 | Config（支持链式） |
| `setdefault(key, value)` | 设置默认值（不存在时） | 最终值 |
| `first(*keys, default)` | 获取第一个存在的键值 | 值或默认值 |
| `require(key)` | 获取必需配置项 | 值（不存在则报错） |

### 批量操作

| 方法 | 说明 |
|------|------|
| `update(dict)` | 批量更新 |
| `set_data(dict)` | 完全替换 |
| `merge(other, strategy)` | 合并配置 |

### 删除操作

| 方法 | 说明 |
|------|------|
| `del_key(key)` | 删除指定键（支持点路径） |
| `del_clean()` | 清空并删除配置文件 |

### 文件操作

| 方法 | 说明 |
|------|------|
| `save()` | 保存到文件 |
| `reload()` | 从文件重新加载 |
| `to_file(file, way)` | 另存为其他文件/格式 |

### 导入导出

| 方法 | 说明 |
|------|------|
| `to_dict()` | 导出为字典 |
| `to_json(indent)` | 导出为 JSON 字符串 |
| `to_env(prefix)` | 导出为环境变量格式 |
| `from_env(prefix)` | 从环境变量导入 |

### 比较操作

| 方法 | 说明 |
|------|------|
| `diff(other)` | 比较两个配置的差异 |

### 监听操作

| 方法 | 说明 |
|------|------|
| `enable_watch()` | 开启文件监听 |
| `disable_watch()` | 关闭文件监听 |

### 状态查询

| 方法 | 说明 |
|------|------|
| `path()` | 获取文件路径（绝对） |
| `path_abs()` | 获取文件路径（绝对） |
| `is_auto_save()` | 是否自动保存 |
| `set_auto_save(flag)` | 设置自动保存 |

---

## 详细函数用法及预期效果

### 1. 初始化 `__init__`

```python
Config(
    data=None,           # 初始数据（dict）
    file="config",       # 文件名（可无扩展名）
    way="",              # 格式（json/toml/yaml/ini/xml）
    replace=False,       # 是否覆盖已有文件
    auto_save=True,      # 是否自动保存
    pwd=None,            # 加密密码
    process_safe=False,  # 是否进程安全
    debounce_ms=0,       # 去抖延迟（毫秒）
    env=None,            # 环境名称（如 'dev', 'production'）
    env_prefix="",       # 环境变量前缀（如 'APP'）
    schema=None          # 类型验证 schema
)
```

**示例：**
```python
# 最简用法
cfg = Config()

# 指定文件
cfg = Config('app.toml')

# 带初始数据
cfg = Config({'name': 'app', 'version': '1.0'}, file='app.toml')

# 加密配置
cfg = Config('secure.toml', pwd='secret')

# 进程安全 + 去抖
cfg = Config('shared.toml', process_safe=True, debounce_ms=100)

# 多环境切换
cfg = Config('app.toml', env='production')
# 自动加载 app.production.toml

# 环境变量覆盖
cfg = Config('app.toml', env_prefix='MYAPP_')
# 自动导入 MYAPP_* 环境变量

# 类型验证
schema = {'port': int, 'debug': bool, 'name': str}
cfg = Config('app.toml', schema=schema)
cfg.port = 8080      # ✅ 正常
cfg.port = "8080"    # ❌ 报错：期望 int，得到 str
# 3. 导入 MYAPP_* 环境变量（最高优先级）
```

**预期效果：**
- 自动创建目录和文件
- 自动推断格式（根据扩展名）
- 程序退出时自动保存
- 支持多环境配置切换

---

### 2. 获取值 `get`

```python
get(key: str, default: Any = None) -> Any
```

**示例：**
```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})

# 获取简单值
cfg.get('db')           # {'host': 'localhost', 'port': 3306}

# 获取嵌套值（点路径）
cfg.get('db.host')      # 'localhost'
cfg.get('db.port')      # 3306

# 带默认值
cfg.get('db.user', 'root')  # 'root'
cfg.get('cache.enabled')    # None
```

---

### 3. 设置值 `set`

```python
set(key: str, value: Any, overwrite_mode: bool = False) -> Config
```

**示例：**
```python
cfg = Config()

# 设置简单值
cfg.set('name', 'MyApp')

# 设置嵌套值（自动创建中间节点）
cfg.set('db.host', 'localhost')
cfg.set('db.port', 3306)

# 链式操作
cfg.set('app.name', 'MyApp').set('app.version', '1.0').set('debug', True)

# 覆盖模式（当类型冲突时）
cfg.set('config', 'old')           # 叶子节点
cfg.set('config.key', 'value', overwrite_mode=True)  # 转为字典
```

**预期效果：**
- 自动保存到文件
- 返回 self 支持链式操作
- 类型冲突时需要 `overwrite_mode=True`

---

### 4. 设置默认值 `setdefault`

```python
setdefault(key: str, value: Any) -> Any
```

**示例：**
```python
cfg = Config({'version': '1.0.0'})

cfg.setdefault('version', '2.0.0')  # 返回 '1.0.0'（已存在，不覆盖）
cfg.setdefault('name', 'MyApp')     # 返回 'MyApp'（不存在，设置）
```

**预期效果：**
- 键存在时返回原值，不修改
- 键不存在时设置新值并返回

---

### 5. 获取第一个存在的键 `first`

```python
first(*keys, default=None) -> Any
```

**示例：**
```python
cfg = Config({'host': 'localhost', 'server_host': '127.0.0.1'})

# 按优先级查找
cfg.first('server_host', 'host', 'db.host')
# 返回 '127.0.0.1'（第一个存在的键）

cfg.first('missing', 'host', default='0.0.0.0')
# 返回 'localhost'

cfg.first('a', 'b', 'c', default='none')
# 返回 'none'（都不存在）
```

**预期效果：**
- 返回第一个存在且非 None 的值
- 所有键都不存在时返回 default

---

### 6. 获取必需配置 `require`

```python
require(key: str) -> Any
```

**示例：**
```python
cfg = Config({'database_url': 'sqlite:///db.sqlite'})

cfg.require('database_url')  # 返回 'sqlite:///db.sqlite'
cfg.require('api_key')       # 抛出 ConfigValidationError: "必需的配置项 'api_key' 不存在或值为 None"
```

**预期效果：**
- 存在时返回值
- 不存在或值为 None 时抛出 ConfigValidationError

---

### 7. 批量更新 `update`

```python
update(data: Dict[str, Any]) -> None
```

**示例：**
```python
cfg = Config({'app': {'name': 'old'}})

cfg.update({
    'app.name': 'new',
    'app.version': '1.0',
    'debug': True
})

print(cfg.app.name)    # 'new'
print(cfg.app.version) # '1.0'
print(cfg.debug)       # True
```

**预期效果：**
- 支持点路径键名
- 合并到现有配置

---

### 8. 完全替换 `set_data`

```python
set_data(data: Dict[str, Any]) -> None
```

**示例：**
```python
cfg = Config({'old': 'data'})

cfg.set_data({
    'new': 'data',
    'version': '2.0'
})

print(cfg.to_dict())  # {'new': 'data', 'version': '2.0'}
```

**预期效果：**
- 完全替换现有数据
- 旧数据丢失

---

### 9. 合并配置 `merge`

```python
merge(other: Union[Dict, Config], strategy: str = "override") -> Config
```

**策略说明：**
- `override`：覆盖已有值（默认）
- `keep`：保留已有值
- `deep`：深度合并嵌套字典

**示例：**
```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})

# override 策略
cfg.merge({'db': {'host': '127.0.0.1'}, 'debug': True}, strategy='override')
# {'db': {'host': '127.0.0.1'}, 'debug': True}

# keep 策略
cfg = Config({'db': {'host': 'localhost'}})
cfg.merge({'db': {'host': '127.0.0.1'}, 'debug': True}, strategy='keep')
# {'db': {'host': 'localhost'}, 'debug': True}  # host 保留原值

# deep 策略
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})
cfg.merge({'db': {'user': 'root'}, 'debug': True}, strategy='deep')
# {'db': {'host': 'localhost', 'port': 3306, 'user': 'root'}, 'debug': True}
```

**预期效果：**
- 返回 self 支持链式操作
- 根据策略决定如何合并

---

### 10. 比较差异 `diff`

```python
diff(other: Union[Dict, Config]) -> Dict[str, Any]
```

**示例：**
```python
cfg1 = Config({'a': 1, 'b': 2, 'c': 3})
cfg2 = Config({'a': 1, 'b': 99, 'd': 4})

diff = cfg1.diff(cfg2)
# {
#     'added': {'d': 4},
#     'removed': {'c': 3},
#     'modified': {'b': {'old': 2, 'new': 99}}
# }
```

**预期效果：**
- 返回包含 `added`、`removed`、`modified` 的字典
- 支持嵌套字典比较

---

### 11. 删除键 `del_key`

```python
del_key(key: str) -> None
```

**示例：**
```python
cfg = Config({'a': {'b': {'c': 1, 'd': 2}}, 'e': 3})

cfg.del_key('a.b.c')
# {'a': {'b': {'d': 2}}, 'e': 3}  # 自动清理空的父节点

cfg.del_key('e')
# {'a': {'b': {'d': 2}}}
```

**预期效果：**
- 支持点路径
- 自动清理空的父节点

---

### 12. 清空配置 `del_clean`

```python
del_clean() -> bool
```

**示例：**
```python
cfg = Config({'name': 'app'}, file='app.toml')
cfg.del_clean()
# 配置文件被删除，内存清空
```

**预期效果：**
- 删除配置文件
- 清空内存数据
- 返回是否成功

---

### 13. 保存 `save`

```python
save() -> None
```

**示例：**
```python
cfg = Config('app.toml', auto_save=False)
cfg.name = 'app'
cfg.save()  # 手动保存
```

**预期效果：**
- 立即保存到文件
- 忽略去抖延迟

---

### 14. 重新加载 `reload`

```python
reload() -> None
```

**示例：**
```python
cfg = Config('app.toml')
# 外部修改了 app.toml
cfg.reload()  # 重新加载
```

**预期效果：**
- 从磁盘重新加载
- 丢弃未保存的更改

---

### 15. 另存为 `to_file`

```python
to_file(file: str = None, way: str = None) -> None
```

**示例：**
```python
cfg = Config({'name': 'app'}, file='app.toml')

cfg.to_file('backup.json', way='json')
cfg.to_file('backup.yaml', way='yaml')
```

**预期效果：**
- 保存到指定文件
- 可以转换格式

---

### 16. 导出为字典 `to_dict`

```python
to_dict() -> Dict[str, Any]
```

**示例：**
```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})
data = cfg.to_dict()
# {'db': {'host': 'localhost', 'port': 3306}}
```

**预期效果：**
- 返回深拷贝的原生字典
- 修改不影响原配置

---

### 17. 导出为 JSON `to_json`

```python
to_json(indent: int = 2) -> str
```

**示例：**
```python
cfg = Config({'name': 'app', 'version': '1.0'})

print(cfg.to_json())
# {
#   "name": "app",
#   "version": "1.0"
# }

print(cfg.to_json(indent=4))
# 更多缩进
```

**预期效果：**
- 返回 JSON 字符串
- 可自定义缩进

---

### 18. 导出为环境变量 `to_env`

```python
to_env(prefix: str = "", uppercase: bool = True) -> Dict[str, str]
```

**示例：**
```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})

env = cfg.to_env()
# {'DB_HOST': 'localhost', 'DB_PORT': '3306'}

env = cfg.to_env(prefix='APP')
# {'APP_DB_HOST': 'localhost', 'APP_DB_PORT': '3306'}

env = cfg.to_env(uppercase=False)
# {'db_host': 'localhost', 'db_port': '3306'}
```

**预期效果：**
- 嵌套键用下划线连接
- 可添加前缀
- 可控制大小写

---

### 19. 从环境变量导入 `from_env`

```python
from_env(prefix: str = "", separator: str = "_") -> Config
```

**示例：**
```python
import os
os.environ['APP_DB_HOST'] = 'localhost'
os.environ['APP_DB_PORT'] = '3306'

cfg = Config()
cfg.from_env(prefix='APP')

print(cfg.db.host)  # 'localhost'
print(cfg.db.port)  # '3306'
```

**预期效果：**
- 只导入指定前缀的变量
- 自动转换为小写
- 自动创建嵌套结构

---

### 20. 开启文件监听 `enable_watch`

```python
enable_watch() -> None
```

**示例：**
```python
cfg = Config('config.toml')
cfg.enable_watch()

# 当 config.toml 被外部修改时，cfg 会自动 reload()

cfg.disable_watch()  # 关闭监听
```

**预期效果：**
- 监听文件变化
- 自动重新加载

---

### 21. 安全访问接口 `opt`

```python
@property
opt -> _DataProxy
```

**示例：**
```python
cfg = Config({'save': True, 'path': '/tmp'})

# cfg.save  # ❌ 调用的是 save() 方法
cfg.opt.save  # ✅ 访问 'save' 配置项

cfg.opt.path = '/var'  # ✅ 安全修改
```

**预期效果：**
- 避免与方法名冲突
- 支持属性和字典方式访问

---

### 22. 属性访问（魔法方法）

```python
# 支持的魔法方法
cfg.key           # __getattr__
cfg.key = value   # __setattr__
del cfg.key       # __delattr__
cfg['key']        # __getitem__
cfg['key'] = val  # __setitem__
del cfg['key']    # __delitem__
len(cfg)          # __len__
iter(cfg)         # __iter__
'key' in cfg      # __contains__
bool(cfg)         # __bool__
cfg('key')        # __call__ 等价于 cfg.get('key')
```

**示例：**
```python
cfg = Config({'a': 1, 'b': {'c': 2}})

# 属性访问
cfg.a           # 1
cfg.b.c         # 2

# 字典访问
cfg['a']        # 1
cfg['b.c']      # 2（支持点路径）

# 长度
len(cfg)        # 2

# 迭代
for key in cfg:
    print(key)

# 包含判断
'a' in cfg      # True
'b.c' in cfg    # True（支持点路径）

# 调用方式
cfg('a')        # 1
cfg('b.c')      # 2
```

---

### 23. 上下文管理器

```python
__enter__() -> Config
__exit__() -> None  # 自动保存
```

**示例：**
```python
with Config('app.toml', auto_save=False) as cfg:
    cfg.name = 'app'
    cfg.version = '1.0'
# 退出时自动保存
```

---

## 高级用法及技巧

### 技巧 1：使用 .txt 文件存储配置

```python
# 用 toml 格式读写 .txt 文件，方便编辑器打开
cfg = Config('config.txt', way='toml')
cfg.name = 'app'
# 文件内容是 toml 格式，但扩展名是 .txt
```

### 技巧 2：批量操作优化

```python
# 关闭自动保存，批量操作后手动保存
with Config('large.toml', auto_save=False) as cfg:
    for i in range(1000):
        cfg.set(f'item.{i}', f'value_{i}')
# 退出时一次性保存
```

### 技巧 3：配置合并

```python
# 默认配置 + 用户配置
default_cfg = Config('default.toml')
user_cfg = Config('user.toml')

# 用户配置覆盖默认配置
default_cfg.merge(user_cfg, strategy='deep')
```

### 技巧 4：多环境配置切换

```python
# 基础配置 app.toml
# [app]
# name = "MyApp"
# debug = false
# [database]
# host = "localhost"
# port = 3306

# 环境配置 app.production.toml
# [database]
# host = "prod-db.example.com"

# 开发环境
cfg = Config('app.toml', env='dev')
# 自动加载 app.dev.toml（如果存在）

# 生产环境
cfg = Config('app.toml', env='production')
# 自动加载 app.production.toml

# 环境变量覆盖（最高优先级）
cfg = Config('app.toml', env='production', env_prefix='MYAPP_')
# 1. 加载 app.toml
# 2. 加载 app.production.toml
# 3. 导入 MYAPP_* 环境变量
```

**配置优先级（从低到高）：**
1. 基础配置文件（app.toml）
2. 环境配置文件（app.{env}.toml）
3. 环境变量（{env_prefix}*）

### 技巧 5：类型验证

```python
# 定义 schema
schema = {
    'port': int,
    'debug': bool,
    'name': str,
    'database.port': int,  # 支持点路径
    'database.host': str
}

# 创建配置（带类型验证）
cfg = Config('app.toml', schema=schema)

# 正常设置
cfg.port = 8080           # ✅
cfg.set('port', 3306)     # ✅
cfg['port'] = 5432        # ✅

# 类型错误会抛出 ConfigValidationError
cfg.port = "8080"         # ❌ 期望 int，得到 str
cfg.debug = "true"        # ❌ 期望 bool，得到 str
cfg.name = 123            # ❌ 期望 str，得到 int

# 点路径验证
cfg.set('database.port', 'not_a_number')  # ❌ 期望 int，得到 str
```

**支持的验证方式：**
- `cfg.key = value`（属性方式）
- `cfg.set('key', value)`（方法方式）
- `cfg['key'] = value`（字典方式）
- `cfg.update({'key': value})`（批量更新）

### 技巧 6：配置模板

```python
# 创建模板
template = {
    'app': {
        'name': 'MyApp',
        'version': '1.0.0',
        'debug': False
    },
    'database': {
        'host': 'localhost',
        'port': 3306,
        'name': 'mydb'
    }
}

# 基于模板创建配置
cfg = Config(template, file='app.toml')
```

### 技巧 7：环境变量覆盖

```python
# 基础配置
cfg = Config('app.toml')

# 环境变量覆盖（优先级更高）
cfg.from_env(prefix='APP')
```

### 技巧 8：配置加密 + 去抖

```python
# 安全配置，100ms 去抖
cfg = Config(
    'secure.toml',
    pwd='my-secret-key',
    debounce_ms=100
)
```

### 技巧 9：多进程共享配置

```python
# 进程安全模式
cfg = Config('shared.toml', process_safe=True)
```

### 技巧 10：配置版本管理

```python
# 读取配置
cfg = Config('config.toml')

# 修改前备份
cfg.to_file('config.backup.toml')

# 修改配置
cfg.version = '2.0.0'
```

### 技巧 11：链式操作

```python
cfg = Config('app.toml')

# 链式设置
cfg.set('db.host', 'localhost') \
  .set('db.port', 3306) \
  .set('db.user', 'root') \
  .set('db.password', 'secret')

# 链式合并
cfg.merge({'cache': {'enabled': True}}) \
  .merge({'logging': {'level': 'INFO'}})
```

### 技巧 12：配置校验

```python
cfg = Config('app.toml')

# 使用 require 确保必需配置存在
db_url = cfg.require('database.url')
api_key = cfg.require('api.key')

# 使用 setdefault 设置默认值
cfg.setdefault('debug', False)
cfg.setdefault('log_level', 'INFO')
```

### 技巧 13：配置差异比较

```python
# 比较两个版本的配置
old_cfg = Config('config.old.toml')
new_cfg = Config('config.new.toml')

diff = old_cfg.diff(new_cfg)

if diff['modified']:
    print("修改的配置:")
    for key, change in diff['modified'].items():
        print(f"  {key}: {change['old']} -> {change['new']}")
```

### 技巧 14：导出为环境变量

```python
cfg = Config('app.toml')

# 导出为 Docker 环境变量格式
env_vars = cfg.to_env(prefix='MYAPP')
for key, value in env_vars.items():
    print(f"{key}={value}")
```

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
