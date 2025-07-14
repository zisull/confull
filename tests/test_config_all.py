# -*- coding: utf-8 -*-
"""confull 全量测试套件（整合 test_config_01 / 02 / 03）

测试函数目录：
1. 基础读写与更新
   - test_read_write               : 多接口读写一致性
   - test_update                   : 批量更新嵌套字典
   - test_leaf_overwrite           : 同叶子键覆盖
   - test_overwrite_mode_conflict  : 节点⇄叶子路径冲突处理
2. 文件持久化
   - test_save_load                : save() + 重新实例化
   - test_save_to_file             : 另存为不同格式
   - test_autosave                 : 自动保存即时落盘
   - test_context_manager          : with 语句自动保存
3. 删除操作
   - test_del_key_cleanup          : del_key() 自动清理空父节点
   - test_del_clean_file           : del_clean() 删除文件+清空内存
   - test_del_clean_in_memory      : 无文件对象的 del_clean()
4. 多格式与加密
   - test_initialization_formats   : 支持 toml/json/yaml/ini/xml
   - test_encryption_workflow      : 加密/解密与密码校验
   - test_decryption_tampered      : 篡改文件后解密失败
5. 高级特性
   - test_reload_external_change   : reload() 放弃内存更改
   - test_reserved_keywords_block  : 保留关键字保护
   - test_write_conflicts          : 叶子→节点、节点→叶子冲突
   - test_dunder_methods           : 魔法方法行为
6. 进程/线程 & Watchdog
   - test_process_safe_flag        : process_safe 切换
   - test_file_watcher             : watchdog 自动重载
   - test_watchdog_thread_naming   : 线程命名
   - test_transactional_save_tmp   : .tmp 自动清理
   - test_default_no_lock_file     : 默认无 .lock 文件

各测试内 docstring 进一步列出“初始数据 / 操作步骤 / 预期结果”。
"""

import os
import threading
import time
import unittest
from pathlib import Path

from confull import Config

# 判断 watchdog 是否可用
after_import = True
try:
    from watchdog.observers import Observer  # type: ignore

    WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover
    WATCHDOG_AVAILABLE = False


class BasicConfigTests(unittest.TestCase):
    """基础增删改查相关测试"""

    def setUp(self):
        self.test_files = []

    def tearDown(self):
        # 清理生成的文件
        for f in self.test_files:
            if os.path.exists(f):
                Config(file=f).del_clean()
        self.test_files.clear()

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------
    def test_read_write(self):
        """多接口读写一致性
        初始数据: {'db': {'host': 'localhost'}}
        步骤: 通过 write()/属性/下标 3 种方式写入并读取。
        预期: 每种方式读取结果一致。"""
        filename = 'basic_rw.toml'
        self.test_files.append(filename)
        cfg = Config({'db': {'host': 'localhost'}}, file=filename, replace=True, auto_save=False)

        # write/read 接口
        cfg.write('db.port', 3306)
        self.assertEqual(cfg.read('db.port'), 3306)

        # 属性接口
        cfg.db.user = 'root'
        self.assertEqual(cfg.db.user, 'root')

        # 下标接口
        cfg['db.password'] = 'secret'
        self.assertEqual(cfg['db.password'], 'secret')

    def test_update(self):
        """批量更新嵌套字典"""
        cfg = Config({'app': {'name': 'demo'}}, auto_save=False)
        cfg.update({'app': {'name': 'new'}, 'debug': True})
        self.assertEqual(cfg.app.name, 'new')
        self.assertTrue(cfg.debug)

    def test_leaf_overwrite(self):
        """同叶子键覆盖无需 overwrite_mode"""
        cfg = Config()
        cfg.write('value', 1)
        cfg.write('value', 2)
        self.assertEqual(cfg.value, 2)

    def test_overwrite_mode_conflict(self):
        """节点⇄叶子冲突需 overwrite_mode"""
        cfg = Config()
        # 叶子 → 节点
        cfg.write('x', 1)
        with self.assertRaises(KeyError):
            cfg.write('x.y', 2)
        cfg.write('x.y', 2, overwrite_mode=True)
        self.assertEqual(cfg.x.y, 2)
        # 节点 → 叶子
        cfg.write('z.k', 3)
        with self.assertRaises(ValueError):
            cfg.write('z', 99)
        cfg.write('z', 99, overwrite_mode=True)
        self.assertEqual(cfg.z, 99)

    # ------------------------------------------------------------------
    # 文件持久化
    # ------------------------------------------------------------------
    def test_save_load(self):
        """save() 后重新实例化应一致"""
        filename = 'save_load.toml'
        self.test_files.append(filename)
        cfg = Config({'a': 1}, file=filename, replace=True)
        cfg.save()
        new_cfg = Config(file=filename)
        self.assertEqual(new_cfg.a, 1)

    def test_save_to_file(self):
        """另存为不同格式并保持数据一致"""
        file1, file2 = 'save_as_1.toml', 'save_as_2.json'
        self.test_files += [file1, file2]
        cfg = Config({'k': 'v'}, file=file1, replace=True)
        cfg.save_to_file(file2, way='json')
        self.assertEqual(Config(file=file2, way='json').k, 'v')

    def test_autosave(self):
        """auto_save=True 时即时落盘"""
        filename = 'autosave.json'
        self.test_files.append(filename)
        cfg = Config({}, file=filename, auto_save=True, replace=True)
        cfg.msg = 'hi'
        time.sleep(0.05)
        self.assertEqual(Config(file=filename).msg, 'hi')

    def test_context_manager(self):
        """with 语句退出时自动保存"""
        filename = 'ctx.toml'
        self.test_files.append(filename)
        with Config(file=filename, auto_save=False) as cfg:
            cfg.token = 123
        self.assertEqual(Config(file=filename).token, 123)

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------
    def test_del_key_cleanup(self):
        """del_key() 自动清理空父节点"""
        cfg = Config({'a': {'b': {'c': 1}}, 'd': 2})
        cfg.del_key('a.b.c')
        self.assertNotIn('a', cfg.to_dict())
        self.assertEqual(cfg.d, 2)

    def test_del_clean_file(self):
        """del_clean() 删除文件并清空内存"""
        filename = 'del_file.toml'
        self.test_files.append(filename)
        cfg = Config({'x': 1}, file=filename, replace=True)
        cfg.del_clean()
        self.assertFalse(os.path.exists(filename))
        self.assertEqual(len(cfg), 0)

    def test_del_clean_in_memory(self):
        """无文件对象的 del_clean()"""
        cfg = Config({'p': 9})
        cfg.del_clean()
        self.assertEqual(cfg.to_dict(), {})


class FormatEncryptionTests(unittest.TestCase):
    """多格式 & 加密相关测试"""

    def test_initialization_formats(self):
        """五种格式读写一致"""
        formats = ['toml', 'json', 'yaml', 'ini', 'xml']
        for fmt in formats:
            file = f'init.{fmt}'
            cfg = Config({'sec': {'k': 'v'}}, file=file, way=fmt, replace=True)
            self.assertEqual(Config(file=file, way=fmt).sec.k, 'v')
            cfg.del_clean()

    def test_encryption_workflow(self):
        """正确密码解密 / 错误密码失败"""
        file, pwd = 'secure.toml', 'pwd'
        cfg = Config({'s': '1'}, file=file, pwd=pwd, replace=True)
        cfg.save()
        self.assertEqual(Config(file=file, pwd=pwd).s, '1')
        with self.assertRaises(Exception):
            Config(file=file, pwd='bad')
        if os.path.exists(file):
            os.remove(file)

    def test_decryption_tampered(self):
        """篡改加密文件后应解密失败"""
        file, pwd = 'tampered.toml', 'p'
        cfg = Config({'x': 'y'}, file=file, pwd=pwd, replace=True)
        cfg.save()
        # 篡改文件内容
        with open(file, 'rb+') as f:
            data = bytearray(f.read())
            data[30:40] = b'0' * 10
            f.seek(0)
            f.write(data)
        with self.assertRaises(ValueError):
            Config(file=file, pwd=pwd)
        if os.path.exists(file):
            os.remove(file)


class AdvancedFeatureTests(unittest.TestCase):
    """高级特性 / 并发 / watchdog"""

    def setUp(self):
        self.tmp_files = []

    def tearDown(self):
        # 停止可能残留的 watchdog 线程
        for th in threading.enumerate():
            if th.name.startswith('DirWatcher') and hasattr(th, 'stop'):
                th.stop()  # type: ignore[attr-defined]
                th.join(timeout=0.2)
        for f in self.tmp_files:
            if os.path.exists(f):
                Config(file=f).del_clean()
        self.tmp_files.clear()

    def test_reload_external_change(self):
        """reload() 应读取磁盘最新内容"""
        file = 'reload.toml'
        self.tmp_files.append(file)
        cfg = Config({'v': 1}, file=file, replace=True)
        with open(file, 'w', encoding='utf-8') as f:
            f.write('v = 2')
        cfg.reload()
        self.assertEqual(cfg.v, 2)

    def test_reserved_keywords_block(self):
        """写入保留关键字应被阻止"""
        cfg = Config()
        with self.assertRaises(AttributeError):
            cfg.to_dict = 'bad'  # type: ignore[attr-defined]

    def test_write_conflicts(self):
        """节点/叶子冲突检测"""
        cfg = Config()
        # 标量 → 节点：应先报错，再覆盖成功
        cfg.write('u', 'leaf')
        with self.assertRaises(KeyError):
            cfg.write('u.k', 1)
        cfg.write('u.k', 1, overwrite_mode=True)
        self.assertEqual(cfg.u.k, 1)

        # 节点 → 标量：应先报错，再覆盖成功
        with self.assertRaises(ValueError):
            cfg.write('u', 999)
        cfg.write('u', 999, overwrite_mode=True)
        self.assertEqual(cfg.u, 999)

    def test_dunder_methods(self):
        """魔法方法综合校验"""
        cfg = Config({'a': 1, 'b': {'c': 2}})
        self.assertTrue('a' in cfg and 'b.c' in cfg and 'x' not in cfg)
        self.assertEqual(len(cfg), 2)
        self.assertEqual(cfg('b.c'), 2)

    def test_process_safe_flag(self):
        """process_safe 切换"""
        file = 'proc.toml'
        self.tmp_files.append(file)
        cfg1 = Config({'v': 1}, file=file)
        cfg2 = Config(file=file, process_safe=False)
        cfg2.v = 2
        cfg2.save()
        cfg1.reload()
        self.assertEqual(cfg1.v, 2)

    @unittest.skipUnless(WATCHDOG_AVAILABLE, 'watchdog 未安装')
    def test_file_watcher(self):
        """enable_watch 自动重载"""
        file = 'watch.toml'
        self.tmp_files.append(file)
        Path(file).write_text('ver = 1')
        cfg = Config(file=file)
        cfg.enable_watch()
        time.sleep(0.5)
        Path(file).write_text('ver = 2')
        time.sleep(0.6)
        self.assertEqual(cfg.ver, 2)
        cfg.disable_watch()

    @unittest.skipUnless(WATCHDOG_AVAILABLE, 'watchdog 未安装')
    def test_watchdog_thread_naming(self):
        """后台线程应以 DirWatcher- 前缀命名"""
        file = 'th.toml'
        cfg = Config(file=file)
        cfg.enable_watch()
        time.sleep(0.1)
        self.assertTrue(any(th.name.startswith('DirWatcher-') for th in threading.enumerate()))
        cfg.disable_watch()

    def test_transactional_save_tmp(self):
        """保存成功后应删除 .tmp"""
        file = 'txn.toml'
        self.tmp_files.append(file)
        cfg = Config({'x': 1}, file=file, replace=True)
        cfg.save()
        self.assertFalse(os.path.exists(file + '.tmp'))

    def test_default_no_lock_file(self):
        """process_safe 默认 False 时不应生成 .lock"""
        file = 'nolock.toml'
        self.tmp_files.append(file)
        cfg = Config({'x': 1}, file=file)
        cfg.save()
        self.assertFalse(os.path.exists(file + '.lock'))


if __name__ == '__main__':
    unittest.main()
