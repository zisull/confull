from enum import Enum

class Format(str, Enum):
    """Supported configuration file formats."""
    JSON = "json"
    TOML = "toml"
    YAML = "yaml"
    INI = "ini"
    XML = "xml"

    @classmethod
    def list(cls):
        """Return list of supported formats as strings."""
        return [member.value for member in cls]

    @classmethod
    def from_str(cls, value: str) -> "Format":
        """Parse string to Format enum (case-insensitive). Raises ValueError on unknown value."""
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unsupported format: {value}. Supported formats are: {', '.join(cls.list())}"
            ) from exc