from dataclasses import dataclass


@dataclass
class DdbExtension:
    """Represent a DuckDB extension in listing."""

    name: str
    is_installed: bool
    is_loaded: bool
