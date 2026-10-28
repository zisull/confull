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
- [0.2.0 变更说明](#020-变更说明)

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

### 按需安装可选能力

```bash
pip install 'confull[yaml]'      # YAML 支持
pip install 'confull[encrypt]'   # 加密存储（pwd 参数）
pip install 'confull[watch]'     # 文件监听（enable_watch）
pip install 'confull[process]'   # 多进程锁（process_safe）
pip install 'confull[all]'       # 以上全部
```

### 依赖说明

| 依赖包 | 版本要求 | 用途 | 是否必装 |
|--------|----------|------|----------|
| orjson | >=3.10 | JSON 高性能序列化 | 是 |
| toml | >=0.10 | TOML 格式（默认格式） | 是 |
| PyYAML | >=6.0 | YAML 格式支持 | 否，`confull[yaml]` |
| cryptography | >=42.0 | 加密功能 | 否，`confull[encrypt]` |
| watchdog | >=6.0 | 文件监听 | 否，`confull[watch]` |
| portalocker | >=3.0 | 进程锁 | 否，`confull[process]` |

可选依赖全部按需导入：不装 `cryptography` 也能正常读写明文配置，只有真正用到 `pwd` /
`enable_watch` / `process_safe` / `.yaml` 时才会提示安装。

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

### 🎯 键名冲突有明确规则
配置键与库的接口名同名（如 `save`、`items`）时，规则只有一条：**属性写法让路，容器写法放行。**

| 写法 | 遇到同名键时 |
|------|--------------|
| `cfg.save = v`、`cfg.set('save', v)` | 报错并指路，不会悄悄替换掉方法 |
| `cfg['save'] = v`、`cfg.opt.save = v` | 永远可用 |
| `update()` / `merge()` / `set_data()` / `from_env()` / 从文件加载 | 永远可用 |

```python
cfg = Config({'save': True, 'path': '/tmp'})
cfg['save']       # ✅ True
cfg.opt.save      # ✅ True —— opt 只认数据，不认接口
cfg.save          # ⚠️ 拿到的是 save() 方法本身
cfg.save = False  # ❌ 报错，并告诉你可以怎么写
```

---

## 注意事项

### 1. 键名冲突

一个对象只有一套属性命名空间，所以「既能 `cfg.name` 又能 `cfg.save()`」在数学上不可能同时成立。
0.2.0 的做法不是消解冲突，而是把它变成**可预期、可查询、绝不静默**的规则。

**规则：属性写法让路，容器写法放行。**

| 写法 | 语义 | 键名与接口同名时 |
|------|------|------------------|
| `cfg.key = v` | 属性写 | ❌ 抛 `ConfigValidationError`，消息里给出可用写法 |
| `cfg.set('key', v)` | 属性写（同 `cfg.key = v`） | ❌ 同上 |
| `cfg['key'] = v` | 容器写 | ✅ 正常写入 |
| `cfg.opt.key = v` | 容器写 | ✅ 正常写入 |
| `update()` / `merge()` / `set_data()` / `from_env()` / 加载文件 | 容器写 | ✅ 正常写入 |

容器写永远放行的理由：配置文件来自外部（别人手写的、别的服务下发的），
库无权因为里面有个键恰好叫 `save` 就拒绝加载。

**读取侧：** 与接口同名的键，属性读取拿到的是方法本身，必须用 `cfg['key']` 或 `cfg.opt.key`。

```python
cfg = Config({'save': True, 'items': [1, 2], 'db': {'get': 'x'}})

cfg.save          # <bound method Config.save>  ← 被遮蔽
cfg['save']       # True
cfg.opt.save      # True
cfg.opt.db.get    # 'x' —— 每一层节点都有 opt，不只是顶层
```

**冲突是可查的，不是靠记忆：**

```python
cfg.shadowed        # ('save', 'items')  本层被遮蔽的配置键
cfg.reserved        # 本层全部接口名（自动从类派生，不会漏项）
cfg.find_shadowed() # {'.': ('save', 'items'), 'db': ('get',)}  整棵树的遮蔽情况
```

加载或批量写入后，若存在被遮蔽的键，库会打一条 `logging.warning` 指路，而不是让你自己猜。

**注意：** `data`、`dict` 在 0.1.x 是节点上的属性名，0.2.0 已不再是接口名，
所以 `cfg.data` 现在正常返回配置键 `data`；导出请用 `to_dict()`。

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

# 方法4：transaction()——一次磁盘写入，推荐用于批量改
with cfg.transaction():
    for i in range(1000):
        cfg.set(f'item.{i}', f'value_{i}')
# 进入时暂停落盘，退出时统一保存一次
# 块内抛异常：默认回滚到进入前的数据，并且不写盘（rollback_on_error=False 可关掉回滚）
```

`update()` / `merge()` / `set_data()` / `from_env()` 内部已经走这套机制，一次调用只写盘一次。

### 3. 加密配置

- 密码丢失将无法恢复数据
- 修改密码需要先用旧密码读取，再用新密码保存
- 加密文件被篡改会触发校验错误
- 保存前会先用当前密码试解既有文件：解不开就拒绝覆盖，避免用错密码把好文件写坏
- 既有明文文件可以直接加密码（首次 `save()` 即转成加密格式）
- 同一实例沿用同一 salt 并缓存派生出的密钥，所以自动保存不会每次赋值都跑一遍 PBKDF2

### 4. 文件格式推断

```python
# 自动推断
Config('app.toml')      # TOML 格式
Config('app.json')      # JSON 格式
Config('app')           # 默认 TOML

# 显式指定（优先级更高）
Config('data.txt', way='toml')  # 使用 TOML 格式读写 .txt 文件
```

**第一个位置参数是字符串时按文件名处理**，等价于 `Config(file='app.toml')`；
初始数据必须是 dict，写成 `Config(data={...}, file='app.toml')`。传别的类型会立刻报错，
不会等到写盘时才出问题。

### 5. 异常层次

```
ConfigError                 # 基类
├── ConfigIOError           # 读写文件失败
├── ConfigValidationError   # 类型/路径/键名冲突等用法错误
│   └── ConfigKeyError      # 键不存在（同时是 KeyError，except KeyError 能接住）
└── ConfigEncryptionError   # 密码错误或密文被篡改
```

`ConfigKeyError` 继承 `KeyError`，所以 `cfg['missing']`、`cfg.pop()`、`'x' in cfg`
的语义和普通 dict 一致；`cfg.get(...)`、`cfg.first(...)` 则不抛异常。

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
| `update(dict)` | 批量更新；容器语义，键名与接口同名也不会失败，整批只写盘一次 |
| `set_data(dict)` | 完全替换；同上 |
| `merge(other, strategy)` | 合并配置（`override` / `keep` / `deep`）；同上 |
| `transaction()` | 上下文管理器，块内暂停落盘、退出时写一次；异常默认回滚，不写盘 |

### 删除操作

| 方法 | 说明 |
|------|------|
| `del_key(key)` | 删除指定键（支持点路径），返回是否真的删了 |
| `del_clean()` | 清空并删除配置文件 |
| `pop(key, default)` / `clear()` | 继承自 dict 协议，同样会触发落盘 |

### 文件操作

| 方法 | 说明 |
|------|------|
| `save()` | 保存到文件 |
| `reload()` | 从文件重新加载 |
| `load(file, way)` | 切换目标文件/格式（不读内容，要立即生效请用 `reload()`） |
| `to_file(file, way)` | 另存为其他文件/格式 |

### 导入导出

| 方法 | 说明 |
|------|------|
| `to_dict()` | 导出为字典（每个节点都有） |
| `to_json(indent)` | 导出为 JSON 字符串 |
| `to_env(prefix, uppercase, separator)` | 导出为环境变量格式（嵌套默认用 `__`） |
| `from_env(prefix, separator)` | 从环境变量导入，与 `to_env` 互逆 |

### 比较操作

| 方法 | 说明 |
|------|------|
| `diff(other)` | 比较两个配置的差异 |

### 命名冲突与校验

| 成员 | 说明 |
|------|------|
| `opt` | 纯数据视图；**每一层节点都有**，可读写任何键 |
| `shadowed` | 本层被接口名遮蔽的配置键（元组） |
| `reserved` | 本层全部接口名（自动派生，元组） |
| `find_shadowed()` | 递归找出整棵树的遮蔽键，返回 `{点路径: (键, ...)}` |
| `validate()` | 按 schema 检查当前全部值，包括从文件加载进来的部分 |

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

`Config` 本身就是一个 dict（`MutableMapping`），`keys()` / `values()` / `items()` /
`pop()` / `popitem()` / `clear()` / `len()` / `in` / `==` 都可用；嵌套节点是 `ConfigNode`，
方法集是顶层的子集。

---

## 详细函数用法及预期效果

### 1. 初始化 `__init__`

```python
Config(
    文件名或初始数据,      # 'app.toml' 或 {'a': 1}，两种写法都支持
    file=None,            # 文件名（可无扩展名，默认 config）
    way="",               # 格式（json/toml/yaml/ini/xml），留空则按扩展名推断
    replace=False,        # 是否覆盖已有文件
    auto_save=True,       # 是否自动保存
    pwd=None,             # 加密密码
    process_safe=False,   # 是否进程安全（需要 confull[process]）
    debounce_ms=0,        # 去抖延迟（毫秒）
    env=None,             # 环境名称（如 'dev', 'production'）
    env_prefix="",        # 环境变量前缀（如 'APP'）
    schema=None,          # 类型验证 schema，键支持点路径
    data=None,            # 初始数据（关键字参数）
)
```

以下三种写法完全等价：

```python
Config({'a': 1}, file='app.toml')
Config('app.toml', data={'a': 1})
Config({'a': 1}, 'app.toml')      # 第二个位置参数仍是文件名，与 0.1.x 一致
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
cfg = Config('app.toml', env_prefix='MYAPP')
# 自动导入 MYAPP_* 环境变量（MYAPP_DB__HOST 还原成嵌套 db.host）

# 类型验证
schema = {'port': int, 'debug': bool, 'name': str}
cfg = Config('app.toml', schema=schema)
cfg.port = 8080      # ✅ 正常
cfg.port = "8080"    # ❌ 报错：期望 int，得到 str
```

**预期效果：**
- 自动创建目录和文件
- 自动推断格式（根据扩展名）
- 程序退出时确保最后一次写盘
- 支持多环境配置切换
- 加密实例复用 salt，赋值即保存也不会被 PBKDF2 拖慢
- 加载磁盘内容时**不**套用 schema（文件不该让构造函数直接失败）；要检查请显式调用 `validate()`

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
- 叶子/节点结构冲突时需要 `overwrite_mode=True`
- `set()` 走**属性语义**：最终键与接口同名会被拒绝并指路。要走容器语义就直接下标写，
  它同样支持点路径：`cfg['db.host'] = 'localhost'`、`cfg['save'] = True`

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
- 走**容器语义**：键名与接口同名也照样写入
- 整批只写盘一次

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
- 返回布尔值：键不存在时返回 `False`，不抛异常

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
- 返回原生 dict，每一层字典都是新建的，改它不会影响配置
- 列表这类可变叶子值是同一引用；需要彻底隔离请 `copy.deepcopy(cfg.to_dict())`
- 每个节点都有这个方法，`cfg.db.to_dict()` 只导出该子树
- `dict(cfg)` 只转最外层，嵌套部分仍是 `ConfigNode`；要**全原生**用 `to_dict()`

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
to_env(prefix: str = "", uppercase: bool = True, separator: str = "__") -> Dict[str, str]
```

**示例：**
```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}, 'name': 'app'})

cfg.to_env()
# {'DB__HOST': 'localhost', 'DB__PORT': '3306', 'NAME': 'app'}

cfg.to_env(prefix='APP')
# {'APP_DB__HOST': 'localhost', 'APP_DB__PORT': '3306', 'APP_NAME': 'app'}

cfg.to_env(uppercase=False)
# {'db__host': 'localhost', 'db__port': '3306', 'name': 'app'}

cfg.to_env(separator='_')   # 想要传统单下划线风格，显式传
# {'DB_HOST': 'localhost', 'DB_PORT': '3306', 'NAME': 'app'}
```

**预期效果：**
- 前缀用**单个**下划线衔接（`APP_NAME`，符合环境变量惯例）
- 嵌套层级用 `separator`（默认双下划线）衔接
- 只输出叶子值；前缀末尾多写的 `_` 会被忽略
- 可控制大小写

为什么默认是 `__`：单下划线在环境变量里太常见，`APP_DB_HOST` 既可能是「前缀 + 扁平键
`DB_HOST`」，也可能是「`db.host` 嵌套」，`from_env` 无法区分。用 `__` 表嵌套后，
`to_env` 和 `from_env` 才真正互逆。

---

### 19. 从环境变量导入 `from_env`

```python
from_env(prefix: str = "", separator: str = "__") -> Config
```

**示例：**
```python
import os
os.environ['MYAPP_DB__HOST'] = 'localhost'
os.environ['MYAPP_DB__PORT'] = '3306'
os.environ['MYAPP_NAME'] = 'app'

cfg = Config()
cfg.from_env(prefix='MYAPP')

cfg.db.host   # 'localhost'   ← __ 还原成嵌套
cfg.db.port   # '3306'
cfg['name']   # 'app'         ← 单下划线保持扁平
```

**预期效果：**
- 只导入指定前缀的变量（去前缀、转小写）
- `separator`（默认 `__`）还原为点路径嵌套，与 `to_env` 互逆
- 走容器语义：`MYAPP_ITEMS`、`MYAPP_SAVE` 这类键名照样能导入
- 整批只写盘一次，返回 self 支持链式
- 值一律是字符串（环境变量没有类型）
- 前缀匹配是 `startswith`，越具体越好：Windows 上用 `prefix='APP'` 会连系统变量
  `APPDATA` 一起吸进来（变成配置里的 `data`），建议用 `MYAPP` 这类不会撞车的名字

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

### 21. 纯数据视图 `opt`

```python
@property
opt -> _DataProxy      # 每个 ConfigNode 都有
```

`opt` 返回的对象不占用任何公开属性名（`__slots__` 只有一个下划线属性），
所以 `opt.` 后面写什么都是配置键，永远不会撞到接口名。

**示例：**
```python
cfg = Config({'save': True, 'items': [1, 2], 'db': {'get': 'x'}})

cfg.opt.save        # True
cfg.opt.items       # [1, 2]     ← 不是 dict 的 items() 方法
cfg.opt.db.get      # 'x'        ← 嵌套层也能一路 opt 下去
cfg.opt.save = False            # ✅ 属性写
cfg.opt['path'] = '/tmp'        # ✅ 下标写也行
del cfg.opt.save                # ✅ 删除

cfg.opt             # 顶层全部数据的 repr
len(cfg.opt)        # 支持 len / in / 迭代 / 调用
'save' in cfg.opt   # True
cfg.opt('save')     # False，等价于 get('save')
cfg.opt.db == {'get': 'x'}   # ✅ 可以直接和 dict 比
```

**预期效果：**
- 读任何键、写任何键都不必再关心命名冲突
- 与接口同名的键被遮蔽时，`shadowed` / `find_shadowed()` 会告诉你，日志里也有 warning
- 想要「只看数据、不看见方法」的场合（打印、模板、调试）用 `opt` 最省心

---

### 22. 属性访问（魔法方法）

```python
# 支持的魔法方法
cfg.key           # __getattr__，接口同名的键拿不到（见 §21）
cfg.key = value   # __setattr__，接口同名时报错指路而不是替换方法
del cfg.key       # __delattr__
cfg['key']        # __getitem__，支持点路径
cfg['key'] = val  # __setitem__，支持点路径
del cfg['key']    # __delitem__，支持点路径
len(cfg)          # __len__
iter(cfg)         # __iter__
'key' in cfg      # __contains__，支持点路径
bool(cfg)         # __bool__
cfg == {...}      # __eq__，直接和普通 dict 比
cfg('key')        # __call__，等价于 cfg.get('key')
cfg('key', 'd')   # 带默认值
cfg | {...}       # __or__，合并成新 dict
cfg |= {...}      # __ior__，原地合并
with cfg: ...     # __enter__/__exit__，退出时保存
```

**示例：**
```python
cfg = Config({'a': 1, 'b': {'c': 2}})

# 属性访问
cfg.a           # 1
cfg.b.c         # 2
cfg.b           # ConfigNode({'c': 2})

# 字典访问
cfg['a']        # 1
cfg['b.c']      # 2（支持点路径）
cfg['b.c'] = 3  # 点路径写入同样支持

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
cfg('b.c')      # 3
cfg('nope', 42) # 42（默认值）

# 与 dict 互操作
dict(cfg)                  # {'a': 1, 'b': ConfigNode(...)} → 需要完整原生 dict 用 to_dict()
cfg == {'a': 1, 'b': {'c': 3}}   # True
```

**注意：** 缺失键统一抛 `ConfigKeyError`（它同时是 `KeyError`），
消息里会提示改用 `get(key, default)` 或 `set(key, value)`；属性读取缺失键抛 `AttributeError`。

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
# 首选 transaction()：自动保存照常开着，块内只写一次盘
with cfg.transaction():
    for i in range(1000):
        cfg.set(f'item.{i}', f'value_{i}')
# 中途抛异常会回滚到进入前的数据，并且不写盘；不想回滚传 rollback_on_error=False

# 或者关闭自动保存，批量操作后手动保存
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
cfg = Config('app.toml', env='production', env_prefix='MYAPP')
# 1. 加载 app.toml
# 2. 加载 app.production.toml
# 3. 导入 MYAPP_* 环境变量
```

```bash
# MYAPP_NAME=api          → 顶层扁平键 name
# MYAPP_DATABASE__HOST=x  → 嵌套 database.host（双下划线表示层级）
```

**配置优先级（从低到高）：**
1. 基础配置文件（app.toml）
2. 环境配置文件（app.{env}.toml）
3. 环境变量（{env_prefix}*）

`env_prefix` 末尾的下划线可写可不写（`'MYAPP'` 与 `'MYAPP_'` 等价）。

### 技巧 5：类型验证

```python
# 定义 schema（键支持点路径）
schema = {
    'port': int,
    'debug': bool,
    'name': str,
    'database.port': int,
    'database.host': str
}

# 创建配置（带类型验证）
cfg = Config(schema=schema, file='app.toml')

# 正常设置
cfg.port = 8080           # ✅
cfg.set('port', 3306)     # ✅
cfg['port'] = 5432        # ✅
cfg['db.host'] = 'h'      # ✅ 点路径写入也校验

# 类型错误会抛出 ConfigValidationError
cfg.port = "8080"         # ❌ 期望 int，得到 str
cfg.debug = "true"        # ❌ 期望 bool，得到 str
cfg.name = 123            # ❌ 期望 str，得到 int
cfg.port = True           # ❌ bool 不是 int（Python 的老坑，这里挡掉了）

# 整棵子树一起赋值也照样校验
cfg.database = {'host': 'h', 'port': 'oops'}   # ❌ 报错：'database.port' 期望 int
```

**校验覆盖的范围：**
- `cfg.key = value`（属性方式）
- `cfg.set('key', value)` / `cfg['key'] = value` / `cfg['a.b'] = value`
- `update()`、`merge()`、`set_data()`、构造函数传入的 `data`
- 嵌套多深都按完整点路径匹配 schema

**不校验的情况：** 从文件、环境配置文件读进来的内容。磁盘上的东西不该让构造函数直接崩掉，
库照常加载，你自己决定要不要检查：

```python
cfg = Config('app.toml', schema=schema)
cfg.validate()   # 按 schema 过一遍当前全部值，不合格抛 ConfigValidationError
```

推荐在服务启动时调用一次 `validate()`，把外部篡改或手改写错尽早暴露出来。

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
cfg.from_env(prefix='MYAPP')

# 反向：把当前配置导出成环境变量，喂给子进程或 Docker
os.environ.update(cfg.to_env(prefix='MYAPP'))
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

# 导出为 Docker 环境变量格式（嵌套用 __，前缀用单个 _）
env_vars = cfg.to_env(prefix='MYAPP')
for key, value in env_vars.items():
    print(f"{key}={value}")
# MYAPP_NAME=api
# MYAPP_DATABASE__HOST=prod-db.example.com
```

### 技巧 15：给既有明文配置加密码 / 换密码

```python
from confull import Config

# 读出内容（旧密码或不加密码）
data = Config('app.toml', pwd='old-password').to_dict()

# 用新密码整份写回
Config('app.toml', data=data, pwd='new-password', replace=True)
```

给明文文件加密码是同一个套路，只是第一步不传 `pwd`。

密码错误时 `save()` 会先试解既有密文，解不开就直接抛 `ConfigEncryptionError`，
不会把原文件覆盖成坏数据。

### 技巧 16：命名冲突自检

```python
cfg = Config('app.toml')

cfg.find_shadowed()   # {'.': ('save',), 'db': ('items',)} —— 哪些键属性访问拿不到
cfg.shadowed          # 只看本层
cfg.reserved          # 本层全部接口名（可用作「哪些键名要避开」的清单）
```

打开或批量导入后如果存在遮蔽键，`logging.warning` 也会点名。CI 里可以硬失败：

```python
shadowed = cfg.find_shadowed()
assert not shadowed, f"这些配置键与接口同名，属性访问会踩坑：{shadowed}"
```

### 技巧 17：与只认 dict 的库打交道

```python
cfg = Config('app.toml')

fastapi_style = cfg.to_dict()          # 完全原生的嵌套 dict
yaml.safe_dump(cfg.to_dict(), f)       # 交给别的序列化库
other = cfg | {'extra': 1}             # 合并成新 dict，不动原配置
```

---

## 0.2.0 变更说明

### 核心：键名冲突的处理方式

一个对象只有一套属性命名空间，「配置键 `save`」和「方法 `save()`」不可能同时用属性访问。
0.2.0 不再假装这个问题不存在，而是定了条规矩：

> **属性写法让路（撞名就报错并指路），容器写法放行（`[]` / `opt` / 批量导入永远可写）。**

于是任何键名都保证可达，遮蔽情况可以用 `shadowed` / `find_shadowed()` 查出来，
接口名单也从手工维护改成**运行时从类里自动派生**，不会再漏项。

### 行为变化清单（0.1.x → 0.2.0）

| # | 变化 | 旧行为 | 新行为 |
|---|------|--------|--------|
| 1 | 属性写撞接口名 | `cfg.save = True` 悄悄把 `save()` 方法替换掉，之后调用直接炸 | 抛 `ConfigValidationError`，消息里给出可用写法 |
| 2 | 保留名单 | 手工维护 8 个名字，且只管嵌套节点 | 自动派生：顶层 39 个、嵌套 14 个，两层规则一致 |
| 3 | `Config` 是不是 dict | 不是（只有 `len/iter/getitem`） | 是 `MutableMapping`：`keys/values/items/pop/popitem/clear`、`dict(cfg)`（只转最外层）、`cfg == {...}` 都能用；代价是这些名字会遮蔽同名配置键 |
| 4 | 缺失键抛什么 | 裸 `ConfigValidationError`，`except KeyError` 接不住 | `ConfigKeyError`（同时是 `KeyError`），消息带 `get(key, default)` 指路 |
| 5 | 节点导出 | `node.data`（内部活引用）、`node.dict` | `to_dict()`，每一层新建 dict，改它不会污染配置 |
| 6 | `opt` 能到哪 | 只有顶层 `cfg.opt` | 每个节点都有：`cfg.db.opt.get`、`cfg.opt.db.items` |
| 7 | 点路径 | 读支持，写 `cfg['a.b'] = v` 会创建一个真名叫 "a.b" 的键 | 读写删对称，`cfg['a.b'] = v` 写到 `a` 节点里的 `b` |
| 8 | 构造函数首参 | `Config('app.toml')` 把文件名当 `data`，只在文件已存在时才"碰巧"能跑 | 字符串按文件名处理；`Config('a.toml', data={...})` 同样支持；非 dict 初始数据立即报错，不碰磁盘 |
| 9 | 环境变量命名 | `to_env` 用 `_` 连接嵌套，`from_env` 读回来却无法区分前缀和层级，两者不互逆 | 前缀用 `_`、嵌套用 `__`（`MY_DB__HOST`），`to_env`/`from_env` 互逆；要旧风格传 `separator='_'` |
| 10 | 批量写入落盘次数 | 每个键写一次盘（改 1000 个键 = 写 1000 次） | `update`/`set_data`/`merge`/`from_env` 一次调用只写一次；`transaction()` 覆盖任意批量场景，异常时默认回滚且不写盘 |
| 11 | schema 校验范围 | 只校验顶层 `set()` 到的键；整棵子树赋值绕过；`bool` 被当成 `int` | 覆盖任意深度、任意写入路径（含子树赋值），区分 `bool`/`int`；**从文件加载的内容不校验**，需要时显式 `validate()` |
| 12 | 加密性能 | 每次保存都生成新 salt 并重新跑 100k 轮 PBKDF2，`cfg.x = 1` 一次落盘约 23.5ms | 同一实例复用 salt + 缓存派生密钥，约 0.9ms；**文件格式不变**（仍是 8 字节 salt 头 + Fernet），旧文件照读 |
| 13 | 加密防呆 | 用错密码也会把内存里的数据写回去，覆盖掉唯一一份密文 | `save()` 前先用当前密码试解既有密文，解不开直接拒绝覆盖 |
| 14 | 依赖 | `PyYAML`/`watchdog`/`portalocker`/`cryptography` 全部硬依赖，`import confull` 就拖进来 | 改为 extras 且按需导入，用到才提示 `pip install 'confull[encrypt]'` 这类命令 |
| 15 | 文件监听 | 自己写盘也会触发 reload，读到一半可能被自己的事件打断 | 比对 mtime，只有确实是外部改动才 reload |
| 16 | 退出保存 | 每个实例注册一个 `atexit` 钩子，实例被回收也留在表里 | 单个 `atexit` 钩子 + 弱引用表，超过 32 条自动清理死引用 |
| 17 | INI 加载 | 依赖 `configparser` 私有 `_sections`，且 `DEFAULT` 段的键被复制进每个 section | 走公开 API，`DEFAULT` 单独成节，不再重复 |
| 18 | 并发 | 子节点的写不持锁，多线程改同一棵树会打架 | 所有写入统一在顶层 `RLock` 下 |

### 迁移清单

绝大多数代码不用改。需要过一遍的是这几处：

```text
1. 全局搜「属性写法赋值给接口名」：cfg.save = / cfg.items = / cfg.get = / cfg.update =
   → 改成 cfg['save'] = 或 cfg.opt.save =

2. node.data / node.dict → node.to_dict()

3. 依赖 to_env 变量名的地方（Docker compose、CI、子进程）
   → APP_DB_HOST 变成 APP_DB__HOST；不想改就显式传 separator='_'

4. 原来指望「类型不对构造函数就炸」的启动校验
   → 文件内容现在不校验，请在构造后调用 cfg.validate()

5. 原来 except ConfigValidationError 捕「键不存在」
   → 可以改用 KeyError（ConfigKeyError 同时是两者）
```

改完可以先跑一次自检，确认没有键名被接口遮蔽：

```python
cfg = Config('app.toml')
print(cfg.find_shadowed())   # {} 就没事
```

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
