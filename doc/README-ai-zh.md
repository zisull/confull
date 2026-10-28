# ConfuLL - AI 集成规范文档

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [AI](https://github.com/zisull/confull/blob/main/doc/README-ai-zh.md)

> 本文档为 AI 提供精确、规范的 API 参考，确保正确使用 confull 库。

---

## 1. 快速参考

### 1.1 安装与导入

```bash
pip install confull                # 必装能力：json/toml/ini/xml + 明文读写
pip install 'confull[yaml]'        # YAML 格式
pip install 'confull[encrypt]'     # pwd 加密
pip install 'confull[watch]'       # enable_watch 文件监听
pip install 'confull[process]'     # process_safe 进程锁
pip install 'confull[all]'         # 以上全部
```

```python
from confull import Config, ConfigNode
from confull import (
    ConfigError,
    ConfigIOError,
    ConfigKeyError,
    ConfigValidationError,
    ConfigEncryptionError,
)
```

可选依赖按需导入：`import confull` 不会拉进 PyYAML / cryptography / watchdog / portalocker，
只有真正用到时才导入并给出可执行的安装提示。

### 1.2 最小可用示例

```python
from confull import Config

# 创建/加载配置（自动推断格式）
cfg = Config('app.toml')

# 读写配置
cfg.name = 'MyApp'
cfg.set('db.host', 'localhost')

# 获取配置
name = cfg.name                    # 属性方式
host = cfg.get('db.host')         # get 方式
port = cfg('db.port', 3306)       # 调用方式（带默认值）
```

---

## 2. 构造函数

### 2.1 签名

```python
Config(
    文件名或初始数据,            # 'app.toml' 或 {'a': 1}（位置参数，二选一）
    file: str = None,            # 文件路径（可无扩展名，默认 config）
    way: str = "",               # 格式：json/toml/yaml/ini/xml（空则自动推断）
    replace: bool = False,       # 是否覆盖已有文件
    auto_save: bool = True,      # 是否自动保存
    pwd: str = None,             # 加密密码（None表示不加密）
    process_safe: bool = False,  # 是否启用进程锁
    debounce_ms: int = 0,        # 自动保存去抖延迟（毫秒）
    env: str = None,             # 环境名称（如 'dev', 'production'）
    env_prefix: str = "",        # 环境变量前缀（如 'APP'）
    schema: dict = None,         # 类型验证 schema（如 {'port': int}）
    *,
    data: dict = None,           # 初始数据（关键字参数）
)
```

第一个参数是**位置专属**（positional-only），既能传文件名也能传初始 dict，
所以 `Config('app.toml', data={...})` 和 `Config({...}, file='app.toml')` 都成立，
第二个位置参数仍是 `file`，与 0.1.x 兼容。

### 2.2 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| 首位置参数 | str/dict/None | None | 文件名或初始数据；非 dict 且非路径时立即抛 `ConfigValidationError` |
| `file` | str | None（→ config） | 配置文件路径，自动创建目录和扩展名 |
| `way` | str | "" | 格式，空字符串时从扩展名推断，无法推断默认toml |
| `replace` | bool | False | True时忽略已有文件，使用data初始化 |
| `auto_save` | bool | True | True时任何修改自动保存到文件 |
| `pwd` | str/None | None | 非空时启用Fernet加密（需要 `confull[encrypt]`） |
| `process_safe` | bool | False | True时使用portalocker进程锁（需要 `confull[process]`） |
| `debounce_ms` | int | 0 | >0时延迟保存，减少频繁IO |
| `env` | str/None | None | 环境名称，自动合并 app.{env}.toml |
| `env_prefix` | str | "" | 环境变量前缀，自动导入 {prefix}* 环境变量 |
| `schema` | dict/None | None | 类型验证，格式如 {'port': int, 'db.host': str}；**不校验文件内容** |
| `data` | dict/None | None | 初始配置数据（只能作为关键字参数） |

### 2.3 格式推断规则

```
1. way 显式指定 → 使用指定格式
2. way 为空 + 扩展名可识别 → 使用扩展名对应格式
3. way 为空 + 扩展名无法识别 → 默认 toml
4. way 为空 + 无扩展名 → 默认 toml，添加 .toml 扩展名
```

### 2.4 格式特性

| 格式 | 嵌套支持 | 类型保留 | 说明 |
|------|----------|----------|------|
| JSON | ✅ 完整 | ✅ 完整 | 推荐格式 |
| TOML | ✅ 完整 | ✅ 完整 | 推荐格式 |
| YAML | ✅ 完整 | ✅ 完整 | 推荐格式 |
| INI | ✅ 点路径 | ❌ 全字符串 | 嵌套结构自动展平为点路径 |
| XML | ✅ 完整 | ❌ 全字符串 | 值读回后为字符串 |

**INI 格式特殊行为：**
```python
# 保存嵌套数据
cfg = Config({'database': {'host': 'localhost', 'port': 3306}}, file='app.ini', way='ini')

# INI 文件内容（点路径格式）：
# [database]
# host = localhost
# port = 3306

# 其他程序读取时需注意：
# - 键名是 'database.host'，不是单独的 'host'
# - 所有值都是字符串，需要手动转换类型
```

### 2.5 常见构造方式

```python
# 空配置（默认文件 config.toml）
cfg = Config()

# 指定文件（自动推断格式）
cfg = Config('app.toml')
cfg = Config('app.json')
cfg = Config('app.yaml')

# 使用 txt 扩展名但 toml 格式
cfg = Config('config.txt', way='toml')

# 带初始数据（三种等价写法）
cfg = Config({'name': 'app', 'version': '1.0'}, file='app.toml')
cfg = Config('app.toml', data={'name': 'app', 'version': '1.0'})
cfg = Config({'name': 'app'}, 'app.toml')

# 加密配置
cfg = Config('secure.toml', pwd='my-secret-key')

# 去抖保存（100ms内只保存一次）
cfg = Config('app.toml', debounce_ms=100)

# 多环境切换
cfg = Config('app.toml', env='production')
# 自动加载 app.production.toml

# 环境变量覆盖（前缀末尾下划线可写可不写）
cfg = Config('app.toml', env_prefix='MYAPP')
# 自动导入 MYAPP_* 环境变量；MYAPP_DB__HOST 还原成嵌套 db.host

# 类型验证
schema = {'port': int, 'debug': bool, 'name': str}
cfg = Config('app.toml', schema=schema)
cfg.port = 8080      # ✅ 正常
cfg.port = "8080"    # ❌ ConfigValidationError
```

---

## 3. 数据访问 API

### 3.0 两种写入语义（命名冲突的唯一规则）

配置键可能与库的接口名同名（`save`、`items`、`get`……）。规则只有一条：

> **属性写法让路，容器写法放行。**

| 写法 | 语义 | 键名与接口同名时 |
|------|------|------------------|
| `cfg.k = v`、`cfg.set('k', v)` | 属性写 | 抛 `ConfigValidationError`，消息给出可用写法（绝不替换方法） |
| `cfg['k'] = v`、`cfg.opt.k = v` | 容器写 | 正常写入 |
| `update()` / `merge()` / `set_data()` / `from_env()` / 加载文件 | 容器写 | 正常写入 |

读取侧：与接口同名的键，属性读拿到的是方法本身，必须用 `cfg['k']` 或 `cfg.opt.k`。
接口名单运行时从类里派生（顶层 39 个、嵌套节点 14 个），用 `cfg.reserved` 查看，
用 `cfg.shadowed` / `cfg.find_shadowed()` 查当前哪些键被遮蔽。详见 §10。

`data`、`dict` 不再是接口名，所以 `cfg.data` 现在能正常读到配置键 `data`。

### 3.1 三种访问方式

```python
cfg = Config({'db': {'host': 'localhost', 'port': 3306}})

# 方式1：属性访问
cfg.db.host              # 'localhost'
cfg.db.port              # 3306

# 方式2：字典访问（支持点路径，读写删对称）
cfg['db']['host']        # 'localhost'
cfg['db.host']           # 'localhost'（点路径）
cfg['db.host'] = '127.0.0.1'
del cfg['db.host']

# 方式3：get/set 方法（推荐用于动态键名）
cfg.get('db.host')       # 'localhost'
cfg.set('db.host', '127.0.0.1')
```

`cfg.db` 返回的是 `ConfigNode`（也是个 dict），与顶层 `Config` 的访问规则完全一致——
包括 `.opt`、点路径和 `to_dict()`。

### 3.2 获取值

```python
# get 方法
get(key: str, default: Any = None) -> Any

# 示例
cfg.get('db.host')              # 'localhost'
cfg.get('db.user', 'root')      # 'root'（不存在时返回默认值）
cfg.get('missing')              # None（不存在时返回None）

# 调用方式（等价于get）
cfg('db.host')                  # 'localhost'
cfg('db.user', 'root')          # 'root'
```

### 3.3 设置值

```python
# set 方法
set(key: str, value: Any, overwrite_mode: bool = False) -> Config

# 示例
cfg.set('db.host', 'localhost')           # 设置值
cfg.set('db.host', '127.0.0.1')           # 覆盖值
cfg.set('new.key', 'value')               # 自动创建中间节点

# 链式操作（set返回self）
cfg.set('db.host', 'localhost').set('db.port', 3306).set('db.user', 'root')
```

### 3.4 overwrite_mode 说明

当路径已存在但结构冲突（叶子 ↔ 节点）时，需要 `overwrite_mode=True`，否则抛 `ConfigValidationError`：

```python
cfg = Config()

# 叶子 -> 字典（冲突）
cfg.set('x', 1)
cfg.set('x.y', 2)                           # ❌ ConfigValidationError
cfg.set('x.y', 2, overwrite_mode=True)      # ✅ 把 x 改成节点后写入

# 字典 -> 叶子（冲突）
cfg.set('a', {'b': 1})
cfg.set('a', 99)                            # ❌ ConfigValidationError
cfg.set('a', 99, overwrite_mode=True)       # ✅ 覆盖

# 容器写法没有这个限制：想直接换掉就下标赋值
cfg['a'] = 99
```

`set()` 走属性语义：如果最终键与接口同名（如 `cfg.set('save', 1)`），会抛
`ConfigValidationError` 并指路；这类键请用 `cfg['save'] = 1` 或 `cfg.opt.save = 1`。

---

## 4. 便捷方法

### 4.1 setdefault - 设置默认值

```python
setdefault(key: str, value: Any) -> Any

# 仅在键不存在时设置，返回最终值
cfg = Config({'version': '1.0'})

cfg.setdefault('version', '2.0')    # 返回 '1.0'（已存在，不覆盖）
cfg.setdefault('name', 'MyApp')     # 返回 'MyApp'（不存在，设置）
```

### 4.2 first - 获取第一个存在的键

```python
first(*keys, default=None) -> Any

# 按优先级查找，返回第一个存在且非None的值
cfg = Config({'host': 'localhost', 'server_host': '127.0.0.1'})

cfg.first('server_host', 'host')              # '127.0.0.1'
cfg.first('missing', 'host')                  # 'localhost'
cfg.first('a', 'b', 'c', default='none')      # 'none'（都不存在）
```

### 4.3 require - 获取必需配置

```python
require(key: str) -> Any

# 不存在或值为 None 时抛出 ConfigValidationError
cfg = Config({'db_url': 'sqlite:///db.sqlite'})

cfg.require('db_url')       # 'sqlite:///db.sqlite'
cfg.require('api_key')      # ❌ ConfigValidationError: "必需的配置项 'api_key' 不存在或值为 None"
```

---

## 5. 批量操作

三个批量入口（`update` / `set_data` / `merge`）都走**容器语义**：键名与接口同名也照样写入，
内部用 `_deferred()` 包住，整批只落盘一次，并且结束后自动 `logging.warning` 报告被遮蔽的键。

### 5.1 update - 批量更新

```python
update(data: Dict[str, Any]) -> None

# 支持点路径键名；键名撞接口也不报错
cfg.update({
    'db.host': 'localhost',
    'db.port': 3306,
    'debug': True,
    'save': True          # ✅ 容器语义，正常写入
})
```

### 5.2 set_data - 完全替换

```python
set_data(data: Dict[str, Any]) -> None

# 替换所有配置数据
cfg.set_data({'new_key': 'new_value'})
# 旧数据完全丢失
```

### 5.3 merge - 合并配置

```python
merge(other: Union[Dict, Config], strategy: str = "override") -> Config

# 策略说明：
# - 'override': 覆盖已有值（默认）
# - 'keep': 保留已有值（只按顶层键判断是否存在）
# - 'deep': 深度合并嵌套字典
# 未知策略抛 ConfigValidationError

cfg = Config({'db': {'host': 'localhost', 'port': 3306}})

# override（覆盖）
cfg.merge({'db': {'host': '127.0.0.1'}, 'debug': True})
# 结果: {'db': {'host': '127.0.0.1'}, 'debug': True}

# keep（保留）
cfg.merge({'db': {'host': '127.0.0.1'}, 'debug': True}, strategy='keep')
# 结果: {'db': {'host': 'localhost', 'port': 3306}, 'debug': True}

# deep（深度合并）
cfg.merge({'db': {'user': 'root'}, 'debug': True}, strategy='deep')
# 结果: {'db': {'host': 'localhost', 'port': 3306, 'user': 'root'}, 'debug': True}
```

### 5.4 transaction - 自定义批量写入

```python
with cfg.transaction():          # 也支持 with cfg.transaction() as cfg:
    for i in range(1000):
        cfg[f'item.{i}'] = f'value_{i}'
# 块内暂停落盘，正常退出时统一写一次；1000 次赋值 = 1 次磁盘写入
```

```python
try:
    with cfg.transaction():
        cfg['half'] = 1
        raise RuntimeError
except RuntimeError:
    ...
# 异常时：内存回滚到进入前的快照，并且不写盘（文件保持原样）
# 不想回滚：with cfg.transaction(rollback_on_error=False) → 异常也把已有改动落盘一次
```

`auto_save=False` 也能减少写盘次数，但 `transaction()` 不改动实例设置、且异常时不会留下
半成品，适合临时批量操作。它保证的是「半途而废的修改不进文件」，不是跨进程事务
（写盘本身已经是临时文件 + 原子替换）。

---

## 6. 删除操作

### 6.1 del_key - 删除指定键

```python
del_key(key: str) -> bool

# 支持点路径，自动清理空的父节点；键不存在时返回 False（不抛异常）
cfg = Config({'a': {'b': {'c': 1, 'd': 2}}, 'e': 3})

cfg.del_key('a.b.c')     # True
# 结果: {'a': {'b': {'d': 2}}, 'e': 3}

cfg.del_key('a.b.d')     # True，'a' 和 'b' 空了就一并删掉
# 结果: {'e': 3}

cfg.del_key('nope')      # False
```

### 6.2 del_clean - 清空配置

```python
del_clean() -> bool

# 清空内存数据并删除配置文件
cfg = Config({'x': 1}, file='app.toml')
cfg.del_clean()
# 返回 True，文件被删除；文件本来就不存在时返回 False
```

### 6.3 dict 协议的删除操作

```python
cfg.pop('db.host', None)   # 支持点路径；缺失键给 default，否则抛 ConfigKeyError
del cfg['db.host']         # 缺失时抛 ConfigKeyError
cfg.clear()                # 清空并落盘
```

`pop` / `del` 只删那一个键，**不会**清理变空的父节点（`{'db': {}}` 会留着）；
要顺手清理空父节点就用 `del_key()`。

---

## 7. 文件操作

### 7.1 save - 保存

```python
save() -> None

# 立即保存（忽略去抖延迟）；没有改动（非 dirty）时直接返回，不重复写盘
cfg = Config('app.toml', auto_save=False)
cfg.name = 'app'
cfg.save()  # 手动保存
```

写入 = 临时文件 + `os.fsync` + `Path.replace` 原子替换。
带 `pwd` 时，落盘前会先用当前密码试解既有密文：**密码不对就抛 `ConfigEncryptionError`
并拒绝覆盖**，避免把唯一一份密文写成坏数据。既有明文文件则放行（这正是给明文加密码的路径）。

### 7.2 reload - 重新加载

```python
reload() -> None

# 从磁盘重新加载（丢弃未保存的更改）
cfg = Config('app.toml')
# 外部修改了 app.toml
cfg.reload()
```

### 7.3 to_file - 另存为

```python
to_file(file: str = None, way: str = None) -> None

# 保存到其他文件/格式
cfg = Config('app.toml')
cfg.to_file('backup.json', way='json')
cfg.to_file('backup.yaml', way='yaml')
```

### 7.4 文件监听

```python
enable_watch() -> None
disable_watch() -> None

# 开启监听（外部修改后自动 reload）；需要 confull[watch]
cfg = Config('config.toml')
cfg.enable_watch()

# 关闭监听（建议在程序退出前调用，析构里也会兜底关闭）
cfg.disable_watch()
```

自己写盘同样会触发文件系统事件，所以 reload 前会比对 mtime：
只有磁盘时间戳和上次落盘不一致才认定是外部改动，不会被自己的保存打断。

### 7.5 load - 切换目标文件/格式

```python
load(file=None, way=None) -> None

# 只改「以后读写哪里」，不读取内容；要立即生效请再调用 reload()
cfg.load('other.toml')
cfg.load(way='json')
```

---

## 8. 导入导出

### 8.1 to_dict - 导出为字典

```python
to_dict() -> Dict[str, Any]     # Config 和每个 ConfigNode 都有

cfg = Config({'db': {'host': 'localhost'}})
cfg.to_dict()               # {'db': {'host': 'localhost'}}
cfg.db.to_dict()            # {'host': 'localhost'}（只导出子树）
```

每一层字典都是新建的，改它不会影响配置；但列表这类**可变叶子值是同一个引用**，
需要彻底隔离用 `copy.deepcopy(cfg.to_dict())`。
旧版的 `node.data` / `node.dict`（返回内部活引用）已移除，一律改用 `to_dict()`。

### 8.2 to_json - 导出为JSON

```python
to_json(indent: int = 2) -> str

# 返回JSON字符串
cfg = Config({'name': 'app'})
cfg.to_json()          # '{\n  "name": "app"\n}'
cfg.to_json(indent=4)  # 更多缩进
```

### 8.3 to_env - 导出为环境变量

```python
to_env(prefix: str = "", uppercase: bool = True, separator: str = "__") -> Dict[str, str]

# 前缀用单个 _ 衔接，嵌套层级用 separator（默认 __）衔接
cfg = Config({'db': {'host': 'localhost', 'port': 3306}, 'name': 'app'})

cfg.to_env()                # {'DB__HOST': 'localhost', 'DB__PORT': '3306', 'NAME': 'app'}
cfg.to_env(prefix='APP')    # {'APP_DB__HOST': ..., 'APP_DB__PORT': ..., 'APP_NAME': 'app'}
cfg.to_env(uppercase=False) # {'db__host': ..., 'db__port': ..., 'name': ...}
cfg.to_env(separator='_')   # {'DB_HOST': ..., 'DB_PORT': ..., 'NAME': ...}
```

只输出叶子值；`prefix` 末尾多写的 `_` 会被忽略（`'APP'` 与 `'APP_'` 等价）。
用 `__` 表嵌套是为了让 `from_env` 能无歧义还原：单下划线在环境变量里太常见，
`APP_DB_HOST` 既可能是前缀+扁平键 `DB_HOST`，也可能是嵌套 `db.host`。

### 8.4 from_env - 从环境变量导入

```python
from_env(prefix: str = "", separator: str = "__") -> Config

import os
os.environ['MYAPP_DB__HOST'] = 'localhost'
os.environ['MYAPP_NAME'] = 'app'

cfg = Config()
cfg.from_env(prefix='MYAPP')
# cfg.db.host == 'localhost'   ← __ 还原成嵌套
# cfg['name'] == 'app'         ← 单下划线保持扁平
```

- 前缀匹配是 `startswith`，去前缀后转小写；`separator` 换成 `.` 得到点路径
- 走容器语义 + 一次落盘，返回 self 支持链式
- 值一律是字符串（环境变量没有类型）
- 前缀要够具体：Windows 上 `prefix='APP'` 会把系统变量 `APPDATA` 也吸进来，
  变成配置里的 `data`
- 与 `to_env(prefix=P)` 互逆的前提是两边用同一个 `separator`

---

## 8.5 多环境切换

```python
# 构造函数参数
Config(file='app.toml', env='production', env_prefix='MYAPP')

# 加载顺序（优先级从低到高）：
# 1. app.toml（基础配置）
# 2. app.production.toml（环境配置，存在才合并；加密规则与主文件一致）
# 3. MYAPP_* 环境变量（最高优先级）

# 示例
cfg = Config('app.toml', env='production', env_prefix='MYAPP')
# 1. 加载 app.toml
# 2. 合并 app.production.toml（如果存在）
# 3. 导入 MYAPP_* 环境变量（MYAPP_DB__HOST → db.host）
```

---

## 8.6 类型验证

```python
# 定义 schema（键是完整点路径）
schema = {
    'port': int,
    'debug': bool,
    'name': str,
    'database.port': int,
    'database.host': str
}

# 创建配置（带类型验证）
cfg = Config('app.toml', schema=schema)

# 正常设置
cfg.port = 8080           # ✅
cfg.set('port', 3306)     # ✅
cfg['port'] = 5432        # ✅
cfg['database.host'] = 'h'  # ✅ 点路径写入同样校验

# 类型错误抛 ConfigValidationError
cfg.port = "8080"         # ❌ 键 'port' 期望类型 int，实际得到 str
cfg.debug = "true"        # ❌
cfg.name = 123            # ❌
cfg.port = True           # ❌ bool 不算 int
cfg.database = {'host': 'h', 'port': 'oops'}   # ❌ 整棵子树赋值也逐叶校验
```

**校验覆盖：** 属性写、`set()`、下标写（含点路径）、`update`/`set_data`/`merge`/`from_env`、
构造函数传入的 `data`，任意深度都按完整点路径匹配 schema。

**不校验：** 从文件（含 `app.{env}.toml`）读进来的内容——磁盘上的东西不该让构造函数直接失败。
需要检查时显式调用：

```python
cfg = Config('app.toml', schema=schema)
cfg.validate()   # 逐叶检查当前全部值，不合格抛 ConfigValidationError
```

---

## 9. 比较操作

### 9.1 diff - 比较差异

```python
diff(other: Union[Dict, Config]) -> Dict[str, Any]

# 返回包含 added/removed/modified 的字典
cfg1 = Config({'a': 1, 'b': 2, 'c': 3})
cfg2 = Config({'a': 1, 'b': 99, 'd': 4})

diff = cfg1.diff(cfg2)
# {
#     'added': {'d': 4},
#     'removed': {'c': 3},
#     'modified': {'b': {'old': 2, 'new': 99}}
# }
```

---

## 10. 命名冲突与 opt

### 10.1 唯一规则

配置键可能与接口名同名。**属性写法让路，容器写法放行**：

| 写法 | 键名与接口同名时 |
|------|------------------|
| `cfg.k = v`、`cfg.set('k', v)` | 抛 `ConfigValidationError`，消息给出可用写法 |
| `cfg['k'] = v`、`cfg.opt.k = v` | 正常写入 |
| `update` / `merge` / `set_data` / `from_env` / 加载文件 | 正常写入 |

读取侧同理：同名键属性读拿到的是方法本身，必须用 `cfg['k']` 或 `cfg.opt.k`。
**AI 生成代码时的默认选择**：键名来自动态来源（用户输入、远端配置、CSV 表头）时，
一律用下标或 `opt`，不要用属性写。

### 10.2 接口名单（运行时从类派生，不用背）

```python
cfg.reserved     # 本层全部接口名（tuple）
node.reserved    # 嵌套节点是子集
```

| 层级 | 数量 | 名单 |
|------|------|------|
| 嵌套 `ConfigNode` | 14 | `clear, find_shadowed, get, items, keys, opt, pop, popitem, reserved, setdefault, shadowed, to_dict, update, values` |
| 顶层 `Config` | 39 | 上面 14 个 + `del_clean, del_key, diff, disable_watch, enable_watch, first, from_env, is_auto_save, load, mark_dirty, merge, notify_dirty, path, path_abs, reload, require, save, set, set_auto_save, set_data, to_env, to_file, to_json, transaction, validate` |

`Config` 是 `MutableMapping`，所以 `items/keys/values/pop/popitem/clear/update` 也在名单里。
`data`、`dict` 已不再是接口名，可以当普通配置键用属性访问。

### 10.3 opt：纯数据视图

`opt` 返回的代理对象不占用任何公开属性名（`__slots__` 只有一个下划线属性），
所以 `opt.` 后面写什么都是配置键。**每个节点都有 `opt`，不限于顶层。**

```python
cfg = Config({'save': True, 'items': [1, 2], 'db': {'get': 'x'}})

cfg.opt.save        # True
cfg.opt.items       # [1, 2]        ← 不是 dict.items() 方法
cfg.opt.db.get      # 'x'           ← 嵌套层一路 opt 下去
cfg.opt.save = False              # 属性写
cfg.opt['path'] = '/tmp'          # 下标写也行
del cfg.opt.save                  # 删除
cfg.opt.db == {'get': 'x'}        # 能直接和 dict 比
cfg.opt('save')                   # 等价于 get('save')
len(cfg.opt) / 'save' in cfg.opt / list(cfg.opt)
cfg.opt             # 整层数据的 repr
```

`opt.opt` 也能拿到名为 `opt` 的配置键（代理不占用名字）。

### 10.4 遮蔽情况可查

```python
cfg = Config({'save': 1, 'db': {'items': 2}}, file='app.toml')

cfg.shadowed          # ('save',)                    本层
cfg.find_shadowed()   # {'.': ('save',), 'db': ('items',)}   整棵树
```

构造 / 批量写入后如果存在遮蔽键，库会打 `logging.warning` 点名并指路（同一批键只报一次），
不会静默。CI 里可以硬失败：

```python
assert not cfg.find_shadowed(), cfg.find_shadowed()
```

---

## 11. 魔法方法

### 11.1 支持的操作

```python
cfg = Config({'a': 1, 'b': {'c': 2}})

# 属性访问（与接口同名的键拿不到，见 §10）
cfg.a               # 1
cfg.b.c             # 2
cfg.b               # ConfigNode({'c': 2})

# 字典访问（读写删都支持点路径）
cfg['a']            # 1
cfg['b.c']          # 2
cfg['b.c'] = 3
del cfg['b.c']

# 删除
del cfg.a

# 长度 / 迭代 / 包含 / 布尔
len(cfg)            # 2
for key in cfg: ...
'a' in cfg          # True
'b.c' in cfg        # True（点路径）
bool(cfg)           # 非空为 True

# 调用方式（等价于 get，可带默认值）
cfg('b.c')          # 3
cfg('missing', 0)   # 0

# dict 协议（Config 与 ConfigNode 都是 MutableMapping）
cfg.keys() / cfg.values() / cfg.items()
cfg.pop('a'); cfg.popitem(); cfg.clear()
dict(cfg)           # 顶层键的原生 dict（嵌套值仍是 ConfigNode）
cfg == {'a': 1, 'b': {'c': 3}}   # True，直接和 dict 比
cfg | {'z': 9}      # 合并成新 dict，不改原配置
cfg |= {'y': 8}     # 原地合并（会落盘）

# 缺失键
cfg['nope']         # ❌ ConfigKeyError（同时是 KeyError，消息带指路）
cfg.nope            # ❌ AttributeError
```

### 11.2 上下文管理器

```python
# 退出时自动保存
with Config('app.toml', auto_save=False) as cfg:
    cfg.name = 'app'
    cfg.version = '1.0'
# 退出时自动调用 save()
```

---

## 12. 属性信息

### 12.1 path / path_abs

```python
path() -> str       # 返回绝对路径
path_abs() -> str   # 返回绝对路径（与 path() 相同）

cfg = Config('app.toml')
cfg.path()          # '/absolute/path/to/app.toml'
cfg.path_abs()      # '/absolute/path/to/app.toml'
```

### 12.2 is_auto_save / set_auto_save

```python
is_auto_save() -> bool
set_auto_save(flag: bool) -> None

cfg.is_auto_save()          # True
cfg.set_auto_save(False)    # 关闭自动保存
cfg.is_auto_save()          # False
```

---

## 13. 错误处理

### 13.1 异常层次结构

```python
ConfigError (基类, .message 保存原始消息)
├── ConfigIOError (文件 I/O 错误)
├── ConfigValidationError (用法错误：类型、路径、键名冲突)
│   └── ConfigKeyError (键不存在；同时继承 KeyError，.key 保存缺失键)
└── ConfigEncryptionError (加密/解密错误)
```

`ConfigKeyError` 继承 `KeyError`，因此 `cfg['nope']`、`cfg.pop('nope')`、`dict(cfg)`
的异常处理和普通 dict 一致；`get()` / `first()` / `del_key()` 不抛异常。

### 13.2 常见异常

| 异常类型 | 原因 | 解决方案 |
|----------|------|----------|
| `ConfigKeyError`（`KeyError`） | 下标 / `pop` 的键或点路径不存在 | 用 `get(key, default)`、`first(...)` 或 `set()` 创建 |
| `ConfigValidationError` | 属性写撞接口名（`cfg.save = 1`） | 改 `cfg['save'] = 1` 或 `cfg.opt.save = 1` |
| `ConfigValidationError` | 叶子/节点结构冲突且 `overwrite_mode=False` | 传 `overwrite_mode=True`，或直接下标赋值 |
| `ConfigValidationError` | schema 类型不符 | 检查 schema 与实际类型（`bool` 不再被当作 `int`） |
| `ConfigValidationError` | 初始数据不是 dict / 文件内容不是键值结构 | 首参数是文件名或 dict；换格式或检查文件 |
| `ConfigEncryptionError` | 加密文件密码错误 / 密文被篡改 | 用正确密码；`save()` 会先试解再覆盖 |
| `ConfigEncryptionError` | 加密文件未提供密码 | 传 `pwd=` |
| `ConfigIOError` | 文件读写失败、目录创建失败 | 检查权限与路径 |
| `ImportError` | 用了未安装的可选能力 | 按提示装：`pip install 'confull[encrypt]'` 等 |

### 13.3 错误信息增强

```python
# 键不存在时提示兜底写法
cfg = Config({'a': 1})
cfg['b']
# ConfigKeyError: "键 'b' 不存在。可用 get('b', default) 兜底，或 set('b', value) 创建。"

# 路径断裂时指出断在哪一段
cfg = Config({'a': 1})
cfg['a.b.c']
# ConfigKeyError: "路径 'a.b.c' 中 'b' 的上游不是可继续查找的节点。"

# 属性写撞接口名时给出两种可用写法
cfg.save = 1
# ConfigValidationError: "'save' 与本层接口同名，属性写法无法写入。请改用 ['save'] = 1 或 opt.save = 1。"

# 类型验证失败
cfg = Config(file='app.toml', schema={'port': int})
cfg.port = True
# ConfigValidationError: "键 'port' 期望类型 int，实际得到 bool"

# 首参数传错类型时直接教怎么写
ConfigNode([1, 2])
# ConfigValidationError: "配置数据必须是 dict，实际得到 list: [1, 2]。若第一个参数想传文件名，请写成 Config(file=[1, 2])。"
```

---

## 14. 线程与进程安全

### 14.1 线程安全

- 顶层 `Config` 持有 `RLock`，**标脏与落盘**（`notify_dirty` → `save` → 展开快照 → 原子替换）
  全程持锁，嵌套节点的变更会冒泡到这把锁上，所以文件不会被写坏。
- 单个键的赋值本身不再额外加锁：多线程同时改多个键时，某一次落盘可能只包含其中一部分改动
  （Python 的 dict 单键写入是原子的，不会撕裂结构）。
- **跨多个键的读-改-写不是原子的**。要让一批改动要么全进文件要么全不进，
  用 `with cfg.transaction():` 并在外层加一把自己的业务锁。
- `debounce_ms > 0` 时保存由后台 `threading.Timer` 执行（daemon），进程退出会再 flush 一次。

### 14.2 进程安全

```python
# 启用进程锁（多进程场景）；需要 confull[process]
cfg = Config('shared.toml', process_safe=True)

# 关闭进程锁（单进程高性能场景）
cfg = Config('app.toml', process_safe=False)
```

读取拿共享锁、写入拿排他锁，锁文件是 `<配置文件>.lock`，写成功后会尝试清理。
`enable_watch()` 与 `process_safe` 正交：监听只解决「外部改了我去 reload」，不解决并发写。

### 14.3 加密与性能

```python
cfg = Config('secure.toml', pwd='my-secret-key')     # 需要 confull[encrypt]
```

- 格式：`ENCRYPT_HEADER(16B) + salt(8B) + Fernet(token)`，明文 JSON 序列化后加密
- 密钥派生：PBKDF2-HMAC-SHA256，100k 轮 → Fernet（AES128-CBC + HMAC-SHA256）
- **同一实例复用 salt 并缓存派生结果**，所以自动保存不会被 KDF 拖慢（实测每次赋值的
  加密落盘约 0.9ms，0.1.x 每次重新派生约 23.5ms）
- salt 长度是文件格式的一部分，不能改：改了就读不出 0.1.x 及 0.2.0 已写出的文件
- 换密码要显式走「旧密码读出 → 新密码写回」两步，没有 `set_password()`
- `save()` 前会用当前密码试解既有密文，解不开就抛 `ConfigEncryptionError` 拒绝覆盖

### 14.4 退出时的落盘

实例通过弱引用登记在一个模块级列表里，`atexit` 钩子统一 flush 仍在世的脏实例
（列表长度到 32 时清理死引用）。也就是说：即使用户忘了 `save()`，
正常退出时数据仍会写盘；异常退出（`os._exit`、断电）不保证。

---

## 15. 最佳实践

### 15.1 批量操作

```python
# ✅ 推荐：transaction()，自动保存照常开着，只写一次盘
with cfg.transaction():
    for i in range(100):
        cfg[f'item.{i}'] = f'value_{i}'

# ✅ 也可以：关闭自动保存，退出上下文时手动保存
with Config('app.toml', auto_save=False) as cfg:
    for i in range(100):
        cfg.set(f'item.{i}', f'value_{i}')

# ⚠️ 下面这种写法在 0.2.0 已经不是「每次都保存」：
cfg = Config('app.toml')
for i in range(100):
    cfg.set(f'item.{i}', f'value_{i}')   # 每次赋值仍会保存一次，慢
# 需要频繁赋值时套上 transaction()
```

### 15.2 去抖延迟

```python
# 高频写入场景
cfg = Config('app.toml', debounce_ms=100)
# 100ms 内多次写入只保存一次
```

### 15.3 配置合并

```python
# 默认配置 + 用户配置
default = Config('default.toml')
user = Config('user.toml')
default.merge(user, strategy='deep')
```

### 15.4 环境变量覆盖

```python
# 基础配置 + 环境变量覆盖（嵌套用 __）
cfg = Config('app.toml')
cfg.from_env(prefix='MYAPP')

# 反向：导出给子进程 / Docker
os.environ.update(cfg.to_env(prefix='MYAPP'))
```

### 15.5 多环境切换

```python
# 开发环境
cfg = Config('app.toml', env='dev')
# 自动加载 app.dev.toml

# 生产环境 + 环境变量覆盖
cfg = Config('app.toml', env='production', env_prefix='MYAPP')
# 1. 加载 app.toml
# 2. 合并 app.production.toml
# 3. 导入 MYAPP_* 环境变量
```

### 15.6 类型验证

```python
# 定义 schema
schema = {'port': int, 'debug': bool, 'name': str}

# 创建配置
cfg = Config('app.toml', schema=schema)

cfg.port = "8080"   # ❌ ConfigValidationError
cfg.port = 8080     # ✅

# 文件里的内容不受 schema 约束，启动时自己过一次
cfg.validate()      # 不合格抛 ConfigValidationError
```

### 15.7 与接口同名的键

```python
cfg = Config({'save': True, 'items': [1, 2]})

cfg.save            # ❌ 拿到的是 save() 方法
cfg['save']         # ✅ True
cfg.opt.save        # ✅ True

cfg.save = False    # ❌ ConfigValidationError（不会把方法悄悄替换掉）
cfg['save'] = False # ✅
cfg.opt.save = False# ✅
```

### 15.8 键名来自外部时一律用下标

动态来源（用户上传的表头、远端下发、别人手写的配置文件）永远不要拼成属性写：

```python
for key, value in incoming.items():
    cfg[key] = value          # ✅ 容器语义，任何键名都能写
    # setattr(cfg, key, value)  # ❌ 撞接口名就抛异常
```

批量场景直接 `cfg.update(incoming)`，它本来就是容器语义，还只写一次盘。
写完后自检一遍遮蔽情况：

```python
if cfg.find_shadowed():
    logging.warning('这些键属性访问拿不到: %s', cfg.find_shadowed())
```

---

## 16. API 速查表

### 构造

| 签名 | 说明 |
|------|------|
| `Config(文件名或初始数据, file, way, replace, auto_save, pwd, process_safe, debounce_ms, env, env_prefix, schema, *, data)` | 创建配置管理器；首参可以是 `'app.toml'` 或 `{...}` |

### 读写

| 方法 | 语义 | 返回值 |
|------|------|--------|
| `cfg.key` / `cfg['key']` / `cfg['a.b']` | 读；下标支持点路径 | 值或 `ConfigNode` |
| `cfg.key = v` / `cfg.set(k, v)` | 属性写，撞接口名报错 | `set` 返回 self |
| `cfg['k'] = v` / `cfg.opt.k = v` | 容器写，任何键名都行 | — |
| `get(key, default)` | 获取值 | 值或默认值 |
| `setdefault(key, value)` | 设置默认值 | 最终值 |
| `first(*keys, default)` | 第一个存在的键 | 值或默认值 |
| `require(key)` | 必需配置 | 值，否则 `ConfigValidationError` |

### 批量

| 方法 | 说明 |
|------|------|
| `update(dict)` | 批量更新（容器语义，一次落盘） |
| `set_data(dict)` | 完全替换（容器语义，一次落盘） |
| `merge(other, strategy)` | 合并：`override`/`keep`/`deep`（一次落盘） |
| `transaction(rollback_on_error=True)` | 上下文：块内不写盘，退出写一次；异常回滚 |
| `from_env(prefix, separator)` | 导入环境变量（容器语义，一次落盘） |

### 删除

| 方法 | 说明 |
|------|------|
| `del_key(key)` | 删除键（支持点路径），清理空父节点，返回 bool |
| `del_clean()` | 清空并删除文件，返回 bool |
| `pop(key, default)` / `popitem()` / `clear()` | dict 协议，同样落盘，不清理空父节点 |

### 文件

| 方法 | 说明 |
|------|------|
| `save()` | 立即保存（dirty 才写；pwd 会先试解既有密文） |
| `reload()` | 从磁盘重新加载 |
| `load(file, way)` | 切换目标文件/格式，不读取内容 |
| `to_file(file, way)` | 另存为 |
| `enable_watch()` / `disable_watch()` | 文件监听（外部改动才 reload） |

### 导入导出

| 方法 | 说明 |
|------|------|
| `to_dict()` | 导出为原生 dict（每层新建；节点也有） |
| `to_json(indent)` | 导出为JSON |
| `to_env(prefix, uppercase, separator='__')` | 导出为环境变量（前缀 `_`、嵌套 `__`） |
| `from_env(prefix, separator='__')` | 从环境变量导入，与 `to_env` 互逆 |

### 命名冲突与校验

| 成员 | 说明 |
|------|------|
| `opt` | 纯数据视图，每个节点都有；读写任何键都不撞名 |
| `shadowed` | 本层被接口名遮蔽的配置键（tuple） |
| `reserved` | 本层全部接口名（tuple，运行时派生） |
| `find_shadowed()` | 整棵树的遮蔽情况，返回 `{点路径: (键, ...)}` |
| `validate()` | 按 schema 检查当前全部值（含文件加载进来的） |

### 多环境与类型验证

| 参数 | 说明 |
|------|------|
| `env` | 环境名称，自动合并 app.{env}.toml |
| `env_prefix` | 环境变量前缀，自动导入 {prefix}* 环境变量 |
| `schema` | 类型验证 schema，如 {'port': int, 'db.host': str}；不校验文件内容 |

### 比较

| 方法 | 说明 |
|------|------|
| `diff(other)` | 比较差异，返回 `added`/`removed`/`modified` |
| `cfg == {...}` | 与普通 dict 直接比较 |
| `cfg \| {...}` / `cfg \|= {...}` | 合并成新 dict / 原地合并 |

### 状态

| 方法 | 说明 |
|------|------|
| `path()` | 绝对路径 |
| `path_abs()` | 绝对路径（与 `path()` 相同） |
| `is_auto_save()` | 是否自动保存 |
| `set_auto_save(flag)` | 设置自动保存 |
| `mark_dirty()` / `notify_dirty()` | 标脏 / 节点冒泡用的内部入口 |

---

## 17. 注意事项清单

1. **命名冲突规则**：属性写法（`cfg.k = v` / `set()`）撞接口名就抛 `ConfigValidationError`
   并指路；容器写法（`cfg['k']` / `cfg.opt.k` / `update` / `merge` / `set_data` / `from_env` /
   加载文件）永远放行。接口名单运行时派生，用 `cfg.reserved` 查
2. **遮蔽可查**：`cfg.shadowed`（本层）、`cfg.find_shadowed()`（整棵树）；
   构造和批量写入后会自动打一条 `logging.warning`
3. **`opt` 每层都有**：`cfg.db.opt.get`、`cfg.opt.items`，代理不占用任何公开属性名
4. **`Config` 是 `MutableMapping`**：`items/keys/values/pop/popitem/clear/update` 是方法，
   因此这些名字的顶层配置键属性读会被遮蔽 —— 这是把 dict 协议换来的代价，`find_shadowed()` 兜底
5. **`to_dict()` 不是深拷贝**：逐层新建 dict，可变叶子值（list 等）仍是同一引用
6. **旧 `node.data` / `node.dict` 已移除**：改用 `to_dict()`；`data`、`dict` 现在可以当普通配置键
7. **结构冲突**：叶子 ↔ 节点互转需要 `set(..., overwrite_mode=True)`，直接下标赋值不受限
8. **schema 范围**：覆盖任意深度的写入路径和整棵子树赋值，区分 `bool`/`int`；
   **不校验从文件读进来的内容**，需要时显式 `cfg.validate()`
9. **环境变量**：`to_env` 前缀用 `_`、嵌套用 `__`（`MY_DB__HOST`），与 `from_env` 互逆；
   值一律是字符串；前缀是 `startswith` 匹配，别用太短（Windows 上 `APP` 会撞上 `APPDATA`）
10. **批量写入**：`update`/`set_data`/`merge`/`from_env` 一次调用只落盘一次；
    自定义批量用 `with cfg.transaction():`（异常默认回滚且不写盘）
11. **加密**：忘记密码无法恢复数据；换密码要走「旧密码读出 → 新密码写回」；
    `save()` 前会试解既有密文，密码不对拒绝覆盖；salt 固定 8 字节（改了就读不出旧文件）
12. **可选依赖**：`yaml` / `encrypt` / `watch` / `process` 是 extras，按需导入，
    缺了会在真正用到时抛 `ImportError` 并给出 `pip install 'confull[...]'` 提示
13. **watchdog**：建议程序退出前 `disable_watch()`（析构也会兜底）；自己写盘不会触发 reload
14. **线程**：落盘有顶层 `RLock`，跨多键的读-改-写不是原子操作；并发批量改动请自己加锁
15. **退出落盘**：`atexit` 会 flush 仍存活的脏实例；`os._exit` / 断电不保证
16. **INI 格式限制**：嵌套结构展平为点路径键，`DEFAULT` 段单独成节，所有值读回是字符串
17. **XML 格式限制**：所有值读回是字符串；同名兄弟节点会被合并成一个键（后者覆盖前者）
18. **异常类型**：`ConfigError` / `ConfigIOError` / `ConfigValidationError` /
    `ConfigKeyError`(也是 `KeyError`) / `ConfigEncryptionError`
19. **`path()` 与 `path_abs()`** 都返回绝对路径
20. **链式操作**：`set` / `merge` / `from_env` 返回 self
