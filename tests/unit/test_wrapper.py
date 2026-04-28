"""Unit tests for pure-Python bits of gizmosql_wrapper.

These tests avoid importing PyQGIS so they can run under any Python 3.12+
environment in CI (no QGIS install, no Docker). The PlgLogger and Qgis
symbols that the wrapper references at import time are stubbed here.

Integration tests that require a live GizmoSQL server live separately and
are gated on ``GIZMOSQL_INTEGRATION=1``.
"""

from __future__ import annotations

import os
import sys
import unittest

# Bring tests/_stubs.py into scope so we can install minimal qgis + ADBC
# shims (shared with integration tests). Then import the wrapper safely.
_TESTS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

from _stubs import install as _install_stubs  # noqa: E402

_install_stubs()

from qgizmosql.provider.gizmosql_wrapper import (  # noqa: E402
    DEFAULT_GIZMOSQL_PORT,
    GizmoSqlConnConfig,
    GizmoSqlTools,
)


class TestGizmoSqlConnConfig(unittest.TestCase):
    def test_defaults(self):
        c = GizmoSqlConnConfig(host="localhost")
        self.assertEqual(c.port, DEFAULT_GIZMOSQL_PORT)
        self.assertTrue(c.use_tls)
        self.assertEqual(c.auth_type, "password")
        self.assertFalse(c.tls_skip_verify)
        self.assertIsNone(c.authcfg)

    def test_flight_uri_tls(self):
        c = GizmoSqlConnConfig(host="gizmosql.example.com", port=31337, use_tls=True)
        self.assertEqual(c.flight_uri, "grpc+tls://gizmosql.example.com:31337")

    def test_flight_uri_plaintext(self):
        c = GizmoSqlConnConfig(host="internal", port=9999, use_tls=False)
        self.assertEqual(c.flight_uri, "grpc://internal:9999")

    def test_connect_kwargs_password(self):
        c = GizmoSqlConnConfig(
            host="h", username="u", password="p", tls_skip_verify=True
        )
        kw = c.connect_kwargs()
        self.assertEqual(kw["username"], "u")
        self.assertEqual(kw["password"], "p")
        self.assertTrue(kw["tls_skip_verify"])
        self.assertNotIn("auth_type", kw)

    def test_connect_kwargs_external_omits_credentials(self):
        c = GizmoSqlConnConfig(
            host="h", username="u", password="p", auth_type="external"
        )
        kw = c.connect_kwargs()
        self.assertEqual(kw["auth_type"], "external")
        self.assertNotIn("username", kw)
        self.assertNotIn("password", kw)

    def test_repr_masks_password(self):
        c = GizmoSqlConnConfig(host="h", password="secret")
        self.assertNotIn("secret", repr(c))
        self.assertIn("***", repr(c))


class TestParseUri(unittest.TestCase):
    def test_password_uri(self):
        w = GizmoSqlTools()
        uri = (
            "gizmosql://localhost:31337?use_tls=1&tls_skip_verify=1"
            "&auth_type=password&username=u&password=p"
            "&schema=main&table=cities&epsg=4326"
        )
        conf, table, epsg, sql, schema, catalog = w.parse_uri(uri)
        self.assertEqual(conf.host, "localhost")
        self.assertEqual(conf.port, 31337)
        self.assertTrue(conf.use_tls)
        self.assertTrue(conf.tls_skip_verify)
        self.assertEqual(conf.username, "u")
        self.assertEqual(conf.password, "p")
        self.assertEqual(table, "cities")
        self.assertEqual(schema, "main")
        self.assertEqual(epsg, "4326")
        self.assertIsNone(sql)
        self.assertIsNone(catalog)

    def test_authcfg_uri(self):
        w = GizmoSqlTools()
        uri = "gizmosql://h:31337?authcfg=abc1234&table=t"
        conf, table, _, _, _, _ = w.parse_uri(uri)
        self.assertEqual(conf.authcfg, "abc1234")
        self.assertIsNone(conf.username)
        self.assertIsNone(conf.password)
        self.assertEqual(table, "t")

    def test_sql_uri_strips_trailing_semicolon(self):
        w = GizmoSqlTools()
        uri = "gizmosql://h:31337?sql=SELECT+1+FROM+t;"
        _, _, _, sql, _, _ = w.parse_uri(uri)
        self.assertEqual(sql, "SELECT 1 FROM t")

    def test_bad_scheme_rejected(self):
        w = GizmoSqlTools()
        with self.assertRaises(ValueError):
            w.parse_uri("http://localhost:31337?table=t")

    def test_missing_host_rejected(self):
        w = GizmoSqlTools()
        with self.assertRaises(ValueError):
            w.parse_uri("gizmosql://?table=t")

    def test_default_port(self):
        w = GizmoSqlTools()
        conf, _, _, _, _, _ = w.parse_uri("gizmosql://h?table=t")
        self.assertEqual(conf.port, DEFAULT_GIZMOSQL_PORT)

    def test_catalog_round_trips(self):
        """A URI with `catalog=` round-trips through parse_uri unmolested."""
        w = GizmoSqlTools()
        uri = (
            "gizmosql://h:31337?authcfg=abc1234"
            "&catalog=mycat&schema=public&table=cities"
        )
        conf, table, _, _, schema, catalog = w.parse_uri(uri)
        self.assertEqual(conf.authcfg, "abc1234")
        self.assertEqual(catalog, "mycat")
        self.assertEqual(schema, "public")
        self.assertEqual(table, "cities")

    def test_catalog_absent_yields_none(self):
        """No catalog in URI → parse_uri returns None for catalog."""
        w = GizmoSqlTools()
        _, _, _, _, _, catalog = w.parse_uri(
            "gizmosql://h:31337?schema=main&table=t"
        )
        self.assertIsNone(catalog)


class TestBuildUri(unittest.TestCase):
    def test_build_uri_uses_authcfg_and_suppresses_raw_credentials(self):
        conf = GizmoSqlConnConfig(
            host="h", port=31337, username="u", password="p", authcfg="abc1234"
        )
        uri = GizmoSqlTools.build_uri(conf, table="cities", schema="main", epsg="4326")
        self.assertIn("authcfg=abc1234", uri)
        # Raw credentials must never land in a URI once authcfg is set —
        # the URI ends up in saved QGIS project files.
        self.assertNotIn("password=", uri)
        self.assertNotIn("username=", uri)

    def test_build_uri_with_raw_credentials_when_no_authcfg(self):
        conf = GizmoSqlConnConfig(host="h", username="u", password="p")
        uri = GizmoSqlTools.build_uri(conf)
        self.assertIn("username=u", uri)
        self.assertIn("password=p", uri)

    def test_round_trip(self):
        """build_uri → parse_uri preserves the essential connection bits."""
        original = GizmoSqlConnConfig(
            host="example.internal",
            port=12345,
            use_tls=False,
            tls_skip_verify=True,
            authcfg="abc1234",
        )
        uri = GizmoSqlTools.build_uri(
            original, table="streets", schema="gis", epsg="3857"
        )
        w = GizmoSqlTools()
        conf, table, epsg, sql, schema, catalog = w.parse_uri(uri)
        self.assertEqual(conf.host, "example.internal")
        self.assertEqual(conf.port, 12345)
        self.assertFalse(conf.use_tls)
        self.assertTrue(conf.tls_skip_verify)
        self.assertEqual(conf.authcfg, "abc1234")
        self.assertEqual(table, "streets")
        self.assertEqual(schema, "gis")
        self.assertEqual(epsg, "3857")
        self.assertIsNone(sql)
        self.assertIsNone(catalog)

    def test_round_trip_with_catalog(self):
        """build_uri(catalog=...) → parse_uri returns the same catalog."""
        conf = GizmoSqlConnConfig(host="h", authcfg="abc1234")
        uri = GizmoSqlTools.build_uri(
            conf, table="cities", schema="public", catalog="mycat"
        )
        # build_uri must include catalog= in the query string
        self.assertIn("catalog=mycat", uri)
        w = GizmoSqlTools()
        _, table, _, _, schema, catalog = w.parse_uri(uri)
        self.assertEqual(catalog, "mycat")
        self.assertEqual(schema, "public")
        self.assertEqual(table, "cities")

    def test_build_uri_omits_catalog_when_absent(self):
        """No catalog kwarg → no catalog= in the resulting URI."""
        conf = GizmoSqlConnConfig(host="h", authcfg="abc1234")
        uri = GizmoSqlTools.build_uri(conf, table="t", schema="s")
        self.assertNotIn("catalog=", uri)


class TestListTablesQuery(unittest.TestCase):
    """Pinning the shape of the SQL_QUERIES['list_tables'] string.

    These are string-level assertions — they don't run the SQL — but they
    catch regressions like 'someone reverted the _gizmosql_system filter'
    or 'someone dropped the catalog. prefix' without needing a live server.
    """

    def test_returns_three_part_name(self):
        sql = GizmoSqlTools.SQL_QUERIES["list_tables"]
        self.assertIn("table_catalog", sql)
        self.assertIn("table_schema", sql)
        self.assertIn("table_name", sql)
        # Must be a single concat of all three (catalog FIRST), not a 2-part.
        self.assertIn(
            "concat(table_catalog, '.', table_schema, '.', table_name)",
            sql,
        )

    def test_excludes_gizmosql_system_catalog(self):
        sql = GizmoSqlTools.SQL_QUERIES["list_tables"]
        self.assertIn("_gizmosql_system", sql)
        self.assertIn("table_catalog NOT IN", sql)

    def test_excludes_information_schema_and_pg_catalog(self):
        sql = GizmoSqlTools.SQL_QUERIES["list_tables"]
        self.assertIn("information_schema", sql)
        self.assertIn("pg_catalog", sql)

    def test_results_are_ordered(self):
        # Ordering matters for the dialog UX — the combo would otherwise
        # surface tables in whatever order the server happens to return.
        sql = GizmoSqlTools.SQL_QUERIES["list_tables"]
        self.assertIn("ORDER BY", sql.upper())


if __name__ == "__main__":
    unittest.main()
