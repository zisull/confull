import unittest
import os
from confull import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        # 初始化测试数据和配置文件
        self.test_file = 'test_config.toml'
        self.initial_data = {'app': {'name': 'TestApp', 'version': '1.0'}}
        self.config = Config(data=self.initial_data, file=self.test_file, way='toml')

    def tearDown(self):
        # 清理测试文件
        # 使用 del_clean() 确保同时清理 .lock 文件
        if os.path.exists(self.test_file):
            try:
                Config(file=self.test_file).del_clean()
            except Exception:
                os.remove(self.test_file)
        # 旧备份文件仍做兜底删除
        backup_file = self.test_file + '.bak'
        if os.path.exists(backup_file):
            os.remove(backup_file)

    def test_read_write(self):
        # 测试读写功能
        self.config.write('database.host', 'localhost', overwrite_mode=True)
        value = self.config.read('database.host')
        self.assertEqual(value, 'localhost')

        # 测试使用属性方式读写
        self.config.database.port = 5432
        self.assertEqual(self.config.database.port, 5432)

        # 测试使用字典方式读写
        self.config['database.user'] = 'admin'
        self.assertEqual(self.config['database.user'], 'admin')

    def test_update(self):
        # 测试批量更新功能
        new_data = {'app': {'name': 'NewTestApp', 'version': '2.0'}, 'new_key': 'new_value'}
        self.config.update(new_data)
        self.assertEqual(self.config.dict['app']['name'], 'NewTestApp')
        self.assertEqual(self.config.dict['new_key'], 'new_value')

    def test_save_load(self):
        # 测试保存和加载功能
        self.config.save()
        new_config = Config(file=self.test_file, way='toml')
        self.assertEqual(new_config.dict, self.config.dict)

    def test_del_key(self):
        # 测试删除配置项功能
        self.config.del_key('app.name')
        self.assertNotIn('name', self.config.dict['app'])

    def test_del_clean(self):
        # 测试清空配置并删除文件功能
        self.config.del_clean()
        self.assertEqual(self.config.dict, {})
        self.assertFalse(os.path.exists(self.test_file))

    def test_overwrite_mode(self):
        # 测试强制覆写模式
        self.config.write('app.name', 'OriginalName', overwrite_mode=True)
        with self.assertRaises(ValueError):
            self.config.write('app.name', 'NewName', overwrite_mode=False)
        self.config.write('app.name', 'NewName', overwrite_mode=True)
        self.assertEqual(self.config.dict['app']['name'], 'NewName')

    def test_context_manager(self):
        # 测试上下文管理器
        with Config(data={'example': 'value'}, file='context_test.toml', way='toml') as config:
            config.write('example', 'new_value', overwrite_mode=True)
        new_config = Config(file='context_test.toml', way='toml')
        self.assertEqual(new_config.dict['example'], 'new_value')
        if os.path.exists('context_test.toml'):
            os.remove('context_test.toml')


if __name__ == '__main__':
    unittest.main()