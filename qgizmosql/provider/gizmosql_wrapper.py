"""GizmoSQL client wrapper. Holds every logic related to talking to a GizmoSQL
(Arrow Flight SQL) server via the ADBC driver.

References:

- https://pypi.org/project/adbc-driver-gizmosql/
- https://arrow.apache.org/adbc/current/driver/flight_sql.html
- https://github.com/gizmodata/gizmosql-public
"""

# standard
from typing import Any, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse

# PyQGIS
from qgis.core import Qgis

# plugin
from qgizmosql.toolbelt.log_handler import PlgLogger

# conditional imports — prefer the Python env's copy, fall back to the plugin's
# embedded_external_libs directory (how QGIS on Windows ships extra deps).
try:
    from adbc_driver_gizmosql import dbapi as gizmosql_dbapi  # type: ignore

    PlgLogger.log(message="adbc-driver-gizmosql loaded from Python installation.")
except Exception:
    PlgLogger.log(
        message="Import from Python installation failed. Trying to load from "
        "embedded external libs.",
        log_level=Qgis.MessageLevel.Info,
        push=False,
    )
    import site

    from qgizmosql.__about__ import DIR_PLUGIN_ROOT

    site.addsitedir(str(DIR_PLUGIN_ROOT / "embedded_external_libs"))
    from adbc_driver_gizmosql import dbapi as gizmosql_dbapi  # type: ignore

    PlgLogger.log(
        message="adbc-driver-gizmosql loaded from embedded external libs."
    )


# Default Flight SQL port used by the GizmoSQL Docker image.
DEFAULT_GIZMOSQL_PORT: int = 31337


# -- CONNECTION CONFIG ---------------------------------------------------------


class GizmoSqlConnConfig:
    """Immutable-ish bundle of connection parameters for a GizmoSQL server.

    Mirrors the kwargs accepted by :func:`adbc_driver_gizmosql.dbapi.connect`.
    Constructed from a parsed QGIS URI (see :meth:`GizmoSqlTools.parse_uri`) or
    directly by the connection dialog.
    """

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_GIZMOSQL_PORT,
        use_tls: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_type: str = "password",
        tls_skip_verify: bool = False,
    ):
        self.host = host
        self.port = int(port)
        self.use_tls = bool(use_tls)
        self.username = username
        self.password = password
        self.auth_type = auth_type  # "password" | "external" (OAuth/SSO)
        self.tls_skip_verify = bool(tls_skip_verify)

    @property
    def flight_uri(self) -> str:
        """Flight SQL URI string passed to the ADBC driver."""
        scheme = "grpc+tls" if self.use_tls else "grpc"
        return f"{scheme}://{self.host}:{self.port}"

    def connect_kwargs(self) -> dict:
        """Build the kwargs dict for gizmosql_dbapi.connect()."""
        kwargs: dict = {
            "tls_skip_verify": self.tls_skip_verify,
        }
        if self.auth_type == "external":
            kwargs["auth_type"] = "external"
        else:
            if self.username is not None:
                kwargs["username"] = self.username
            if self.password is not None:
                kwargs["password"] = self.password
        return kwargs

    def display_name(self) -> str:
        """Short human-readable identifier — used in log messages."""
        return f"{self.host}:{self.port}"

    def __repr__(self) -> str:
        return (
            f"GizmoSqlConnConfig(host={self.host!r}, port={self.port}, "
            f"use_tls={self.use_tls}, auth_type={self.auth_type!r}, "
            f"username={self.username!r}, password={'***' if self.password else None})"
        )


# -- MAIN WRAPPER --------------------------------------------------------------


class GizmoSqlTools:
    """High-level operations against a GizmoSQL server."""

    SQL_QUERIES: dict = {
        "connection_alive": "SELECT 1;",
        "list_tables": (
            "SELECT concat(table_schema, '.', table_name) AS table_name "
            "FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog')"
        ),
        "list_schemas": (
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
        ),
    }

    def __init__(self, conn_config: Optional[GizmoSqlConnConfig] = None):
        self.conn_config: Optional[GizmoSqlConnConfig] = conn_config
        self.conn: Any = None  # adbc_driver_gizmosql.dbapi.Connection

        # Parsed URI attributes (set by parse_uri)
        self._table_name: Optional[str] = None
        self._epsg_code: Optional[str] = None
        self._sql: Optional[str] = None
        self._schema: Optional[str] = None

    # -- CONNECT / CLOSE / ALIVE -----------------------------------------------

    def connect(self) -> Any:
        """Open a connection to the GizmoSQL server (or return the existing one).

        :return: adbc_driver_gizmosql.dbapi.Connection
        """
        if self.conn_config is None:
            raise ValueError(
                "No connection config set on the wrapper. Call parse_uri() first "
                "or pass conn_config to the constructor."
            )

        if self.is_connection_alive():
            PlgLogger.log(
                message=f"Connection to {self.conn_config.display_name()} already open.",
                log_level=Qgis.MessageLevel.Info,
                push=False,
            )
            return self.conn

        try:
            self.conn = gizmosql_dbapi.connect(
                self.conn_config.flight_uri,
                **self.conn_config.connect_kwargs(),
            )
            PlgLogger.log(
                message=f"Connected to GizmoSQL at {self.conn_config.display_name()}.",
                log_level=Qgis.MessageLevel.Info,
                push=False,
            )
            return self.conn
        except Exception as exc:
            PlgLogger.log(
                message=(
                    f"Connection to {self.conn_config.display_name()} failed. "
                    f"Trace: {exc}"
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            raise

    def close(self) -> None:
        """Close the connection held at wrapper level, if any."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception as exc:
                PlgLogger.log(
                    message=f"Error while closing connection. Trace: {exc}",
                    log_level=Qgis.MessageLevel.Warning,
                    push=False,
                )
            finally:
                self.conn = None

    def is_connection_alive(self) -> bool:
        """Return True if self.conn is a live, responsive connection."""
        if self.conn is None:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(self.SQL_QUERIES["connection_alive"])
                cur.fetchone()
            return True
        except Exception:
            return False

    # -- QUERY -----------------------------------------------------------------

    def run_sql(
        self,
        query_sql: str,
        results_fetcher: str = "fetchall",
    ) -> Union[list, tuple, Any, None]:
        """Execute SQL against the GizmoSQL server and return results.

        :param query_sql: SQL string, or a key from :attr:`SQL_QUERIES`.
        :param results_fetcher: one of ``"fetchall"``, ``"fetchone"``,
            ``"fetch_arrow"`` (returns a pyarrow.Table), or ``"no_output"``.
        """
        if query_sql in self.SQL_QUERIES:
            query_sql = self.SQL_QUERIES[query_sql]

        if not self.is_connection_alive():
            self.connect()

        try:
            with self.conn.cursor() as cur:
                cur.execute(query_sql)
                if results_fetcher == "fetchall":
                    result = cur.fetchall()
                elif results_fetcher == "fetchone":
                    result = cur.fetchone()
                elif results_fetcher == "fetch_arrow":
                    result = cur.fetch_arrow_table()
                elif results_fetcher == "no_output":
                    result = None
                else:
                    raise ValueError(
                        f"Unknown results_fetcher: {results_fetcher!r}"
                    )
            PlgLogger.log(
                message=(
                    f"Query succeeded on {self.conn_config.display_name()}: "
                    f"{query_sql[:120]}"
                ),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )
            return result
        except Exception as exc:
            PlgLogger.log(
                message=(
                    f"Query failed on {self.conn_config.display_name()}. "
                    f"SQL: {query_sql!r}. Trace: {exc}"
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            raise

    # -- URI ENCODING / DECODING -----------------------------------------------

    # QGIS passes the plugin a single URI string to identify a layer. We use a
    # query-string format because QGIS's providerMetadata.encodeUri/decodeUri
    # expects a dict of str — the old DuckDB plugin leaned on that; we roll our
    # own parsing here so the wrapper works outside of the provider registry too.
    #
    # Example URI:
    #   gizmosql://host:31337?use_tls=1&tls_skip_verify=1&auth_type=password
    #       &username=gizmosql_user&password=gizmosql_password
    #       &schema=main&table=my_spatial_table&epsg=4326

    URI_SCHEME = "gizmosql"

    def parse_uri(self, uri: str) -> tuple[
        GizmoSqlConnConfig,
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
    ]:
        """Parse a qgizmosql layer URI.

        :return: (conn_config, table, epsg, sql, schema)
        """
        parsed = urlparse(uri)
        if parsed.scheme and parsed.scheme != self.URI_SCHEME:
            raise ValueError(
                f"Invalid URI scheme: expected {self.URI_SCHEME!r}, got "
                f"{parsed.scheme!r} in {uri!r}"
            )

        if not parsed.hostname:
            raise ValueError(f"URI missing host: {uri!r}")

        q = dict(parse_qsl(parsed.query, keep_blank_values=True))

        def _bool(v: Optional[str], default: bool) -> bool:
            if v is None:
                return default
            return v.strip().lower() in ("1", "true", "yes", "on")

        conn_config = GizmoSqlConnConfig(
            host=parsed.hostname,
            port=parsed.port or DEFAULT_GIZMOSQL_PORT,
            use_tls=_bool(q.get("use_tls"), True),
            username=q.get("username"),
            password=q.get("password"),
            auth_type=q.get("auth_type", "password"),
            tls_skip_verify=_bool(q.get("tls_skip_verify"), False),
        )

        table = q.get("table") or None
        epsg = q.get("epsg") or None
        sql = q.get("sql") or None
        schema = q.get("schema") or None

        # Trailing-semicolon workaround: we don't support multi-statement transactions.
        if sql:
            sql = sql.rstrip().rstrip(";")

        # Save for wrapper-level reuse
        self.conn_config = conn_config
        self._table_name = table
        self._epsg_code = epsg
        self._sql = sql
        self._schema = schema

        PlgLogger.log(
            message=(
                f"URI parsed: host={conn_config.display_name()} "
                f"auth={conn_config.auth_type} table={table} schema={schema} "
                f"epsg={epsg} sql={'<set>' if sql else None}"
            ),
            log_level=Qgis.MessageLevel.NoLevel,
            push=False,
        )

        return conn_config, table, epsg, sql, schema

    @staticmethod
    def build_uri(
        conn_config: GizmoSqlConnConfig,
        table: Optional[str] = None,
        schema: Optional[str] = None,
        epsg: Optional[str] = None,
        sql: Optional[str] = None,
    ) -> str:
        """Build a layer URI from a connection config and layer bits."""
        params: dict = {
            "use_tls": "1" if conn_config.use_tls else "0",
            "tls_skip_verify": "1" if conn_config.tls_skip_verify else "0",
            "auth_type": conn_config.auth_type,
        }
        if conn_config.username:
            params["username"] = conn_config.username
        if conn_config.password:
            params["password"] = conn_config.password
        if table:
            params["table"] = table
        if schema:
            params["schema"] = schema
        if epsg:
            params["epsg"] = epsg
        if sql:
            params["sql"] = sql
        return (
            f"{GizmoSqlTools.URI_SCHEME}://{conn_config.host}:{conn_config.port}"
            f"?{urlencode(params)}"
        )
