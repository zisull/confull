from confull import Config

# 写入加密配置
cc = Config(file='secure.toml', way='toml', pwd='123456')
cc.write('token', 'xyz')

# 读取加密配置
cc2 = Config(file='secure.toml', way='toml', pwd='123456')
print(cc2.read('token'))  # 应该输出 xyz

# 用错误密码
cc3 = Config(file='secure.toml', way='toml', pwd='wrong')
print(cc3.read('token'))  # None，并且secure.toml会被备份为secure.toml.old