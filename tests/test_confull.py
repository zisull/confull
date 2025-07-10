import os
import tempfile
import unittest
from confull.config import Config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # 每个测试用例都用独立的临时文件
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_file = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        # 测试后只删除本次用到的临时数据文件
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_basic_config(self):
        """测试基本配置功能"""
        config = Config(file=self.test_file, way="toml", replace=True)
        config.write("test_key", "test_value")
        self.assertEqual(config.read("test_key"), "test_value")

    def test_encrypted_config(self):
        """测试加密配置功能"""
        config = Config(file=self.test_file, way="toml", pwd="test_password", replace=True)
        config.write("secret_key", "secret_value")
        config.write("nested.key", "nested_value", overwrite_mode=True)
        self.assertEqual(config.read("secret_key"), "secret_value")
        self.assertEqual(config.read("nested.key"), "nested_value")
        # 重新加载验证
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        self.assertEqual(config2.read("secret_key"), "secret_value")
        self.assertEqual(config2.read("nested.key"), "nested_value")

    def test_encrypted_config_wrong_password(self):
        """测试错误密码的情况"""
        config = Config(file=self.test_file, way="toml", pwd="correct_password", replace=True)
        config.write("secret_key", "secret_value")
        config2 = Config(file=self.test_file, way="toml", pwd="wrong_password")
        self.assertEqual(config2.read("secret_key"), None)

    def test_mixed_encrypted_unencrypted(self):
        """测试加密和非加密配置的兼容性"""
        config1 = Config(file=self.test_file, way="toml", replace=True)
        config1.write("public_key", "public_value")
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        self.assertEqual(config2.read("public_key"), None)

    def test_encrypted_config_dict_access(self):
        """测试加密配置的字典访问方式"""
        config = Config(file=self.test_file, way="toml", pwd="test_password", replace=True)
        config["user"] = "admin"
        config["settings.auto_save"] = True
        self.assertEqual(config["user"], "admin")
        self.assertEqual(config["settings.auto_save"], True)
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        self.assertEqual(config2["user"], "admin")
        self.assertEqual(config2["settings.auto_save"], True)

if __name__ == "__main__":
    unittest.main() 