"""confull – 多格式配置管理工具"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .config import Config  # noqa: E402
from .formats import Format  # noqa: E402

# 版本号（若未安装则给默认值）
try:
    __version__ = _pkg_version("confull")
except PackageNotFoundError:
    __version__ = "0.0.4"

# * 导入时可见符号
__all__ = ["Config", "Format", "__version__"]
