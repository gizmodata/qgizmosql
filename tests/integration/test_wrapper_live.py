"""Integration tests that exercise the wrapper against a real GizmoSQL server.

These tests connect over Arrow Flight SQL via ``adbc-driver-gizmosql`` —
they only run when the server fixture in ``conftest.py`` is satisfiable
(Docker SDK installed locally, or ``GIZMOSQL_TEST_HOST`` set in CI).

The point of this file is the *catalog plumbing*: prove that
``list_tables`` filters out ``_gizmosql_system`` and emits 3-part names,
and that the queries we built into the provider don't fall over against
a live server. Heavy provider/dialog coverage that needs PyQGIS lives
in a separate (future) job that runs inside the QGIS Docker image.
"""

from __future__ import annotations

import os

import pytest

# Skip the whole module if the native ADBC driver isn't installed —
# integration tests need it to actually open a Flight SQL connection.
pytest.importorskip(
    "adbc_driver_gizmosql",
    reason="install `pip install adbc-driver-gizmosql` to run integration tests",
)

# Install the qgis stubs (the wrapper imports qgis.core at top level) before
# touching the wrapper. Stubs live in tests/_stubs.py so unit + integration
# share the same setup. _stubs.install() leaves the *real* adbc driver alone
# when it's importable, which is exactly what we need here.
import os  # noqa: E402
import sys  # noqa: E402

_TESTS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

from _stubs import install as _install_stubs  # noqa: E402

_install_stubs()

from qgizmosql.provider.gizmosql_wrapper import GizmoSqlTools  # noqa: E402


def _connected_tools(conn_config) -> GizmoSqlTools:
    """Return a connected GizmoSqlTools wrapper."""
    tools = GizmoSqlTools(conn_config=conn_config)
    tools.connect()
    return tools


@pytest.mark.integration
def test_connection_alive(gizmosql_conn_config):
    """Sanity: SELECT 1; round-trips and the wrapper returns a row."""
    tools = _connected_tools(gizmosql_conn_config)
    rows = tools.run_sql("connection_alive")
    assert len(rows) == 1
    assert rows[0][0] == 1


@pytest.mark.integration
def test_list_tables_emits_three_part_names(gizmosql_conn_config):
    """Every row from list_tables is `catalog.schema.table` (>= 2 dots)."""
    tools = _connected_tools(gizmosql_conn_config)
    # Seed at least one user table so list_tables has something to return
    # regardless of what the test container starts with.
    with tools.conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS qgz_test_cities ("
            "  id INTEGER, name VARCHAR"
            ")"
        )

    rows = tools.run_sql("list_tables")
    assert rows, "list_tables returned no rows even after seeding a table"
    for (qualified,) in rows:
        # Three-part name → exactly two dots in the catalog/schema/table form.
        assert qualified.count(".") >= 2, (
            f"expected catalog.schema.table format, got {qualified!r}"
        )


@pytest.mark.integration
def test_list_tables_hides_gizmosql_system_catalog(gizmosql_conn_config):
    """The internal `_gizmosql_system` catalog must never appear in the picker."""
    tools = _connected_tools(gizmosql_conn_config)
    rows = tools.run_sql("list_tables")
    catalogs = {qualified.split(".", 1)[0] for (qualified,) in rows}
    assert "_gizmosql_system" not in catalogs, (
        f"_gizmosql_system leaked into list_tables; catalogs seen: {catalogs}"
    )


@pytest.mark.integration
def test_list_tables_hides_information_schema(gizmosql_conn_config):
    """Standard SQL system schemas stay hidden too."""
    tools = _connected_tools(gizmosql_conn_config)
    rows = tools.run_sql("list_tables")
    for (qualified,) in rows:
        # qualified == "<catalog>.<schema>.<table>"
        parts = qualified.split(".")
        schema = parts[-2]
        assert schema not in ("information_schema", "pg_catalog"), (
            f"system schema {schema!r} leaked into list_tables: {qualified!r}"
        )


@pytest.mark.integration
def test_current_database_is_resolvable(gizmosql_conn_config):
    """The provider relies on `SELECT current_database()` to default catalog;
    confirm the server actually has one."""
    tools = _connected_tools(gizmosql_conn_config)
    with tools.conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        catalog = cur.fetchone()[0]
    assert isinstance(catalog, str) and catalog, (
        f"current_database() returned {catalog!r}; provider's catalog default "
        f"would break"
    )


@pytest.mark.integration
def test_information_schema_is_qualifiable_by_catalog(gizmosql_conn_config):
    """Bind-parameter version of the provider's column-list query — proves
    that `WHERE table_catalog = ? AND table_schema = ? AND table_name = ?`
    actually returns rows for a real, default-catalog table."""
    tools = _connected_tools(gizmosql_conn_config)
    with tools.conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS qgz_probe_tbl ("
            "  pk INTEGER PRIMARY KEY, name VARCHAR"
            ")"
        )
        cur.execute("SELECT current_database()")
        catalog = cur.fetchone()[0]

        cur.execute(
            operation=(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_catalog = ? AND table_schema = ? "
                "AND table_name = ? "
                "ORDER BY ordinal_position"
            ),
            parameters=[catalog, "main", "qgz_probe_tbl"],
        )
        cols = [row[0] for row in cur.fetchall()]
    assert cols == ["pk", "name"], (
        f"catalog-qualified information_schema query returned {cols!r}"
    )


def pytest_configure(config):
    """Register the `integration` marker so `pytest -m integration` works
    without an `unknown mark` warning, and so users can `-m 'not integration'`
    to skip in non-integration environments.
    """
    config.addinivalue_line("markers", "integration: hits a live GizmoSQL server")
