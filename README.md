# confull

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [AI](https://github.com/zisull/confull/blob/main/doc/README-ai-zh.md)

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
- 支持自动保存（即时持久化，无延迟）
- 支持加密存储（传入 pwd 参数即可自动加密和解密配置文件）
- 线程安全
- 支持文件变更监听 (`enable_watch` / `disable_watch`)，外部修改后自动重载
- 进程安全：可选 `portalocker` 跨进程锁 (`process_safe=False` 默认关闭，可设为 True 以跨进程安全)
- 键名冲突防护：若顶层键名与内部接口同名（如 `to_dict`、`clean_del` 等）将抛出 `AttributeError`，避免意外覆盖
- 自动补全（Autovivification）：链式赋值时自动创建中间节点

### 变更说明

- **已移除备份功能**，简化配置管理。
- **新增加密功能**，只需传入 `pwd` 参数，即可自动加密和解密配置文件。

### 使用示例（新增文件监听）

```python
from confull import Config

cfg = Config(file='watch_demo.toml')

# 开启监听：当 watch_demo.toml 被外部程序修改后，cfg 会自动 reload()
cfg.enable_watch()

# 1. 普通用法
cc = Config()
cc.set('user', 'admin')
print(cc.get('user'))  # admin

# 2. 加密用法
cc = Config(file='secure.toml', way='toml', pwd='123456')
cc.set('token', 'xyz')
print(cc.get('token'))  # xyz

# 3. 点路径写入和读取
cc.set('db.host', '127.0.0.1', overwrite_mode=True)
cc.set('db.port', 3306, overwrite_mode=True)
print(cc.get('db.host'))  # 127.0.0.1
print(cc.get('db.port'))  # 3306

# 4. dict方式批量赋值
cc.set_data({'user': 'root', 'password': 'pass'})
print(cc['user'])  # root

# 5. 属性方式赋值和读取
cc.site = 'mysite'
print(cc.site)  # mysite

# 6. 删除配置项
cc.del_key('user')
print(cc.get('user'))  # None

# 7. 批量更新
cc.update({'email': 'a@b.com', 'db.host': 'localhost'})
print(cc.get('email'))  # a@b.com
print(cc.get('db.host'))  # localhost

# 8. 清空并删除配置文件
cc.clean_del()

# 9. 另存为其他格式
cc = Config({'user': 'admin'}, file='a.toml', way='toml')
cc.to_file(file='a.yaml', way='yaml')

# 若不再需要监听，可关闭
cfg.disable_watch()

# 进程安全开关示例（高级场景）
cfg_safe = Config(file='shared.toml', process_safe=True)  # 默认即安全
cfg_fast = Config(file='shared.toml', process_safe=False)  # 关闭进程锁，单进程场景
```

---

## 二、安装

在命令行中运行以下命令来安装 `confull`：

```bash
# 推荐使用 PyPI 包（已自动处理依赖）
pip install confull

# 若手动安装依赖，可执行
pip install orjson toml pyyaml watchdog portalocker configparser
```

---

## 三、类和方法说明

### 1. `Config` 类

该类是配置管理器的核心，负责配置数据的读写、保存等操作。

#### 初始化方法 `__init__`

```python
def __init__(self,
             data: dict | None = None,
             file: str = "config",
             way: str = "toml",
             replace: bool = False,
             auto_save: bool = True,
             pwd: str | None = None,
             process_safe: bool = False):
```
- 新增参数 `pwd`，用于加密配置文件。
- 已移除参数 `backup`。

#### 核心方法速查

| 方法 | 说明 |
|------|------|
| `get(key, default=None)` | 读取键，支持点路径 |
| `set(key, value, *, overwrite_mode=False)` | 写入键；标量↔️字典冲突须 `overwrite_mode=True` |
| `update(dict_like)` | 批量写入（点路径支持） |
| `del_key(key)` | 删除键 |
| `clean_del()` | 清空并删除配置文件 |
| `to_dict()` | 返回深拷贝 `dict` 数据 |
| `to_json(indent=2)` | JSON 字符串 |
| `is_auto_save()` / `set_auto_save(flag)` | 获取 / 设置自动保存状态 |
| `path()` / `path_abs()` | 相对 / 绝对路径 |
| `save()` | 立即保存（忽略去抖） |
| `to_file(file, way)` | 另存为其它文件 / 格式 |
| `enable_watch()` / `disable_watch()` | 开 / 关文件监听 |

#### 魔法方法

| 魔法方法名                                  | 描述                                                   |
| ------------------------------------------- | ------------------------------------------------------ |
| `__del__()`                                 | 对象销毁时，若 `auto_save` 为 `True`，会自动保存配置。 |
| `__getattr__(self, item)`                   | 属性访问代理到配置数据。                               |
| `__getitem__(self, item)`                   | `dict` 方式访问配置数据。                              |
| `__call__(self, key, value=None)`           | `cc(key)` 等价于 `cc.get(key, value)`。               |
| `__len__(self)`                             | 配置项数量。                                           |
| `__iter__(self)`                            | 遍历配置项。                                           |
| `__contains__(self, item)`                  | 判断配置项是否存在。                                   |
| `__bool__(self)`                            | 配置是否非空。                                         |
| `__enter__(self)`                           | 上下文管理器 `enter`。                                 |
| `__exit__(self, exc_type, exc_val, exc_tb)` | 上下文管理器 `exit`，自动保存。                        |
| `__setattr__(self, key, value)`             | 属性赋值代理到配置数据，内部属性用 `_` 前缀。          |
| `__delattr__(self, key)`                    | 属性删除代理到配置数据。                               |

---

## 四、使用技巧与注意事项

### 4.1 常见注意事项

1. **键名冲突** – 顶层键若与 `_CONF_RESERVED` 列表冲突会抛 `AttributeError`；若必须使用类似名字，请放到子节点中，如 `meta.to_dict`。
2. **去抖延迟** – 频繁写场景请设置 `debounce_ms`（毫秒）。0 表示立即保存；100–500 ms 可显著降低磁盘 I/O。
3. **进程锁 vs 性能** – `process_safe=True` 可避免多进程竞争，但在单进程密集写时略微降低速度；可按需关闭。
4. **加密不可逆** – 丢失密码将无法解密；文件被篡改会触发 HMAC 校验错误并拒绝加载。
5. **watchdog** – 监听线程以 `DirWatcher-<id>` 命名；在单元测试结束应 `disable_watch()` 关闭，避免残留线程。

### 4.2 高级示例

```python
from confull import Config

# 1) 加密 + 去抖保存（100 ms），支持 toml
cfg = Config({'token': 'abc'}, file='secure.toml', pwd='secret', debounce_ms=100)
cfg.set('log.level', 'INFO')

# 2) 上下文批量操作
with Config(file='batch.yaml', auto_save=False) as c:
    c.set_data({'app': {'ver': '1.2'}, 'features': ['x', 'y']})
    c.to_file('backup.json', way='json')  # 退出时自动 save()

# 3) 开启文件监听
cfg_watch = Config(file='live.toml')
cfg_watch.enable_watch()

# 4) 进程安全共享配置
shared = Config(file='shared.toml', process_safe=True)
# ... 跨进程读写

# 5) 清理
shared.clean_del()
```

### 4.3 玩法小技巧

* **链式赋值** – `cfg.app.version.build = 5` 可一次性创建深层键。
* **函数式读取** – `value = cfg('a.b', default=0)` 等价于 `cfg.get(...)`，适合快速取值。
* **混合更新** – `update({'a': 1, 'b.c': 2})` 同时支持顶层与点路径键。
* **动态格式切换** – 任意时刻可 `cfg.load(file='x.yaml', way='yaml')` 改写目标文件与格式。
* **安全回收** – `clean_del()` 在单元测试或临时文件场景快速清理磁盘与内存。
* **只读模式** – 将配置文件权限设为只读，仍可使用 `get()` 快速获取数据；写入将抛出异常，可用于生产只读节点。
* **跨模块共享** – 在不同模块中 `Config(file='same.toml')` 打开同一文件，实现配置中心。

---