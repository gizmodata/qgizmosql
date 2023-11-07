"""DuckDB client wrapper and helpers, meant to hold every logic related to the DuckDB
client.

References:

- https://duckdb.org/docs/api/python/overview
- https://duckdb.org/docs/extensions/spatial
"""

# standard
from pathlib import Path
from typing import Optional, Union

# plugin
from qduckdb.provider.models import DdbExtension
from qduckdb.toolbelt.log_handler import PlgLogger

# conditional imports
try:
    import duckdb

    PlgLogger.log(message="Dependencies loaded from Python installation.")
except Exception:
    PlgLogger.log(
        message="Import from Python installation failed. Trying to load from "
        "embedded external libs.",
        log_level=0,
        push=False,
    )
    import site

    from qduckdb.__about__ import DIR_PLUGIN_ROOT

    site.addsitedir(DIR_PLUGIN_ROOT / "embedded_external_libs")
    import duckdb

    PlgLogger.log(
        message=f"Dependencies loaded from embedded external libs: {duckdb.__version__=}"
    )


# -- CLASSES --
class DuckDbTools:
    """High-level operations with duckdb."""

    # DuckDB installation
    DDB_EXTENSIONS: list[DdbExtension] = []
    DDB_VERSION: str = duckdb.__version__

    # predefined SQL queries
    SQL_QUERIES: dict = {
        "connection_alive": "SELECT 1;",
        "duckdb_settings": "SELECT * FROM duckdb_settings();",
        "list_extensions": "SELECT extension_name, installed, loaded FROM duckdb_extensions();",
        "list_tables": "SELECT table_name from information_schema.tables;",
        "spatial_install": "INSTALL spatial;",
        "spatial_load": "LOAD spatial;",
    }

    def __init__(
        self,
        database_path: Union[str, Path, None] = None,
        auto_setup_spatial: bool = False,
    ):
        """Object instanciation.

        :param database_path: _description_, defaults to None
        :type database_path: Union[str, Path, None], optional
        """
        # init class
        self.ddb_conn: Union[duckdb.DuckDBPyConnection, None] = None
        self.database_path = database_path

        # perform automatic operations
        if auto_setup_spatial:
            self.load_spatial_extension()

        # attributes
        self._table_name: str = None
        self._epsg_code: str = None

    def connect(
        self,
        read_only: bool = True,
        requires_spatial: bool = True,
    ) -> duckdb.DuckDBPyConnection:
        """Open a connection to the DuckDB database and let it opened. Useful to
            perform multiple requests at different points of a workflow. But don't
            forget to properly close the connection (using self.close()) once you're
            done.

        :param query_sql: SQL query to perform against the database
        :type query_sql: str
        :param read_only: read-only mode, defaults to True
        :type read_only: bool, optional
        :param requires_spatial: option to load spatial extension before running the
            SQL query, defaults to True
        :type requires_spatial: bool, optional

        :return: connection object
        :rtype: duckdb.DuckDBPyConnection
        """
        # determine which database to use
        if not self.database_path.is_file() and read_only is True:
            raise FileNotFoundError(
                "In read-only mode, database must exist before. "
                "Database path passed as parameter does not: {}".format(
                    self.database_path
                )
            )

        PlgLogger.log(
            message="Using the database path defined at object level: {}".format(
                self.database_path
            ),
            log_level=4,
            push=False,
        )

        # check if connection is already alive
        if self.is_connection_alive():
            PlgLogger.log(
                message="An open connection to {} already exists. Use it or close it "
                "before.".format(self.database_path.resolve()),
                log_level=0,
                push=False,
            )
            return self.ddb_conn

        try:
            self.ddb_conn = duckdb.connect(
                database=f"{self.database_path.resolve()}", read_only=read_only
            )

            PlgLogger.log(
                message="Connection to database {} succeeded.".format(
                    self.database_path.resolve()
                ),
                log_level=0,
                push=False,
            )

            if requires_spatial:
                self.ddb_conn.sql(query=self.SQL_QUERIES.get("spatial_load"))
                PlgLogger.log(
                    message="Spatial extension loaded on database {}.".format(
                        self.database_path.resolve()
                    ),
                    log_level=0,
                    push=False,
                )
            return self.ddb_conn

        except duckdb.IOException as exc:
            PlgLogger.log(
                "{} is not a valid database DuckDB. Trace: {}".format(
                    self.database_path.resolve(), exc
                ),
                log_level=2,
                push=True,
            )
            raise exc
        except duckdb.ConnectionException as exc:
            PlgLogger.log(
                "Connection to {} failed. Trace: {}".format(
                    self.database_path.resolve(), exc
                ),
                log_level=2,
                push=True,
            )
            raise exc
        except Exception as exc:
            PlgLogger.log(
                "Connection to {} failed for a generic reason. Trace: {}".format(
                    self.database_path.resolve(), exc
                ),
                log_level=2,
                push=True,
            )
            raise exc

    def close(self):
        """Close the connection stored in class attribute."""
        if (
            self.is_connection_alive()
            and isinstance(self.ddb_conn, duckdb.DuckDBPyConnection)
            and hasattr(self.ddb_conn, "close")
        ):
            self.ddb_conn.close()
            PlgLogger.log(
                "Connection to {} has been closed.".format(
                    self.database_path.resolve()
                ),
                log_level=2,
                push=True,
            )
            return self.ddb_conn

    def run_sql(
        self,
        query_sql: str,
        database_path: Optional[Path] = None,
        read_only: bool = True,
        results_fetcher: str = "fetchall",
        requires_spatial: bool = True,
    ) -> list:
        """Executes SQL query in a context manager that open a connection to the
            database, perform the query, close properly the connection and returns the
            result.

        :param query_sql: SQL query to perform against the database
        :type query_sql: str
        :param database_path: path to the database file. If None, it tries to use the
            database defined at object level, defaults to None
        :type database_path: Optional[Path], optional
        :param read_only: read-only mode, defaults to True
        :type read_only: bool, optional
        :param results_fetcher: method to use to fetch results, defaults to "fetchall"
        :type results_fetcher: str, optional
        :param requires_spatial: option to load spatial extension before running the
            SQL query, defaults to True
        :type requires_spatial: bool, optional

        :raises exc: _description_
        :return: results list
        :rtype: list
        """

        # determine which database to use
        if isinstance(database_path, Path):
            # check incompatibility with read-only mode
            if read_only and not database_path.is_file():
                raise FileNotFoundError(
                    "In read-only mode, database must exist before. "
                    "Database path passed as parameter does not: {}".format(
                        database_path
                    )
                )

            PlgLogger.log(
                message="Using the passed database path: {}".format(database_path),
                log_level=4,
                push=False,
            )

            # if there is no database path defined at wrapper's level, let's use this
            if not isinstance(self.database_path, Path) or (
                isinstance(self.database_path, Path)
                and not self.database_path.is_file()
            ):
                PlgLogger.log(
                    message="Defining the passed database path as wrapper's level: {}".format(
                        database_path
                    ),
                    log_level=4,
                    push=False,
                )

        elif database_path is None and isinstance(self.database_path, Path):
            # using database path defined at wrapper's level

            # check incompatibility with read-only mode
            if read_only and not self.database_path.is_file():
                raise FileNotFoundError(
                    "In read-only mode, database must exist before. "
                    "Wrapper's defined database does not: {}".format(self.database_path)
                )

            database_path = self.database_path
            PlgLogger.log(
                message="Using the database path defined at object level: {}".format(
                    database_path
                ),
                log_level=4,
                push=False,
            )
        else:
            err_message = (
                "Neither the database path passed in parameter ({}) nor the one "
                "defined at wrapper's level ({}) is valid.".format(
                    database_path, self.database_path
                )
            )
            PlgLogger.log(
                message=err_message,
                log_level=2,
                push=True,
            )
            raise FileNotFoundError(err_message)

        # handle predefined SQL queries
        if query_sql in self.SQL_QUERIES:
            query_sql = self.SQL_QUERIES.get(query_sql)

        # try to run query
        try:
            with duckdb.connect(
                database=f"{database_path.resolve()}", read_only=read_only
            ) as con:
                if requires_spatial:
                    con.sql(query=self.SQL_QUERIES.get("spatial_load"))

                query_results = con.sql(query_sql)

                # fetch results depending on specified method
                if results_fetcher == "fetchall":
                    query_results = query_results.fetchall()
                elif results_fetcher == "fetchone":
                    query_results = query_results.fetchone()

            # connection is now closed
            PlgLogger.log(
                message="SUCCESS - Query '{}' on '{}' database.".format(
                    query_sql, self.database_path
                ),
                log_level=4,
                push=False,
            )
            return query_results

        except Exception as exc:
            PlgLogger.log(
                message="Querying '{}' in the {} database failed. Trace: {}".format(
                    query_sql, self.database_path, exc
                ),
                log_level=2,
                push=True,
            )
            raise exc

    def install_spatial_extension(self) -> None:
        """Make sure that spatial extension is installed in DuckDB client."""
        if self.is_spatial_extension_installed():
            PlgLogger.log(
                message="Spatial extension is already installed in DuckDB engine.",
                log_level=4,
                push=False,
            )
            return
        try:
            duckdb.sql(self.SQL_QUERIES.get("spatial_install"))
            PlgLogger.log(
                message="Spatial extension has been installed in DuckDB engine.",
                log_level=0,
                push=False,
            )
        except Exception as exc:
            PlgLogger.log(
                message="Unable to install spatial extension in DuckDB. Trace: {}".format(
                    exc
                ),
                log_level=2,
                push=True,
            )
            raise exc

    def is_connection_alive(self) -> bool:
        """Check if the connection attribute (self.con) is functional and opened.

        :return: True if the self.con and self.datababase_path attributes exist, and if
            the connection is valid (not closed or not failing on a simple query).
        :rtype: bool
        """
        if not isinstance(self.ddb_conn, duckdb.DuckDBPyConnection):
            PlgLogger.log(
                message="Connection attribute is not a valid DuckDbPyConnection object, "
                "but {}".format(type(self.ddb_conn)),
                log_level=4,
                push=False,
            )
            return False

        if self.database_path is None:
            PlgLogger.log(
                message="Connection object does not exist. to {} is not alive or not "
                "working.".format(self.database_path),
                log_level=4,
                push=False,
            )
            return False

        try:
            self.ddb_conn.sql(self.SQL_QUERIES.get("connection_alive"))
            PlgLogger.log(
                message="Connection to {} is still alive".format(self.database_path),
                log_level=4,
                push=False,
            )
            return True
        except duckdb.ConnectionException as exc:
            PlgLogger.log(
                message="Connection to {} is not alive or not working. "
                "Trace: {}".format(self.database_path, exc),
                log_level=4,
                push=False,
            )
            return False
        except Exception as exc:
            PlgLogger.log(
                message="Connection to {} is not working. "
                "Trace: {}".format(self.database_path, exc),
                log_level=4,
                push=False,
            )
            return False

    def is_spatial_extension_installed(self) -> bool:
        """Check if spatial extension is installed in DuckDB client.

        :return: True if spatial is part of DuckDB installed extensions
        :rtype: bool
        """
        return "spatial" in self.list_installed_extensions()

    def is_spatial_extension_loaded(self) -> bool:
        """Check if spatial extension is loaded in DuckDB client.

        :return: True if spatial is part of DuckDB loaded extensions
        :rtype: bool
        """
        return "spatial" in self.list_loaded_extensions()

    def retrieve_duckdb_extensions(self) -> list[DdbExtension]:
        """Retrieve DuckDB's extensions names and status (loaded and installed).

        Remember that this request is performed at the duckdb installation level (not
            in a specific database). If the request works, extensions list is also
            stored as DDB_EXTENSIONS attribute.

        :return: list of DuckDB extensions
        :rtype: list[DdbExtension]
        """
        try:
            self.DDB_EXTENSIONS = [
                DdbExtension(
                    name=result[0], is_installed=result[1], is_loaded=result[2]
                )
                for result in duckdb.sql(
                    query=self.SQL_QUERIES.get("list_extensions")
                ).fetchall()
            ]
            PlgLogger.log(
                message="Retrieving DuckDB client's extensions succeeded: {}".format(
                    "; ".join([extension.name for extension in self.DDB_EXTENSIONS])
                ),
                log_level=0,
                push=False,
            )
            return self.DDB_EXTENSIONS
        except Exception as exc:
            PlgLogger.log(
                message="Unable to retrieve DuckDB client's extensions. Trace: {}".format(
                    exc
                ),
                log_level=2,
                push=True,
            )
            return []

    def list_installed_extensions(self) -> list[str]:
        """List DuckDB's extensions installed.

        :return: list of installed extensions
        :rtype: list[str]
        """
        if not self.DDB_EXTENSIONS:
            self.retrieve_duckdb_extensions()

        ddb_installed_extensions = [
            extension.name
            for extension in self.DDB_EXTENSIONS
            if extension.is_installed is True
        ]

        PlgLogger.log(
            message="List of DuckDB installed extensions succeeded: {}".format(
                "; ".join(ddb_installed_extensions)
            ),
            log_level=0,
            push=False,
        )

        return ddb_installed_extensions

    def list_loaded_extensions(self) -> list[str]:
        """List DuckDB's extensions which are loaded.

        :return: list of loaded extensions
        :rtype: list[str]
        """
        if not self.DDB_EXTENSIONS:
            self.retrieve_duckdb_extensions()

        ddb_loaded_extensions = [
            extension.name
            for extension in self.DDB_EXTENSIONS
            if extension.is_loaded is True
        ]

        PlgLogger.log(
            message="List of DuckDB loaded extensions succeeded: {}".format(
                "; ".join(ddb_loaded_extensions)
            ),
            log_level=0,
            push=False,
        )

        return ddb_loaded_extensions

    def load_spatial_extension(self, database_path: Optional[Path] = None) -> None:
        """Load spatial extension on the specified database or at DuckDB level.

        :param database_path: path to a specific database. If None, the extension is
            loaded at the DuckDB's installation level, defaults to None
        :type database_path: Optional[Path], optional
        """
        # first check spatial extension is installed
        self.install_spatial_extension()

        # load extension at database or installation level
        if isinstance(database_path, Path) and database_path.is_file():
            PlgLogger.log(
                message="Loading spatial extension on the specified database {}".format(
                    database_path
                ),
                log_level=4,
                push=False,
            )
            self.run_sql(query_sql="spatial_load", database_path=database_path)
        elif isinstance(self.database_path, Path) and self.database_path.is_file():
            PlgLogger.log(
                message="Loading spatial extension on the database defined at wrapper {}".format(
                    database_path
                ),
                log_level=4,
                push=False,
            )
            self.run_sql(
                query_sql="spatial_load",
                database_path=self.database_path,
                results_fetcher=None,
                requires_spatial=False,
            )
        elif self.is_spatial_extension_loaded():
            PlgLogger.log(
                message="Spatial extension is already loaded on DuckDB client",
                log_level=4,
                push=False,
            )
        else:
            PlgLogger.log(
                message="Loading spatial extension on DuckDB client",
                log_level=4,
                push=False,
            )
            duckdb.sql(query=self.SQL_QUERIES.get("spatial_load"))
            PlgLogger.log(
                message="Spatial extension has been loaded into DuckDB client",
                log_level=4,
                push=False,
            )
        self.retrieve_duckdb_extensions()

    def parse_uri(self, uri: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse the input URI and returns the path to the database and the name of the
        table. If the parsing is successfull, the path, table, and epsg are set at wwrapper's level.

        :param uri: input URI connection
        :type uri: str

        :return: tuple with database path, table name and CRS code
        :rtype: tuple[Optional[str], Optional[str], Optional[str]]

        :example:

            .. code-block:: python

                >>> test_uri = f"path=/home/test/gis/insee/bureaux_vote.db table=cities epsg=4326"
                >>> db_path, table_name, epsg_code = ddb_wrapper.parse_uri(test_uri)
        """
        path = None
        table = None
        epsg = None
        for variable in uri.split(" "):
            try:
                key, value = variable.split("=")
                if key == "path":
                    path = value
                elif key == "table":
                    table = value
                elif key == "epsg":
                    epsg = value
            except ValueError as exc:
                PlgLogger.log(
                    message="Parsing URI failed: {}".format(exc),
                    log_level=1,
                    push=False,
                )

        PlgLogger.log(
            message="URI parsed successfully: path={} ; table={} ; epsg={}".format(
                path, table, epsg
            ),
            log_level=4,
            push=False,
        )

        # check parsing results
        if not path or not table:
            raise ValueError(
                "Invalid URI. Expected something like: path=/fake_path/database_duck.db "
                "table=table_name epsg=4326. Received: {}".format(uri)
            )

        # check database path
        if not Path(path).is_file():
            raise FileNotFoundError(
                "Database does not exists at the specified path: {}".format(path)
            )

        # set results as wrapper attributes
        self.database_path = Path(path)
        self._table_name = table
        self._epsg_code = epsg

        PlgLogger.log(
            message="Results from URI parsing are now used as wrapper attributes.",
            log_level=4,
            push=False,
        )

        return path, table, epsg
