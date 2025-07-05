# confull

[Zh](https://github.com/zisull/confull/blob/main/README.md) / [En](https://github.com/zisull/confull/blob/main/doc/README-en.md)

## I. Overview

`confull` is a multi-format configuration management tool that supports read and write operations between `dict` and formats such as `ini`, `xml`, `json`, `toml`, and `yaml`, and can automatically save configurations. It provides a convenient interface to manage configuration data and allows you to switch configuration files and formats as needed.

### Installation

Run the following command in the command line to install `confull`:

```cmd
pip install confull
```

## II. Class and Method Descriptions

### 1. `Config` Class

This class is the core of the configuration manager, responsible for reading, writing, and saving configuration data.

#### Initialization Method `__init__`

```python
def __init__(self, data: dict = None, file: str = "config", way: str = "toml", replace: bool = False,
             auto_save: bool = True, backup: bool = False):
```

- Parameter Explanation:
  - `data`: Initial configuration data, of type `dict`, default is `None`.
  - `file`: Configuration file name (extension can be omitted), default is `"config"`. If the specified directory does not exist, it will be automatically created.
  - `way`: Configuration file format, supports `json`, `toml`, `yaml`, `ini`, `xml`, default is `"toml"`.
  - `replace`: Whether to overwrite the existing configuration file, boolean, default is `False`.
  - `auto_save`: Whether to save automatically, boolean, default is `True`.
  - `backup`: Whether to back up the original configuration file, boolean, default is `False`.

#### Attributes

| Attribute Name  | Description                                                  |
| --------------- | ------------------------------------------------------------ |
| `json`          | Returns the configuration data in JSON string format.        |
| `dict`          | Returns the configuration data in `dict` format, and can also be used to set configuration data in batches. |
| `auto_save`     | Whether to save automatically, a readable and writable attribute. |
| `backup`        | Whether to back up the original configuration file, a readable and writable attribute. |
| `str`           | Returns the configuration data in string format.             |
| `file_path`     | Configuration file path.                                     |
| `file_path_abs` | Absolute path of the configuration file.                     |

#### Methods

| Method Name                                            | Description                                                  |
| ------------------------------------------------------ | ------------------------------------------------------------ |
| `read(key: str, default=None)`                         | Reads a configuration item, supports dot notation paths, such as `a.b.c`. If the configuration item does not exist, returns the default value. |
| `write(key: str, value, overwrite_mode: bool = False)` | Writes a configuration item, supports dot notation paths. If `overwrite_mode` is `True`, it will overwrite when there is a path conflict. After writing, if `auto_save` is `True`, it will save automatically. |
| `del_clean()`                                          | Clears all configurations and deletes the configuration file. |
| `update(data: dict)`                                   | Updates configuration items in batches, supports dot notation paths. After updating, if `auto_save` is `True`, it will save automatically. |
| `set_data(data: dict)`                                 | Completely replaces the configuration data with a `dict`. After replacement, if `auto_save` is `True`, it will save automatically. |
| `del_key(key: str)`                                    | Deletes the specified configuration item, supports dot notation paths. After deletion, if `auto_save` is `True`, it will save automatically. |
| `_load()`                                              | Loads the configuration from the file, an internal method.   |
| `load(file: str = None, way: str = None)`              | Switches the configuration file or format (does not automatically load the content). |
| `mark_dirty()`                                         | Marks the configuration as changed.                          |
| `save()`                                               | Saves the configuration to the file.                         |
| `save_to_file(file: str = None, way: str = None)`      | Saves as a specified file and format.                        |
| `_ensure_file_exists()`                                | Ensures that the configuration file exists, an internal method. |
| `_backup_file()`                                       | Backs up the original configuration file, an internal method. |
| `_recursive_update(original, new_data)`                | Recursively updates the configuration, supports dot notation paths, an internal method. |
| `validate_format(_way)`                                | Validates and returns a legal format name, a static method.  |
| `ensure_extension(file)`                               | Ensures that the file name has the correct extension.        |

#### Magic Methods

| Magic Method Name                           | Description                                                  |
| ------------------------------------------- | ------------------------------------------------------------ |
| `__del__()`                                 | When the object is destroyed, if `auto_save` is `True`, it will automatically save the configuration. |
| `__getattr__(self, item)`                   | Attribute access is proxied to the configuration data.       |
| `__getitem__(self, item)`                   | Accesses the configuration data in `dict` style.             |
| `__call__(self, key, value=None)`           | `cc(key)` is equivalent to `cc.read(key, value)`.            |
| `__len__(self)`                             | Number of configuration items.                               |
| `__iter__(self)`                            | Iterates over the configuration items.                       |
| `__contains__(self, item)`                  | Checks if a configuration item exists.                       |
| `__bool__(self)`                            | Checks if the configuration is non-empty.                    |
| `__enter__(self)`                           | Context manager `enter`.                                     |
| `__exit__(self, exc_type, exc_val, exc_tb)` | Context manager `exit`, saves automatically.                 |
| `__setattr__(self, key, value)`             | Attribute assignment is proxied to the configuration data, internal attributes use the `_` prefix. |
| `__delattr__(self, key)`                    | Attribute deletion is proxied to the configuration data.     |

III. Usage Examples

```python
from confull import Config

# 1. Initialize the configuration manager
# Initialize with default parameters
cc = Config()

# Initialize with custom parameters
initial_data = {'app': {'name': 'MyApp', 'version': '1.0'}}
cc = Config(data=initial_data, file='custom_config', way='json', replace=False, auto_save=True, backup=True)

# 2. Basic read and write operations
# Write a configuration item using dot notation path
cc.write('database.host', 'localhost')

# Read a configuration item using dot notation path
host = cc.read('database.host')
print(f"Database host (using read method): {host}")

# Write a configuration item using attribute access
cc.database.port = 5432
# Read a configuration item using attribute access
port = cc.database.port
print(f"Database port (using attribute access): {port}")

# Write a configuration item using dictionary access
cc['database.user'] = 'admin'
# Read a configuration item using dictionary access
user = cc['database.user']
print(f"Database user (using dict access): {user}")

# 3. Batch update configuration items
new_data = {'app': {'name': 'NewApp', 'version': '2.0'}, 'new_key': 'new_value'}
cc.update(new_data)
print("Updated config:", cc.dict)

# 4. Save and save as a different file
# Save the configuration file
cc.save()

# Save as a specified file and format
cc.save_to_file(file='backup_config', way='yaml')

# 5. Delete configuration items and clear the configuration
# Delete a configuration item
cc.del_key('database.host')
del cc.database.port
del cc['database.user']

# Clear the configuration and delete the file
cc.del_clean()

# 6. Switch configuration file or format
cc.load(file='new_config', way='toml')

# 7. Mark the configuration as changed and save manually
cc.mark_dirty()
cc.save()

# 8. Use the context manager
with Config(data={'example': 'value'}, file='context_config', way='toml') as config:
    config.write('example', 'new_value')
    # Automatically save when leaving the context

# 9. Use the __del__ magic function
temp_config = Config(data={'test': 'data'}, file='del_test', way='json')
# When the temp_config object is destroyed, if auto_save is True, it will automatically save the configuration
del temp_config

# 10. Use the dict attribute to set and get configuration data in batches
cc = Config()
cc.dict = {'location': 'Beijing', 'books': {'quantity': 100, 'price': 10.5}, 'students': {'quantity': 1000, 'age': 20}}
print("Config data using dict property:", cc.dict)

# 11. Use the forced overwrite mode
dic_ = {'school': 'pass'}
cc = Config(data=dic_)
cc.write('school.university', 'University', overwrite_mode=True)  # overwrite_mode=True forces overwrite, but the original path will be deleted
print("Config after forced overwrite:", cc.dict)

# 12. Check if a configuration item exists
print("Does 'school' exist in cc?", 'school' in cc)

# 13. Iterate over configuration items
for key in cc:
    print(f"Key: {key}, Value: {cc[key]}")

# 14. Get the number of configuration items
print("Number of configuration items:", len(cc))

# 15. Use the __call__ method
value = cc('school.university')
print(f"Value of 'school.university' using __call__: {value}")

# 16. Check if the configuration is non-empty
print("Is cc non-empty?", bool(cc))

# 17. Use the pop method to delete and return the value of the specified key
cc = Config(data={'a': 1, 'b': 2})
popped_value = cc.pop('a')
print(f"Popped value: {popped_value}, Remaining config: {cc.dict}")

# 18. Use the clear method to clear the configuration data
cc.clear()
print("Config after clear:", cc.dict)

# 19. Use the get method to safely get a configuration item
default_value = cc.get('non_existent_key', 'default')
print(f"Value of non-existent key using get: {default_value}")
```

## IV. Notes

- When using methods such as `write`, `update`, `set_data`, `del_key` to modify configuration data, if `auto_save` is `True`, the configuration file will be saved automatically.
- If the configuration file format is not supported, a `ValueError` exception will be thrown.
- When using the `INIConfigHandler` to save the configuration, if the data is not a nested dictionary, it will be wrapped in a default `'Default'` section.

## Conclusion

The author's level is limited, and the goal is to simplify the read and write process of configuration files as much as possible, allowing users to operate configuration information in a more intuitive and convenient way.

November 19, 2024 zisull@qq.com