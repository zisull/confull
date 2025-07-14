from confull import Config
cc = Config()
cc.write('id', 123456)
cc.write('name','紫苏')
cc.write('db.host', '127.0.0.1')
cc.write('db.port',3306 )
print(cc.read('db.host'))  # 127.0.0.1
print(cc.read('db.port'))  # 3306
cc.save_to_file('config.json', 'json')
cc.save_to_file('config.yaml', 'yaml')
cc.save_to_file(file='tests/config.ini', way='ini')
cc.save_to_file(file='tests/config.xml', way='xml')
cc.save_to_file(file='tests/config.yaml', way='yaml')

