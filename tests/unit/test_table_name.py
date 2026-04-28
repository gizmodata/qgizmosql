"""Unit tests for the dialog's qualified-table-name parser.

The parser lives in qgizmosql.gui._table_name (a deliberately PyQGIS-free
module) so we can exercise it without standing up a QGIS environment.
"""
from __future__ import annotations

import os
import sys
import unittest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from qgizmosql.gui._table_name import split_qualified_table  # noqa: E402


class TestSplitQualifiedTable(unittest.TestCase):
    def test_three_part_returns_all_segments(self):
        self.assertEqual(
            split_qualified_table("mycat.public.cities"),
            ("mycat", "public", "cities"),
        )

    def test_two_part_returns_none_catalog(self):
        # Back-compat: pre-catalog list_tables emitted schema.table.
        self.assertEqual(
            split_qualified_table("public.cities"),
            (None, "public", "cities"),
        )

    def test_bare_name_defaults_schema_to_main(self):
        # DuckDB's default schema is "main"; an unqualified name should resolve there.
        self.assertEqual(
            split_qualified_table("cities"),
            (None, "main", "cities"),
        )

    def test_extra_segments_take_last_three(self):
        # Defensive: a catalog or schema with a dot in it would produce >3 segments.
        # The parser keeps the last three so the table identifier is never lost.
        self.assertEqual(
            split_qualified_table("a.b.c.d"),
            ("b", "c", "d"),
        )


if __name__ == "__main__":
    unittest.main()
