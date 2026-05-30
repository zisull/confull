# -*- coding: utf-8 -*-
"""统一异常定义。

方便外部根据具体错误类型捕获。
"""

import logging

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """配置库基类异常，会自动写入日志。"""

    def __init__(self, message: str):
        super().__init__(message)
        # 立即记录错误日志，便于统一追踪
        logger.error(message)

class ConfigIOError(ConfigError):
    """文件 I/O 相关错误"""

class ConfigValidationError(ConfigError):
    """解析或数据校验错误"""

class ConfigEncryptionError(ConfigError):
    """加密 / 解密相关错误"""