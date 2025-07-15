# -*- coding: utf-8 -*-
"""confull 全量测试套件（精简版）

此文件聚合了对 `confull.Config` 的 **全部功能** 覆盖性单元测试，
基于 `unittest` 框架实现，文件结构清晰、无重复，且所有临时数据均
被写入独立的临时目录，测试结束后自动清理，不会在仓库留下垃圾文件。

测试分组一览：
1. 基础读写与更新          – `BasicBehaviourTests`
2. 文件持久化 & 去抖保存     – `PersistenceTests`
3. 删除操作                – `DeleteOperationTests`
4. 多格式 / 加密            – `FormatEncryptionTests`
5. 进程安全相关            – `ProcessSafeTests`
6. Watchdog 文件监听        – `WatchdogTests`（watchdog 缺失时自动跳过）
7. 高级特性与魔法方法        – `AdvancedFeatureTests`

如需新增功能，只需在对应分组类中补充测试方法即可。
"""
# -------------------- 公共依赖 --------------------
import gc
import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from confull import Config

# watchdog 是可选依赖，若未安装则相关测试自动跳过
try:
    from watchdog.observers import Observer  # type: ignore

    WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover
    WATCHDOG_AVAILABLE = False

# -------------------- 基础类：临时目录 --------------------


class TempDirTestCase(unittest.TestCase):
    """为所有测试提供隔离的临时工作目录。

    setUp 流程：
    1. 记录当前工作目录 → ``_old_cwd``
    2. 创建 ``tempfile.mkdtemp()`` 目录 → ``_tmp_dir``
    3. ``os.chdir`` 进入该目录，保证后续相对路径写文件均位于临时目录

    tearDown 流程：
    1. 终止后台监听线程，避免资源泄露
    2. ``gc.collect()`` 触发析构，从而让 `Config.__del__` 在临时目录内执行
    3. 删除临时目录并恢复 cwd
    """

    # ---------- 生命周期 ----------
    def setUp(self):  # noqa: D401 – 中文注释覆盖英文化要求
        self._old_cwd = os.getcwd()
        self._tmp_dir = tempfile.mkdtemp()
        os.chdir(self._tmp_dir)
        self._created_files: list[str] = []

    def tearDown(self):  # noqa: D401
        # 1) 终止后台监听线程，避免资源泄露
        for th in threading.enumerate():
            if th.name.startswith("DirWatcher") and hasattr(th, "stop"):
                th.stop()  # type: ignore[attr-defined]
                th.join(timeout=0.2)

        # 2) 回收垃圾，触发 Config 自动保存
        gc.collect()

        # 3) 删除临时目录并恢复 cwd
        os.chdir(self._old_cwd)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._created_files.clear()

    # ---------- 工具 ----------
    def _f(self, name: str) -> str:
        """生成位于临时目录的绝对路径，并记录以便调试。"""
        path = os.path.join(self._tmp_dir, name)
        self._created_files.append(path)
        return path

# ===========================================================
# 1) 基础读写与更新
# ===========================================================


class BasicBehaviourTests(TempDirTestCase):
    """基础增删改查相关测试。"""

    def test_multi_interface_rw(self):
        """通过 set / 属性 / 下标 三种方式读写，应返回一致结果。"""
        cfg = Config({"db": {"host": "localhost"}}, file=self._f("basic.toml"))
        # set/get
        cfg.set("db.port", 3306)
        self.assertEqual(cfg.get("db.port"), 3306)
        # 属性
        cfg.db.user = "root"
        self.assertEqual(cfg.db.user, "root")
        # 下标
        cfg["db.password"] = "secret"
        self.assertEqual(cfg["db.password"], "secret")

    def test_update_batch(self):
        cfg = Config({"app": {"name": "demo"}})
        cfg.update({"app": {"name": "new"}, "debug": True})
        self.assertEqual(cfg.app.name, "new")
        self.assertTrue(cfg.debug)

    def test_leaf_overwrite(self):
        cfg = Config()
        cfg.set("value", 1)
        cfg.set("value", 2)  # 不需要 overwrite_mode
        self.assertEqual(cfg.value, 2)

    def test_overwrite_mode_conflict(self):
        cfg = Config()
        # 叶子 → 节点
        cfg.set("x", 1)
        with self.assertRaises(KeyError):
            cfg.set("x.y", 2)
        cfg.set("x.y", 2, overwrite_mode=True)
        # 节点 → 叶子
        with self.assertRaises(ValueError):
            cfg.set("x", 99)
        cfg.set("x", 99, overwrite_mode=True)
        self.assertEqual(cfg.x, 99)

# ===========================================================
# 2) 文件持久化 & 去抖保存
# ===========================================================


class PersistenceTests(TempDirTestCase):
    """保存 / 加载 / 格式转换 / 去抖相关测试。"""

    def test_save_and_load(self):
        fn = self._f("save_load.toml")
        Config({"k": "v"}, file=fn).save()
        self.assertEqual(Config(file=fn).k, "v")

    def test_to_file_conversion(self):
        toml_path = self._f("a.toml")
        json_path = self._f("a.json")
        Config({"x": 1}, file=toml_path).to_file(json_path, way="json")
        self.assertEqual(Config(file=json_path, way="json").x, 1)

    def test_auto_save_debounce(self):
        fn = self._f("debounce.toml")
        cfg = Config({}, file=fn, debounce_ms=50)  # 50ms 去抖
        cfg.msg = "hi"
        time.sleep(0.1)  # > 50ms
        self.assertEqual(Config(file=fn).msg, "hi")

    def test_context_manager_autosave(self):
        fn = self._f("ctx.toml")
        with Config(file=fn, auto_save=False) as c:
            c.token = 123
        self.assertEqual(Config(file=fn).token, 123)

# ===========================================================
# 3) 删除操作
# ===========================================================


class DeleteOperationTests(TempDirTestCase):
    """键删除与文件清理相关测试。"""

    def test_del_key_cleanup(self):
        cfg = Config({"a": {"b": {"c": 1}}, "d": 2})
        cfg.del_key("a.b.c")
        self.assertNotIn("a", cfg.to_dict())
        self.assertEqual(cfg.d, 2)

    def test_del_clean_file_and_memory(self):
        fn = self._f("del.toml")
        c = Config({"x": 1}, file=fn)
        c.del_clean()
        self.assertFalse(os.path.exists(fn))
        self.assertEqual(len(c), 0)

    def test_del_clean_in_memory(self):
        cfg = Config({"p": 9})
        cfg.del_clean()
        self.assertEqual(cfg.to_dict(), {})

# ===========================================================
# 4) 多格式 & 加密
# ===========================================================


class FormatEncryptionTests(TempDirTestCase):
    """多格式读写与 Fernet 加密测试。"""

    def test_initialization_formats(self):
        for ext in ["toml", "json", "yaml", "ini", "xml"]:
            fn = self._f(f"file.{ext}")
            cfg = Config({"sec": {"k": "v"}}, file=fn, way=ext, replace=True)
            self.assertEqual(Config(file=fn, way=ext).sec.k, "v")
            cfg.del_clean()

    def test_encryption_workflow(self):
        fn = self._f("secure.toml")
        pwd = "pwd"
        Config({"s": "1"}, file=fn, pwd=pwd).save()
        self.assertEqual(Config(file=fn, pwd=pwd).s, "1")
        with self.assertRaises(Exception):
            Config(file=fn, pwd="bad")

    def test_decryption_tampered(self):
        fn = self._f("tampered.toml")
        pwd = "p"
        Config({"x": "y"}, file=fn, pwd=pwd).save()
        # 篡改部分字节
        with open(fn, "rb+") as f:
            data = bytearray(f.read())
            data[30:40] = b"0" * 10
            f.seek(0)
            f.write(data)
        with self.assertRaises(ValueError):
            Config(file=fn, pwd=pwd)

# ===========================================================
# 5) 进程安全相关
# ===========================================================


class ProcessSafeTests(TempDirTestCase):
    """跨进程安全及临时文件清理。"""

    def test_process_safe_flag(self):
        fn = self._f("proc.toml")
        cfg1 = Config({"v": 1}, file=fn)
        cfg2 = Config(file=fn, process_safe=False)  # 关闭锁
        cfg2.v = 2
        cfg2.save()
        cfg1.reload()
        self.assertEqual(cfg1.v, 2)

    def test_transactional_save_tmp_cleanup(self):
        fn = self._f("txn.toml")
        cfg = Config({"x": 1}, file=fn)
        cfg.save()
        self.assertFalse(os.path.exists(fn + ".tmp"))

    def test_default_no_lock_file(self):
        fn = self._f("nolock.toml")
        Config({"x": 1}, file=fn).save()
        self.assertFalse(os.path.exists(fn + ".lock"))

# ===========================================================
# 6) Watchdog 文件监听
# ===========================================================


class WatchdogTests(TempDirTestCase):
    """需要 watchdog 才运行的文件监控测试。"""

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog 未安装")
    def test_file_watcher_reload(self):
        fn = self._f("watch.toml")
        Path(fn).write_text("ver = 1")
        cfg = Config(file=fn)
        cfg.enable_watch()
        try:
            Path(fn).write_text("ver = 2")
            # 轮询等待 ≤5 秒
            for _ in range(10):
                time.sleep(0.5)
                if cfg.ver == 2:
                    break
            self.assertEqual(cfg.ver, 2)
        finally:
            cfg.disable_watch()

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog 未安装")
    def test_watchdog_thread_naming(self):
        fn = self._f("th.toml")
        cfg = Config(file=fn)
        cfg.enable_watch()
        try:
            time.sleep(0.1)
            self.assertTrue(any(th.name.startswith("DirWatcher-") for th in threading.enumerate()))
        finally:
            cfg.disable_watch()

# ===========================================================
# 7) 高级特性与保留关键字
# ===========================================================


class AdvancedFeatureTests(TempDirTestCase):
    """保留关键字保护 / 魔法方法整合等。"""

    def test_reserved_keywords_block(self):
        cfg = Config()
        with self.assertRaises(AttributeError):
            cfg.to_dict = "bad"  # type: ignore[attr-defined]

    def test_write_conflicts(self):
        cfg = Config()
        # 标量 → 节点
        cfg.set("u", "leaf")
        with self.assertRaises(KeyError):
            cfg.set("u.k", 1)
        cfg.set("u.k", 1, overwrite_mode=True)
        # 节点 → 标量
        with self.assertRaises(ValueError):
            cfg.set("u", 999)
        cfg.set("u", 999, overwrite_mode=True)
        self.assertEqual(cfg.u, 999)

    def test_dunder_methods(self):
        cfg = Config({"a": 1, "b": {"c": 2}})
        self.assertTrue("a" in cfg and "b.c" in cfg and "x" not in cfg)
        self.assertEqual(len(cfg), 2)
        self.assertEqual(cfg("b.c"), 2)


# 直接运行文件时执行全部测试
if __name__ == "__main__":
    unittest.main() 