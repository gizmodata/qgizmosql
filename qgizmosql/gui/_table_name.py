"""Pure-Python helpers for parsing the qualified table name shown in the
add-layer dialog's combo box. Kept free of PyQGIS imports so the parsing
logic is unit-testable in plain Python (see tests/unit/test_table_name.py).
"""
from __future__ import annotations

from typing import Optional, Tuple


def split_qualified_table(name: str) -> Tuple[Optional[str], str, str]:
    """Split a (possibly qualified) table name into ``(catalog, schema, table)``.

    Accepts three input shapes — list_tables emits the first; older callers
    or hand-built URIs may still produce the others:

    * ``catalog.schema.table`` → returns all three.
    * ``schema.table``         → returns ``(None, schema, table)``.
    * ``table``                → returns ``(None, "main", table)``.

    The catalog/schema slots use the *last* segments so a stray dot in a
    catalog or schema name still gets parsed sensibly.
    """
    parts = name.split(".")
    if len(parts) >= 3:
        return parts[-3], parts[-2], parts[-1]
    if len(parts) == 2:
        return None, parts[0], parts[1]
    return None, "main", parts[0]
