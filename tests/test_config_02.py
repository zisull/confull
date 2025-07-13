# -*- coding: utf-8 -*-
import os
import time
from confull.config import Config

# 用于在测试结束时清理所有生成的配置文件
test_files = []

def run_test(test_func):
    """装饰器，用于运行测试函数并捕获结果"""
    def wrapper():
        global test_files
        print(f"--- Running test: {test_func.__name__} ---")
        try:
            # 每个测试都使用自己独立的文件列表
            local_files = test_func()
            if local_files:
                # 确保返回的是列表
                if isinstance(local_files, str):
                    local_files = [local_files]
                test_files.extend(local_files)
            print(f"PASS: {test_func.__name__}")
            return True
        except Exception as e:
            print(f"FAIL: {test_func.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    return wrapper

@run_test
def test_initialization_and_formats():
    """测试不同格式的初始化、创建和加载"""
    formats = ['toml', 'json', 'yaml', 'ini', 'xml']
    files = []
    for fmt in formats:
        filename = f"test_init.{fmt}"
        files.append(filename)
        
        # 1. 使用初始数据创建
        initial_data = {'section': {'key': 'value1'}}
        cfg = Config(initial_data, file=filename, way=fmt, replace=True)
        assert cfg.section.key == 'value1'
        assert os.path.exists(filename)
        
        # 2. 从文件加载
        cfg_load = Config(file=filename, way=fmt)
        assert cfg_load.section.key == 'value1'
        
    return files

@run_test
def test_read_write_methods():
    """测试多种读写方式"""
    filename = "test_read_write.toml"
    initial_data = {'user': {'name': 'Alice', 'age': 30}, 'db': {'host': 'localhost'}}
    cfg = Config(initial_data, file=filename, replace=True, auto_save=False)
    
    # 读取
    assert cfg.read('user.name') == 'Alice'
    assert cfg('user.age') == 30
    assert cfg['user']['name'] == 'Alice'
    assert cfg.user.name == 'Alice'
    
    # 写入
    cfg.write('user.email', 'alice@example.com')
    assert cfg.user.email == 'alice@example.com'
    
    cfg.db.port = 5432
    assert cfg.db.port == 5432
    
    cfg['server'] = {'ip': '127.0.0.1'}
    assert cfg.server.ip == '127.0.0.1'
    
    cfg.save()
    
    # 验证保存
    cfg_load = Config(file=filename)
    assert cfg_load.user.email == 'alice@example.com'
    assert cfg_load.server.ip == '127.0.0.1'
    
    return filename

@run_test
def test_autosave():
    """测试自动保存功能"""
    filename = "test_autosave.json"
    cfg = Config({}, file=filename, auto_save=True, replace=True)
    cfg.feature.enabled = True
    
    # 等待一小段时间确保文件IO完成
    time.sleep(0.1)
    
    cfg_load = Config(file=filename)
    assert cfg_load.feature.enabled is True
    
    return filename

@run_test
def test_delete_methods():
    """测试删除配置项"""
    filename = "test_delete.toml"
    data = {'a': {'b': {'c': 1}}, 'd': 2, 'e': {'f': 3}}
    cfg = Config(data, file=filename, replace=True, auto_save=True)
    
    # 删除深层嵌套的键
    cfg.del_key('a.b.c')
    
    # 验证 a, b, c 都被自动清理
    final_dict_1 = cfg.dict
    assert 'a' not in final_dict_1, "删除'a.b.c'后，'a'应该被清理"
    assert final_dict_1.get('d') == 2, "'d'应该不受影响"

    # 使用 del 语法删除顶层键
    del cfg.e
    
    # 验证 e 被清理
    final_dict_2 = cfg.dict
    assert 'e' not in final_dict_2, "del cfg.e 后，'e'应该被清理"
    
    return filename

@run_test
def test_encryption():
    """测试加密和解密功能"""
    filename = "test_secure.toml"
    password = "my-secret-password"
    data = {'secret': {'key': '12345'}}
    
    # 1. 创建加密文件
    cfg_enc = Config(data, file=filename, pwd=password, replace=True)
    cfg_enc.save()
    
    with open(filename, 'rb') as f:
        content = f.read()
        assert content.startswith(b'ZISULLCONFULLENC')
        
    # 2. 使用正确密码加载
    cfg_dec = Config(file=filename, pwd=password)
    assert cfg_dec.secret.key == '12345'
    
    # 3. 使用错误密码加载 (应失败)
    try:
        Config(file=filename, pwd="wrong-password")
        assert False, "使用错误密码加载时应抛出异常"
    except Exception as e:
        assert "解密失败" in str(e) or "校验失败" in str(e)

    # 4. 无密码加载 (应失败)
    try:
        Config(file=filename)
        assert False, "加载加密文件不提供密码时应抛出异常"
    except Exception as e:
        assert "加密文件" in str(e)

    # 5. 覆盖加密文件但新实例密码错误 (应失败)
    try:
        cfg_overwrite_fail = Config(data, file=filename, pwd="another-wrong-password", replace=False)
        cfg_overwrite_fail.new_data = "test"
        cfg_overwrite_fail.save() # save会触发校验
        assert False, "使用错误密码覆盖加密文件时应失败"
    except Exception as e:
        assert "校验失败" in str(e)
        
    return filename
    
@run_test
def test_reload():
    """测试 reload() 方法"""
    filename = "test_reload.toml"
    cfg = Config({'version': 1}, file=filename, way='toml', replace=True)
    
    # 内存中修改，但不保存
    cfg.version = 2
    assert cfg.version == 2
    
    # 模拟外部进程修改文件 (使用正确的 TOML 格式)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('version = 3')
        
    # 重新加载
    cfg.reload()
    assert cfg.version == 3
    
    return filename

@run_test
def test_del_clean():
    """测试 del_clean() 方法"""
    filename = "test_del_clean.toml"
    Config({'a': 1}, file=filename, replace=True)
    assert os.path.exists(filename)
    
    cfg = Config(file=filename)
    cfg.del_clean()
    
    assert not os.path.exists(filename)
    assert cfg.dict == {}
    
    return None # 文件已被删除

@run_test
def test_save_to_file():
    """测试 save_to_file() 方法"""
    file1 = "test_save_as_1.toml"
    file2 = "test_save_as_2.json"
    
    cfg = Config({'data': 'original'}, file=file1, replace=True)
    cfg.save_to_file(file2, way='json')
    
    assert os.path.exists(file2)
    
    cfg_load = Config(file=file2, way='json')
    
    assert cfg_load.data == 'original'
    
    return [file1, file2]

def cleanup():
    """清理所有测试过程中创建的文件"""
    print("\n--- Cleaning up test files ---")
    cleaned_count = 0
    for f in set(test_files):
        if os.path.exists(f):
            try:
                Config(file=f).del_clean()
            except Exception:
                os.remove(f)
            cleaned_count += 1
            # 额外清理锁文件
            lock_file = f + '.lock'
            if os.path.exists(lock_file):
                os.remove(lock_file)
                cleaned_count += 1
    print(f"Cleanup complete. Removed {cleaned_count} file(s).")


if __name__ == "__main__":
    tests = [
        test_initialization_and_formats,
        test_read_write_methods,
        test_autosave,
        test_delete_methods,
        test_encryption,
        test_reload,
        test_del_clean,
        test_save_to_file
    ]
    
    results = [test() for test in tests]
    
    cleanup()
    
    if all(results):
        print("\n✅ All tests passed!")
    else:
        failed_count = results.count(False)
        print(f"\n❌ {failed_count} test(s) failed.") 