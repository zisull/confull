import unittest
import os
import time
import threading
from pathlib import Path

from confull import Config
from confull.node import ConfigNode

# Check if watchdog is available to conditionally run tests
try:
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class TestAdvancedFeatures(unittest.TestCase):
    def setUp(self):
        self.test_files = []

    def tearDown(self):
        # Stop any running observers from previous tests
        for th in threading.enumerate():
            if th.name.startswith("DirWatcher"): # Watchdog thread name
                # This is a bit of a hack, but necessary for cleanup
                if hasattr(th, "stop"):
                    th.stop()
                    th.join(timeout=1)
        
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)
        self.test_files.clear()

    def _create_config(self, filename="test_adv.toml", **kwargs) -> Config:
        path = str(Path("tests") / filename)
        self.test_files.append(path)
        # Ensure directory exists
        Path(path).parent.mkdir(exist_ok=True)
        return Config(file=path, **kwargs)

    def test_reserved_keywords_in_node(self):
        """Test that data keys have precedence over methods."""
        cfg = self._create_config(data={'app': 'test'})
        
        # 1. dict 属性应返回原生字典
        self.assertIsInstance(cfg.dict, dict)
        
        # 2. Assign a value to a key that used to collide with method name
        cfg.to_dict = "shadowed"
        cfg.save() # Ensure it's persisted

        # 3. Now, accessing it should return the data key value
        self.assertEqual(cfg.to_dict, "shadowed")
            
        # 5. Reload and verify the behavior persists
        new_cfg = self._create_config()
        self.assertEqual(new_cfg.to_dict, "shadowed")

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog is not installed")
    def test_file_watcher(self):
        """Test file watcher for auto-reloading."""
        filepath = str(Path("tests") / "watch_test.toml")
        self.test_files.append(filepath)

        # 1. Initial setup
        with open(filepath, "w") as f:
            f.write("version = 1")
        
        cfg = Config(file=filepath)
        self.assertEqual(cfg.version, 1)

        # 2. Enable watching and modify file
        cfg.enable_watch()
        time.sleep(0.2) # Give observer time to start
        
        with open(filepath, "w") as f:
            f.write("version = 2")
            
        time.sleep(0.5) # Give observer time to notice and reload
        
        self.assertEqual(cfg.version, 2, "Config should have reloaded to version 2")
        
        # 3. Disable watching and modify again
        cfg.disable_watch()
        time.sleep(0.2)

        with open(filepath, "w") as f:
            f.write("version = 3")
            
        time.sleep(0.5) # Wait, but no reload should happen
        self.assertEqual(cfg.version, 2, "Config should NOT have reloaded after disabling watch")

    def test_write_conflicts(self):
        """Test write behavior on path conflicts."""
        cfg = self._create_config(data={'user': 'anonymous'})
        
        # 1. Writing a sub-key to a leaf node should fail without overwrite
        with self.assertRaises(KeyError):
            cfg.write("user.name", "test")
            
        # 2. With overwrite, it should replace the leaf with a new dict
        cfg.write("user.name", "admin", overwrite_mode=True)
        self.assertIsInstance(cfg.user, ConfigNode)
        self.assertEqual(cfg.user.name, "admin")
        self.assertIsNone(cfg.dict.get('user', {}).get('')) # Ensure no old value remains

    def test_dunder_methods(self):
        """Test various magic methods."""
        cfg = self._create_config(data={'a': 1, 'b': {'c': 2}})
        
        # __contains__
        self.assertTrue('a' in cfg)
        self.assertTrue('b.c' in cfg)
        self.assertFalse('c' in cfg)
        
        # __len__
        self.assertEqual(len(cfg), 2)
        
        # __bool__
        self.assertTrue(bool(cfg))
        empty_cfg = self._create_config("empty.toml", data={})
        self.assertEqual(empty_cfg.dict, {})
        
        # __call__
        self.assertEqual(cfg('b.c'), 2)
        self.assertEqual(cfg('x', 'default'), 'default')

    def test_decryption_failure_on_tampered_file(self):
        """Test that loading a corrupted encrypted file fails."""
        filepath = str(Path("tests") / "secure_tampered.toml")
        password = "a-secure-password"
        cfg = self._create_config(filename="secure_tampered.toml", data={'secret': 'data'}, pwd=password)
        cfg.save()
        
        # Read the encrypted content and tamper with it
        with open(filepath, "rb") as f:
            content = f.read()
        
        # Corrupt the HMAC part
        tampered_content = content[:20] + b'0' * 10 + content[30:]
        
        with open(filepath, "wb") as f:
            f.write(tampered_content)
            
        # Attempting to load should now fail with a ValueError
        with self.assertRaises(ValueError, msg="HMAC校验失败"):
            Config(file=filepath, pwd=password)
            
    def test_del_clean_on_non_existent_file(self):
        """Test del_clean on a config with no backing file."""
        cfg = Config(data={'a': 1}) # No file provided, so it's in-memory
        cfg.del_clean()
        self.assertEqual(len(cfg), 0)
        self.assertEqual(cfg.dict, {})
        # Should not raise any error

    def test_process_safe_flag(self):
        """Ensure Config works with process_safe toggle."""
        path = str(Path("tests") / "proc_safe.toml")
        self.test_files.append(path)

        # Create config with process_safe=True (default)
        cfg1 = Config(file=path, data={'v': 1})
        self.assertEqual(cfg1.v, 1)

        # Open same file with process_safe=False and modify
        cfg2 = Config(file=path, process_safe=False)
        cfg2.v = 2
        cfg2.save()

        # reload cfg1 to see last writer wins
        cfg1.reload()
        self.assertEqual(cfg1.v, 2)

    # ------------------------------------------------------------------
    # 新增功能测试
    # ------------------------------------------------------------------

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog is not installed")
    def test_transactional_save_cleanup(self):
        """保存应使用临时文件并在完成后清理 .tmp"""
        filename = "transact_test.toml"
        cfg = self._create_config(filename=filename, data={'x': 1})
        cfg.save()

        tmp_path = filename + ".tmp"
        self.assertFalse(os.path.exists(tmp_path), ".tmp 文件应在成功保存后被清理")
        return filename

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog is not installed")
    def test_watchdog_thread_naming(self):
        """enable_watch 后应启动以 DirWatcher- 前缀命名的线程"""
        filename = "watch_thread.toml"
        cfg = self._create_config(filename=filename)
        cfg.enable_watch()
        time.sleep(0.2)

        # 检查是否存在 DirWatcher 线程
        self.assertTrue(any(th.name.startswith("DirWatcher-") for th in threading.enumerate()))

        cfg.disable_watch()
        return filename

    @unittest.skipUnless(WATCHDOG_AVAILABLE, "watchdog is not installed")
    def test_default_no_lock_file(self):
        """process_safe 默认 False，应不生成 .lock 文件"""
        filename = "proc_default.toml"
        cfg = self._create_config(filename=filename, data={'a': 1})
        cfg.save()

        self.assertFalse(os.path.exists(filename + '.lock'), "默认应不生成 .lock 文件")
        return filename


if __name__ == '__main__':
    unittest.main() 