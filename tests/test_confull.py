import os
import tempfile
import unittest

from confull.config import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_config.toml")

    def tearDown(self):
        # 清理测试文件
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_basic_config(self):
        """测试基本配置功能"""
        config = Config(file=self.test_file, way="toml")
        config.write("test_key", "test_value")
        self.assertEqual(config.read("test_key"), "test_value")

    def test_encrypted_config(self):
        """测试加密配置功能"""
        # 创建带密码的配置
        config = Config(file=self.test_file, way="toml", pwd="test_password")
        config.write("secret_key", "secret_value")
        config.write("nested.key", "nested_value")
        
        # 验证数据已保存
        self.assertEqual(config.read("secret_key"), "secret_value")
        self.assertEqual(config.read("nested.key"), "nested_value")
        
        # 重新加载配置验证加密解密
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        self.assertEqual(config2.read("secret_key"), "secret_value")
        self.assertEqual(config2.read("nested.key"), "nested_value")

    def test_encrypted_config_wrong_password(self):
        """测试错误密码的情况"""
        # 创建带密码的配置
        config = Config(file=self.test_file, way="toml", pwd="correct_password")
        config.write("secret_key", "secret_value")
        
        # 用错误密码加载配置
        config2 = Config(file=self.test_file, way="toml", pwd="wrong_password")
        # 应该返回空字典或默认值
        self.assertEqual(config2.read("secret_key"), None)

    def test_mixed_encrypted_unencrypted(self):
        """测试加密和非加密配置的兼容性"""
        # 创建不带密码的配置
        config1 = Config(file=self.test_file, way="toml")
        config1.write("public_key", "public_value")
        
        # 用密码重新加载（应该失败或返回空）
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        # 由于文件格式不匹配，应该返回None或空字典
        self.assertEqual(config2.read("public_key"), None)

    def test_encrypted_config_dict_access(self):
        """测试加密配置的字典访问方式"""
        config = Config(file=self.test_file, way="toml", pwd="test_password")
        config["user"] = "admin"
        config["settings.auto_save"] = True
        
        # 验证字典访问
        self.assertEqual(config["user"], "admin")
        self.assertEqual(config["settings.auto_save"], True)
        
        # 重新加载验证
        config2 = Config(file=self.test_file, way="toml", pwd="test_password")
        self.assertEqual(config2["user"], "admin")
        self.assertEqual(config2["settings.auto_save"], True)


if __name__ == "__main__":
    unittest.main()