# -*- coding: utf-8 -*-
"""统一异常定义。

方便外部根据具体错误类型捕获。
"""


class ConfigError(Exception):
    """配置库基类异常。

    构造时不写日志：是否记录由调用方决定，库本身不应在抛出路径上产生副作用。
    """

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class ConfigIOError(ConfigError):
    """文件 I/O 相关错误"""


class ConfigValidationError(ConfigError):
    """解析或数据校验错误"""


class ConfigEncryptionError(ConfigError):
    """加密 / 解密相关错误"""


class ConfigKeyError(ConfigValidationError, KeyError):
    """配置键或路径不存在。

    同时是 ``KeyError``，以便 ``in``、``get`` 等 Mapping 协议保持标准语义。
    """

    def __init__(self, key, message: str = ""):
        super().__init__(message or f"键 '{key}' 不存在。")
        self.key = key
