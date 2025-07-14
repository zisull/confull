# -*- coding: utf-8 -*-
"""统一异常定义。

方便外部根据具体错误类型捕获。
"""

class ConfigError(Exception):
    """配置库基类异常"""

class ConfigIOError(ConfigError):
    """文件 I/O 相关错误"""

class ConfigValidationError(ConfigError):
    """解析或数据校验错误"""

class ConfigEncryptionError(ConfigError):
    """加密 / 解密相关错误"""