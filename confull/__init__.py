"""confull – 多格式配置管理工具"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .config import Config  # noqa: E402
from .formats import Format  # noqa: E402
from .node import ConfigNode  # noqa: E402
from .exceptions import (  # noqa: E402
    ConfigEncryptionError,
    ConfigError,
    ConfigIOError,
    ConfigKeyError,
    ConfigValidationError,
)

# 版本号（若未安装则给默认值）
try:
    __version__ = _pkg_version("confull")
except PackageNotFoundError:
    __version__ = "0.2.0"

# * 导入时可见符号
__all__ = [
    "Config",
    "ConfigNode",
    "Format",
    "__version__",
    "ConfigError",
    "ConfigIOError",
    "ConfigKeyError",
    "ConfigValidationError",
    "ConfigEncryptionError",
]
