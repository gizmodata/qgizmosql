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
import types
import unittest

# Repo root on sys.path so ``import qgizmosql.*`` resolves against the real
# package — the stubs below only fill in the qgis / adbc bits.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _install_qgis_stubs() -> None:
    """Install minimal stubs for the ``qgis.core`` and ``qgizmosql.toolbelt``
    symbols the wrapper touches at import time.

    The wrapper module only uses these for side-effect logging, so dummy
    implementations are enough to exercise parse_uri / build_uri / config.
    """
    # qgis.core stubs
    qgis = types.ModuleType("qgis")
    qgis_core = types.ModuleType("qgis.core")

    class _MessageLevel:
        NoLevel = 0
        Info = 1
        Warning = 2
        Critical = 3
        Success = 4

    class _Qgis:
        MessageLevel = _MessageLevel

    class _QgsApplication:
        @staticmethod
        def authManager():
            return None  # tests that need it patch this

    class _QgsAuthMethodConfig:
        def __init__(self):
            self._cfg = {}

        def config(self, key):
            return self._cfg.get(key)

    qgis_core.Qgis = _Qgis
    qgis_core.QgsApplication = _QgsApplication
    qgis_core.QgsAuthMethodConfig = _QgsAuthMethodConfig
    sys.modules.setdefault("qgis", qgis)
    sys.modules["qgis.core"] = qgis_core

    # Stub the real qgizmosql.toolbelt.log_handler — it imports PlgLogger from
    # QGIS internals we don't want to pull in. Replace with a no-op before the
    # wrapper module is imported.
    log_handler_mod = types.ModuleType("qgizmosql.toolbelt.log_handler")

    class _PlgLogger:
        @staticmethod
        def log(**kwargs):
            pass

    log_handler_mod.PlgLogger = _PlgLogger
    sys.modules["qgizmosql.toolbelt.log_handler"] = log_handler_mod


_install_qgis_stubs()

# Stub adbc_driver_gizmosql so the wrapper's top-level import doesn't fail in
# environments where the real driver isn't on sys.path (CI without install).
_adbc_pkg = types.ModuleType("adbc_driver_gizmosql")
_adbc_dbapi = types.ModuleType("adbc_driver_gizmosql.dbapi")
_adbc_dbapi.connect = lambda *a, **kw: None  # overridden in integration tests
_adbc_pkg.dbapi = _adbc_dbapi
sys.modules.setdefault("adbc_driver_gizmosql", _adbc_pkg)
sys.modules.setdefault("adbc_driver_gizmosql.dbapi", _adbc_dbapi)

# Now the import is safe.
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
        conf, table, epsg, sql, schema = w.parse_uri(uri)
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

    def test_authcfg_uri(self):
        w = GizmoSqlTools()
        uri = "gizmosql://h:31337?authcfg=abc1234&table=t"
        conf, table, _, _, _ = w.parse_uri(uri)
        self.assertEqual(conf.authcfg, "abc1234")
        self.assertIsNone(conf.username)
        self.assertIsNone(conf.password)
        self.assertEqual(table, "t")

    def test_sql_uri_strips_trailing_semicolon(self):
        w = GizmoSqlTools()
        uri = "gizmosql://h:31337?sql=SELECT+1+FROM+t;"
        _, _, _, sql, _ = w.parse_uri(uri)
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
        conf, _, _, _, _ = w.parse_uri("gizmosql://h?table=t")
        self.assertEqual(conf.port, DEFAULT_GIZMOSQL_PORT)


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
        conf, table, epsg, sql, schema = w.parse_uri(uri)
        self.assertEqual(conf.host, "example.internal")
        self.assertEqual(conf.port, 12345)
        self.assertFalse(conf.use_tls)
        self.assertTrue(conf.tls_skip_verify)
        self.assertEqual(conf.authcfg, "abc1234")
        self.assertEqual(table, "streets")
        self.assertEqual(schema, "gis")
        self.assertEqual(epsg, "3857")
        self.assertIsNone(sql)


if __name__ == "__main__":
    unittest.main()
