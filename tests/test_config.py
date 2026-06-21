# -*- coding: utf-8 -*-
"""confull 全面测试套件

覆盖所有功能的单元测试：
1. 基础读写与更新
2. 文件持久化与去抖保存
3. 删除操作
4. 多格式支持
5. 加密功能
6. 进程安全
7. 文件监听（watchdog）
8. 便捷方法（setdefault/first/require）
9. 链式操作
10. 配置合并（merge）
11. 配置对比（diff）
12. 环境变量导入导出
13. 运算符支持
14. 高级特性与魔法方法
"""

import gc
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from confull import Config
from confull import ConfigError, ConfigIOError, ConfigValidationError, ConfigEncryptionError
from confull.node import ConfigNode

try:
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class TempDirTestCase(unittest.TestCase):
    """为所有测试提供隔离的临时工作目录。"""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp_dir = tempfile.mkdtemp()
        os.chdir(self._tmp_dir)
        self._created_files = []

    def tearDown(self):
        for th in threading.enumerate():
            if th.name.startswith("DirWatcher") and hasattr(th, "stop"):
                th.stop()
                th.join(timeout=0.2)
        gc.collect()
        os.chdir(self._old_cwd)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._created_files.clear()

    def _f(self, name: str) -> str:
        path = os.path.join(self._tmp_dir, name)
        self._created_files.append(path)
        return path


# ===========================================================
# 1) 基础读写与更新
# ===========================================================


class BasicReadWriteTests(TempDirTestCase):
    """基础增删改查测试。"""

    def test_set_and_get(self):
        """测试 set 和 get 方法。"""
        cfg = Config({'a': 1}, file=self._f('basic.toml'))
        self.assertEqual(cfg.get('a'), 1)
        cfg.set('b', 2)
        self.assertEqual(cfg.get('b'), 2)

    def test_attribute_access(self):
        """测试属性方式访问。"""
        cfg = Config({'name': 'app'}, file=self._f('attr.toml'))
        self.assertEqual(cfg.name, 'app')
        cfg.version = '1.0'
        self.assertEqual(cfg.version, '1.0')

    def test_dict_access(self):
        """测试字典方式访问。"""
        cfg = Config({'a': 1}, file=self._f('dict.toml'))
        self.assertEqual(cfg['a'], 1)
        cfg['b'] = 2
        self.assertEqual(cfg['b'], 2)

    def test_nested_access(self):
        """测试嵌套访问。"""
        cfg = Config({'db': {'host': 'localhost'}}, file=self._f('nested.toml'))
        self.assertEqual(cfg.db.host, 'localhost')
        cfg.set('db.port', 3306)
        self.assertEqual(cfg.get('db.port'), 3306)

    def test_dot_path_access(self):
        """测试点路径访问。"""
        cfg = Config({'a': {'b': {'c': 1}}}, file=self._f('dotpath.toml'))
        self.assertEqual(cfg.get('a.b.c'), 1)
        self.assertEqual(cfg['a.b.c'], 1)

    def test_update_batch(self):
        """测试批量更新。"""
        cfg = Config({'a': 1}, file=self._f('update.toml'))
        cfg.update({'b': 2, 'c': 3})
        self.assertEqual(cfg.b, 2)
        self.assertEqual(cfg.c, 3)

    def test_set_data(self):
        """测试完全替换数据。"""
        cfg = Config({'old': 'data'}, file=self._f('setdata.toml'))
        cfg.set_data({'new': 'data'})
        self.assertEqual(cfg.new, 'data')
        self.assertIsNone(cfg.get('old'))

    def test_overwrite_mode(self):
        """测试覆盖模式。"""
        cfg = Config(file=self._f('overwrite.toml'))
        cfg.set('x', 1)
        with self.assertRaises(ConfigValidationError):
            cfg.set('x.y', 2)
        cfg.set('x.y', 2, overwrite_mode=True)

    def test_leaf_to_node_conflict(self):
        """测试叶子节点转字典节点冲突。"""
        cfg = Config(file=self._f('conflict.toml'))
        cfg.set('value', 'leaf')
        with self.assertRaises(ConfigValidationError):
            cfg.set('value.key', 'node')
        cfg.set('value.key', 'node', overwrite_mode=True)

    def test_node_to_leaf_conflict(self):
        """测试字典节点转叶子节点冲突。"""
        cfg = Config(file=self._f('conflict2.toml'))
        cfg.set('dict', {'key': 'value'})
        with self.assertRaises(ConfigValidationError):
            cfg.set('dict', 'leaf')
        cfg.set('dict', 'leaf', overwrite_mode=True)


# ===========================================================
# 2) 文件持久化
# ===========================================================


class PersistenceTests(TempDirTestCase):
    """保存/加载/格式转换测试。"""

    def test_save_and_load(self):
        """测试保存和加载。"""
        fn = self._f('save_load.toml')
        Config({'k': 'v'}, file=fn).save()
        self.assertEqual(Config(file=fn).k, 'v')

    def test_to_file_conversion(self):
        """测试格式转换。"""
        toml_path = self._f('a.toml')
        json_path = self._f('a.json')
        Config({'x': 1}, file=toml_path).to_file(json_path, way='json')
        self.assertEqual(Config(file=json_path, way='json').x, 1)

    def test_auto_save(self):
        """测试自动保存。"""
        fn = self._f('auto.toml')
        cfg = Config(file=fn)
        cfg.msg = 'hello'
        cfg2 = Config(file=fn)
        self.assertEqual(cfg2.msg, 'hello')

    def test_no_auto_save(self):
        """测试关闭自动保存。"""
        fn = self._f('noauto.toml')
        cfg = Config({'a': 1}, file=fn, auto_save=False)
        cfg.b = 2
        cfg2 = Config(file=fn)
        self.assertIsNone(cfg2.get('b'))

    def test_context_manager(self):
        """测试上下文管理器。"""
        fn = self._f('ctx.toml')
        with Config(file=fn, auto_save=False) as c:
            c.token = 123
        self.assertEqual(Config(file=fn).token, 123)

    def test_debounce(self):
        """测试去抖保存。"""
        fn = self._f('debounce.toml')
        cfg = Config({}, file=fn, debounce_ms=50)
        cfg.msg = 'hi'
        time.sleep(0.1)
        self.assertEqual(Config(file=fn).msg, 'hi')


# ===========================================================
# 3) 删除操作
# ===========================================================


class DeleteOperationTests(TempDirTestCase):
    """删除操作测试。"""

    def test_del_key(self):
        """测试删除键。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('del.toml'))
        cfg.del_key('a')
        self.assertIsNone(cfg.get('a'))
        self.assertEqual(cfg.b, 2)

    def test_del_nested_key(self):
        """测试删除嵌套键。"""
        cfg = Config({'a': {'b': {'c': 1, 'd': 2}}}, file=self._f('delnest.toml'))
        cfg.del_key('a.b.c')
        self.assertIsNone(cfg.get('a.b.c'))
        self.assertEqual(cfg.get('a.b.d'), 2)

    def test_del_key_cleanup(self):
        """测试删除键后自动清理空父节点。"""
        cfg = Config({'a': {'b': {'c': 1}}, 'd': 2}, file=self._f('cleanup.toml'))
        cfg.del_key('a.b.c')
        self.assertIsNone(cfg.get('a'))

    def test_del_clean(self):
        """测试清空配置。"""
        fn = self._f('delclean.toml')
        cfg = Config({'x': 1}, file=fn)
        cfg.del_clean()
        self.assertFalse(os.path.exists(fn))
        self.assertEqual(len(cfg), 0)


# ===========================================================
# 4) 多格式支持
# ===========================================================


class FormatTests(TempDirTestCase):
    """多格式支持测试。"""

    def test_json_format(self):
        """测试 JSON 格式。"""
        fn = self._f('test.json')
        cfg = Config({'key': 'value'}, file=fn, way='json')
        self.assertEqual(Config(file=fn, way='json').key, 'value')

    def test_toml_format(self):
        """测试 TOML 格式。"""
        fn = self._f('test.toml')
        cfg = Config({'key': 'value'}, file=fn, way='toml')
        self.assertEqual(Config(file=fn, way='toml').key, 'value')

    def test_yaml_format(self):
        """测试 YAML 格式。"""
        fn = self._f('test.yaml')
        cfg = Config({'key': 'value'}, file=fn, way='yaml')
        self.assertEqual(Config(file=fn, way='yaml').key, 'value')

    def test_ini_format(self):
        """测试 INI 格式。"""
        fn = self._f('test.ini')
        cfg = Config({'section': {'key': 'value'}}, file=fn, way='ini')
        self.assertEqual(Config(file=fn, way='ini').section.key, 'value')

    def test_xml_format(self):
        """测试 XML 格式。"""
        fn = self._f('test.xml')
        cfg = Config({'key': 'value'}, file=fn, way='xml')
        self.assertEqual(Config(file=fn, way='xml').key, 'value')

    def test_auto_detect_format(self):
        """测试自动检测格式。"""
        fn = self._f('auto.json')
        cfg = Config({'key': 'value'}, file=fn)
        self.assertEqual(Config(file=fn).key, 'value')

    def test_txt_with_way(self):
        """测试 txt 扩展名指定格式。"""
        fn = self._f('test.txt')
        cfg = Config({'key': 'value'}, file=fn, way='toml')
        self.assertEqual(Config(file=fn, way='toml').key, 'value')


# ===========================================================
# 5) 加密功能
# ===========================================================


class EncryptionTests(TempDirTestCase):
    """加密功能测试。"""

    def test_encrypt_decrypt(self):
        """测试加密和解密。"""
        fn = self._f('secure.toml')
        pwd = 'my-secret'
        Config({'token': 'abc'}, file=fn, pwd=pwd).save()
        self.assertEqual(Config(file=fn, pwd=pwd).token, 'abc')

    def test_wrong_password(self):
        """测试错误密码。"""
        fn = self._f('wrong.toml')
        Config({'token': 'abc'}, file=fn, pwd='correct').save()
        with self.assertRaises(Exception):
            Config(file=fn, pwd='wrong')

    def test_tampered_file(self):
        """测试篡改文件。"""
        fn = self._f('tamper.toml')
        Config({'x': 'y'}, file=fn, pwd='p').save()
        with open(fn, 'rb+') as f:
            data = bytearray(f.read())
            data[30:40] = b'0' * 10
            f.seek(0)
            f.write(data)
        with self.assertRaises(ConfigEncryptionError):
            Config(file=fn, pwd='p')

    def test_no_password_for_encrypted_file(self):
        """测试不提供密码访问加密文件。"""
        fn = self._f('nopwd.toml')
        Config({'secret': 'data'}, file=fn, pwd='key').save()
        with self.assertRaises(ConfigEncryptionError):
            Config(file=fn)


# ===========================================================
# 6) 文件监听
# ===========================================================


class WatchdogTests(TempDirTestCase):
    """文件监听测试。"""

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog 未安装")
    def test_file_watcher_reload(self):
        """测试文件监听自动重载。"""
        fn = self._f('watch.toml')
        Path(fn).write_text('ver = 1')
        cfg = Config(file=fn)
        cfg.enable_watch()
        try:
            Path(fn).write_text('ver = 2')
            for _ in range(10):
                time.sleep(0.5)
                if cfg.ver == 2:
                    break
            self.assertEqual(cfg.ver, 2)
        finally:
            cfg.disable_watch()

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog 未安装")
    def test_watchdog_thread_naming(self):
        """测试 watchdog 线程命名。"""
        fn = self._f('thread.toml')
        cfg = Config(file=fn)
        cfg.enable_watch()
        try:
            time.sleep(0.1)
            self.assertTrue(any(th.name.startswith("DirWatcher-") for th in threading.enumerate()))
        finally:
            cfg.disable_watch()


# ===========================================================
# 7) 便捷方法
# ===========================================================


class ConvenienceMethodTests(TempDirTestCase):
    """便捷方法测试。"""

    def test_setdefault_new_key(self):
        """测试 setdefault 设置新键。"""
        cfg = Config(file=self._f('sd1.toml'))
        result = cfg.setdefault('version', '1.0')
        self.assertEqual(result, '1.0')
        self.assertEqual(cfg.version, '1.0')

    def test_setdefault_existing_key(self):
        """测试 setdefault 不覆盖已存在键。"""
        cfg = Config({'version': '1.0'}, file=self._f('sd2.toml'))
        result = cfg.setdefault('version', '2.0')
        self.assertEqual(result, '1.0')
        self.assertEqual(cfg.version, '1.0')

    def test_setdefault_nested(self):
        """测试 setdefault 支持点路径。"""
        cfg = Config(file=self._f('sd3.toml'))
        result = cfg.setdefault('app.name', 'MyApp')
        self.assertEqual(result, 'MyApp')

    def test_first_found(self):
        """测试 first 返回第一个存在的值。"""
        cfg = Config({'host': 'localhost', 'server_host': '127.0.0.1'}, file=self._f('first1.toml'))
        result = cfg.first('server_host', 'host')
        self.assertEqual(result, '127.0.0.1')

    def test_first_fallback(self):
        """测试 first 回退到后续键。"""
        cfg = Config({'host': 'localhost'}, file=self._f('first2.toml'))
        result = cfg.first('missing', 'host')
        self.assertEqual(result, 'localhost')

    def test_first_default(self):
        """测试 first 返回默认值。"""
        cfg = Config(file=self._f('first3.toml'))
        result = cfg.first('a', 'b', default='none')
        self.assertEqual(result, 'none')

    def test_first_skip_none(self):
        """测试 first 跳过 None 值。"""
        cfg = Config({'a': None, 'b': 'value'}, file=self._f('first4.toml'))
        result = cfg.first('a', 'b')
        self.assertEqual(result, 'value')

    def test_require_existing(self):
        """测试 require 返回存在的值。"""
        cfg = Config({'db_url': 'sqlite:///db.sqlite'}, file=self._f('req1.toml'))
        result = cfg.require('db_url')
        self.assertEqual(result, 'sqlite:///db.sqlite')

    def test_require_missing(self):
        """测试 require 不存在时抛出异常。"""
        cfg = Config(file=self._f('req2.toml'))
        with self.assertRaises(ConfigValidationError):
            cfg.require('missing_key')

    def test_require_none_value(self):
        """测试 require 值为 None 时抛出异常。"""
        cfg = Config({'key': None}, file=self._f('req3.toml'))
        with self.assertRaises(ConfigValidationError):
            cfg.require('key')

    def test_require_nested(self):
        """测试 require 支持点路径。"""
        cfg = Config({'db': {'host': 'localhost'}}, file=self._f('req4.toml'))
        result = cfg.require('db.host')
        self.assertEqual(result, 'localhost')


# ===========================================================
# 8) 链式操作
# ===========================================================


class ChainOperationTests(TempDirTestCase):
    """链式操作测试。"""

    def test_set_chain(self):
        """测试 set 链式操作。"""
        cfg = Config(file=self._f('chain.toml'))
        result = cfg.set('a', 1).set('b', 2).set('c', 3)
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg.b, 2)
        self.assertEqual(cfg.c, 3)
        self.assertIs(result, cfg)

    def test_merge_chain(self):
        """测试 merge 链式操作。"""
        cfg = Config(file=self._f('merge_chain.toml'))
        result = cfg.merge({'a': 1}).merge({'b': 2}).merge({'c': 3})
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg.b, 2)
        self.assertEqual(cfg.c, 3)
        self.assertIs(result, cfg)

    def test_from_env_chain(self):
        """测试 from_env 链式操作。"""
        os.environ['TEST_CHAIN'] = 'value'
        try:
            cfg = Config(file=self._f('env_chain.toml'))
            result = cfg.from_env(prefix='TEST')
            self.assertIs(result, cfg)
        finally:
            del os.environ['TEST_CHAIN']


# ===========================================================
# 9) 配置合并
# ===========================================================


class MergeTests(TempDirTestCase):
    """配置合并测试。"""

    def test_merge_override(self):
        """测试 override 策略。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('merge1.toml'))
        cfg.merge({'b': 3, 'c': 4}, strategy='override')
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg.b, 3)
        self.assertEqual(cfg.c, 4)

    def test_merge_keep(self):
        """测试 keep 策略。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('merge2.toml'))
        cfg.merge({'b': 3, 'c': 4}, strategy='keep')
        self.assertEqual(cfg.a, 1)
        self.assertEqual(cfg.b, 2)  # 保留原值
        self.assertEqual(cfg.c, 4)

    def test_merge_deep(self):
        """测试 deep 策略。"""
        cfg = Config({'db': {'host': 'localhost', 'port': 3306}}, file=self._f('merge3.toml'))
        cfg.merge({'db': {'user': 'root'}, 'debug': True}, strategy='deep')
        self.assertEqual(cfg.db.host, 'localhost')
        self.assertEqual(cfg.db.port, 3306)
        self.assertEqual(cfg.db.user, 'root')
        self.assertTrue(cfg.debug)

    def test_merge_with_config(self):
        """测试合并 Config 对象。"""
        fn1 = self._f('merge_cfg1.toml')
        fn2 = self._f('merge_cfg2.toml')
        cfg1 = Config({'a': 1}, file=fn1)
        cfg2 = Config({'b': 2}, file=fn2)
        cfg1.merge(cfg2)
        self.assertEqual(cfg1.a, 1)
        self.assertEqual(cfg1.b, 2)

    def test_merge_invalid_strategy(self):
        """测试无效合并策略。"""
        cfg = Config(file=self._f('merge_invalid.toml'))
        with self.assertRaises(ConfigValidationError):
            cfg.merge({'a': 1}, strategy='invalid')


# ===========================================================
# 10) 配置对比
# ===========================================================


class DiffTests(TempDirTestCase):
    """配置对比测试。"""

    def test_diff_added(self):
        """测试检测新增键。"""
        cfg = Config({'a': 1}, file=self._f('diff1.toml'))
        diff = cfg.diff({'a': 1, 'b': 2})
        self.assertEqual(diff['added'], {'b': 2})
        self.assertEqual(diff['removed'], {})
        self.assertEqual(diff['modified'], {})

    def test_diff_removed(self):
        """测试检测删除键。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('diff2.toml'))
        diff = cfg.diff({'a': 1})
        self.assertEqual(diff['added'], {})
        self.assertEqual(diff['removed'], {'b': 2})

    def test_diff_modified(self):
        """测试检测修改键。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('diff3.toml'))
        diff = cfg.diff({'a': 1, 'b': 3})
        self.assertEqual(diff['modified'], {'b': {'old': 2, 'new': 3}})

    def test_diff_nested(self):
        """测试嵌套字典对比。"""
        cfg = Config({'db': {'host': 'localhost'}}, file=self._f('diff4.toml'))
        diff = cfg.diff({'db': {'host': '127.0.0.1', 'port': 3306}})
        self.assertIn('port', diff['added'].get('db', {}))
        self.assertIn('host', diff['modified'].get('db', {}))

    def test_diff_no_changes(self):
        """测试无差异。"""
        cfg = Config({'a': 1}, file=self._f('diff5.toml'))
        diff = cfg.diff({'a': 1})
        self.assertEqual(diff['added'], {})
        self.assertEqual(diff['removed'], {})
        self.assertEqual(diff['modified'], {})

    def test_diff_with_config(self):
        """测试与 Config 对象对比。"""
        fn1 = self._f('diff_cfg1.toml')
        fn2 = self._f('diff_cfg2.toml')
        cfg1 = Config({'a': 1}, file=fn1)
        cfg2 = Config({'a': 2}, file=fn2)
        diff = cfg1.diff(cfg2)
        self.assertEqual(diff['modified'], {'a': {'old': 1, 'new': 2}})


# ===========================================================
# 11) 环境变量导入导出
# ===========================================================


class EnvTests(TempDirTestCase):
    """环境变量导入导出测试。"""

    def test_to_env_flat(self):
        """测试展平配置为环境变量。"""
        cfg = Config({'host': 'localhost', 'port': 3306}, file=self._f('env1.toml'))
        env = cfg.to_env()
        self.assertEqual(env['HOST'], 'localhost')
        self.assertEqual(env['PORT'], '3306')

    def test_to_env_nested(self):
        """测试嵌套配置导出。"""
        cfg = Config({'db': {'host': 'localhost'}}, file=self._f('env2.toml'))
        env = cfg.to_env()
        self.assertEqual(env['DB_HOST'], 'localhost')

    def test_to_env_prefix(self):
        """测试带前缀导出。"""
        cfg = Config({'host': 'localhost'}, file=self._f('env3.toml'))
        env = cfg.to_env(prefix='APP')
        self.assertEqual(env['APP_HOST'], 'localhost')

    def test_to_env_lowercase(self):
        """测试小写导出。"""
        cfg = Config({'host': 'localhost'}, file=self._f('env4.toml'))
        env = cfg.to_env(uppercase=False)
        self.assertEqual(env['host'], 'localhost')

    def test_from_env(self):
        """测试从环境变量导入。"""
        os.environ['TEST_HOST'] = 'localhost'
        os.environ['TEST_PORT'] = '3306'
        try:
            cfg = Config(file=self._f('env5.toml'))
            cfg.from_env(prefix='TEST')
            self.assertEqual(cfg.host, 'localhost')
            self.assertEqual(cfg.port, '3306')
        finally:
            del os.environ['TEST_HOST']
            del os.environ['TEST_PORT']


# ===========================================================
# 12) 运算符支持
# ===========================================================


class OperatorTests(TempDirTestCase):
    """运算符支持测试。"""

    def test_or_operator(self):
        """测试 | 运算符。"""
        node1 = ConfigNode({'a': 1, 'b': 2})
        node2 = ConfigNode({'b': 3, 'c': 4})
        result = node1 | node2
        self.assertEqual(result, {'a': 1, 'b': 3, 'c': 4})

    def test_or_operator_with_dict(self):
        """测试 | 运算符与 dict。"""
        node = ConfigNode({'a': 1})
        result = node | {'b': 2}
        self.assertEqual(result, {'a': 1, 'b': 2})

    def test_ror_operator(self):
        """测试 | 运算符（左侧为 dict）。"""
        node = ConfigNode({'b': 2})
        result = {'a': 1} | node
        self.assertEqual(result, {'a': 1, 'b': 2})

    def test_ior_operator(self):
        """测试 |= 运算符。"""
        node1 = ConfigNode({'a': 1, 'b': 2})
        node2 = ConfigNode({'b': 3, 'c': 4})
        node1 |= node2
        self.assertEqual(node1._data, {'a': 1, 'b': 3, 'c': 4})

    def test_ior_operator_with_dict(self):
        """测试 |= 运算符与 dict。"""
        node = ConfigNode({'a': 1})
        node |= {'b': 2}
        self.assertEqual(node._data, {'a': 1, 'b': 2})


# ===========================================================
# 13) 高级特性
# ===========================================================


class AdvancedFeatureTests(TempDirTestCase):
    """高级特性测试。"""

    def test_reserved_keywords(self):
        """测试保留关键字保护。"""
        cfg = Config(file=self._f('reserved.toml'))
        with self.assertRaises(ConfigValidationError):
            cfg.to_dict = 'bad'

    def test_opt_property(self):
        """测试 opt 安全访问接口。"""
        cfg = Config({'save': True, 'path': '/tmp'}, file=self._f('opt.toml'))
        self.assertTrue(cfg.opt.save)
        self.assertEqual(cfg.opt.path, '/tmp')

    def test_call_syntax(self):
        """测试调用语法。"""
        cfg = Config({'a': 1}, file=self._f('call.toml'))
        self.assertEqual(cfg('a'), 1)
        self.assertEqual(cfg('missing', 'default'), 'default')

    def test_contains(self):
        """测试包含判断。"""
        cfg = Config({'a': {'b': 1}}, file=self._f('contains.toml'))
        self.assertTrue('a' in cfg)
        self.assertTrue('a.b' in cfg)
        self.assertFalse('missing' in cfg)

    def test_len(self):
        """测试长度。"""
        cfg = Config({'a': 1, 'b': 2, 'c': 3}, file=self._f('len.toml'))
        self.assertEqual(len(cfg), 3)

    def test_iter(self):
        """测试迭代。"""
        cfg = Config({'a': 1, 'b': 2}, file=self._f('iter.toml'))
        keys = list(cfg)
        self.assertIn('a', keys)
        self.assertIn('b', keys)

    def test_bool(self):
        """测试布尔值。"""
        cfg1 = Config(file=self._f('bool1.toml'))
        cfg2 = Config({'a': 1}, file=self._f('bool2.toml'))
        self.assertFalse(bool(cfg1))
        self.assertTrue(bool(cfg2))

    def test_str_repr(self):
        """测试字符串表示。"""
        cfg = Config({'a': 1}, file=self._f('str.toml'))
        self.assertIn('a', str(cfg))

    def test_to_dict(self):
        """测试导出为字典。"""
        cfg = Config({'a': {'b': 1}}, file=self._f('todict.toml'))
        d = cfg.to_dict()
        self.assertEqual(d, {'a': {'b': 1}})
        self.assertIsInstance(d, dict)

    def test_to_json(self):
        """测试导出为 JSON。"""
        cfg = Config({'a': 1}, file=self._f('tojson.toml'))
        j = cfg.to_json()
        self.assertIn('"a": 1', j)

    def test_path(self):
        """测试路径获取。"""
        fn = self._f('path.toml')
        cfg = Config(file=fn)
        self.assertIn('path.toml', cfg.path())
        self.assertTrue(os.path.isabs(cfg.path_abs()))

    def test_auto_save_toggle(self):
        """测试自动保存切换。"""
        cfg = Config(file=self._f('toggle.toml'))
        self.assertTrue(cfg.is_auto_save())
        cfg.set_auto_save(False)
        self.assertFalse(cfg.is_auto_save())


# ===========================================================
# 14) ConfigNode 测试
# ===========================================================


class ConfigNodeTests(TempDirTestCase):
    """ConfigNode 测试。"""

    def test_node_creation(self):
        """测试节点创建。"""
        node = ConfigNode({'a': 1})
        self.assertEqual(node['a'], 1)

    def test_node_attribute_access(self):
        """测试节点属性访问。"""
        node = ConfigNode({'key': 'value'})
        self.assertEqual(node.key, 'value')

    def test_node_setitem(self):
        """测试节点设置值。"""
        node = ConfigNode({})
        node['key'] = 'value'
        self.assertEqual(node['key'], 'value')

    def test_node_delitem(self):
        """测试节点删除值。"""
        node = ConfigNode({'key': 'value'})
        del node['key']
        self.assertNotIn('key', node)

    def test_node_len(self):
        """测试节点长度。"""
        node = ConfigNode({'a': 1, 'b': 2})
        self.assertEqual(len(node), 2)

    def test_node_iter(self):
        """测试节点迭代。"""
        node = ConfigNode({'a': 1, 'b': 2})
        keys = list(node)
        self.assertIn('a', keys)
        self.assertIn('b', keys)

    def test_node_contains(self):
        """测试节点包含判断。"""
        node = ConfigNode({'key': 'value'})
        self.assertTrue('key' in node)
        self.assertFalse('missing' in node)

    def test_node_dict_property(self):
        """测试节点 dict 属性。"""
        node = ConfigNode({'a': 1})
        d = node.dict
        self.assertEqual(d, {'a': 1})
        self.assertIsInstance(d, dict)

    def test_node_reserved_keywords(self):
        """测试节点保留关键字。"""
        node = ConfigNode({})
        with self.assertRaises(AttributeError):
            node.has_top_level_key = 'bad'


# ===========================================================
# 15) 多环境切换
# ===========================================================


class EnvSwitchTests(TempDirTestCase):
    """多环境切换测试。"""

    def test_env_config_loading(self):
        """测试环境配置文件加载。"""
        # 创建基础配置
        base_file = self._f('app.toml')
        Config({'app': {'name': 'base', 'debug': False}}, file=base_file)
        
        # 创建环境配置
        env_file = self._f('app.production.toml')
        Config({'app': {'name': 'production', 'debug': False}}, file=env_file)
        
        # 使用 env 参数加载
        cfg = Config(file=base_file, env='production')
        self.assertEqual(cfg.app.name, 'production')
        self.assertEqual(cfg.app.debug, False)

    def test_env_config_override(self):
        """测试环境配置覆盖基础配置。"""
        # 创建基础配置
        base_file = self._f('app2.toml')
        Config({'db_host': 'localhost', 'db_port': 3306}, file=base_file)
        
        # 创建环境配置（只覆盖部分）
        env_file = self._f('app2.dev.toml')
        Config({'db_host': '127.0.0.1'}, file=env_file)
        
        # 使用 env 参数加载
        cfg = Config(file=base_file, env='dev')
        self.assertEqual(cfg.db_host, '127.0.0.1')  # 被覆盖
        self.assertEqual(cfg.db_port, 3306)  # 保留基础值

    def test_env_config_not_found(self):
        """测试环境配置文件不存在时的行为。"""
        base_file = self._f('app3.toml')
        Config({'app': {'name': 'base'}}, file=base_file)
        
        # 不存在的环境配置文件
        cfg = Config(file=base_file, env='nonexistent')
        self.assertEqual(cfg.app.name, 'base')  # 保持基础配置

    def test_env_prefix(self):
        """测试环境变量前缀导入。"""
        import os
        base_file = self._f('app4.toml')
        Config({'app_name': 'base'}, file=base_file)
        
        # 设置环境变量
        os.environ['TEST_APP_NAME'] = 'from_env'
        os.environ['TEST_APP_DEBUG'] = 'true'
        
        try:
            cfg = Config(file=base_file, env_prefix='TEST_')
            self.assertEqual(cfg.app_name, 'from_env')
            self.assertEqual(cfg.app_debug, 'true')
        finally:
            # 清理环境变量
            del os.environ['TEST_APP_NAME']
            del os.environ['TEST_APP_DEBUG']

    def test_env_and_prefix_combined(self):
        """测试环境配置和环境变量组合使用。"""
        import os
        # 创建基础配置
        base_file = self._f('app5.toml')
        Config({'app_name': 'base', 'app_env': 'base'}, file=base_file)
        
        # 创建环境配置
        env_file = self._f('app5.staging.toml')
        Config({'app_name': 'staging'}, file=env_file)
        
        # 设置环境变量
        os.environ['MYAPP_APP_NAME'] = 'override'
        
        try:
            # 同时使用 env 和 env_prefix
            cfg = Config(file=base_file, env='staging', env_prefix='MYAPP_')
            self.assertEqual(cfg.app_name, 'override')  # 环境变量优先级最高
            self.assertEqual(cfg.app_env, 'base')  # 保留基础值
        finally:
            del os.environ['MYAPP_APP_NAME']

    def test_env_config_encrypted(self):
        """测试加密环境配置文件加载。"""
        pwd = 'test-password'
        # 创建加密的基础配置
        base_file = self._f('secure.toml')
        Config({'app': {'name': 'base'}}, file=base_file, pwd=pwd)
        
        # 创建加密的环境配置
        env_file = self._f('secure.prod.toml')
        Config({'app': {'name': 'prod'}}, file=env_file, pwd=pwd)
        
        # 加载环境配置
        cfg = Config(file=base_file, env='prod', pwd=pwd)
        self.assertEqual(cfg.app.name, 'prod')


if __name__ == "__main__":
    unittest.main()
