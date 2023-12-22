#! python3  # noqa E265

"""
    Usage from the repo root folder:

    .. code-block:: bash
        # for whole tests
        python -m unittest tests.unit.test_duckdb_wrapper
        # for specific test
        python -m unittest tests.unit.test_duckdb_wrapper.TestDdbWrapper.test_parse_uri
"""
from pathlib import Path

import duckdb
from qgis.testing import start_app, unittest

from qduckdb.provider.duckdb_wrapper import DuckDbTools
from qduckdb.provider.models import DdbExtension

from .utilities import register_provider_if_necessary


class TestDdbWrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.fixture_db_path = Path(__file__).parent.parent.joinpath(
            "fixtures/base_test.db"
        )
        cls.fixture_csv_path = Path(__file__).parent.parent.joinpath(
            "fixtures/capitals.csv"
        )
        cls.sql_query_loading_from_csv = f"""
                CREATE TEMP TABLE temp_table AS SELECT *
                    FROM read_csv_auto('{cls.fixture_csv_path}');
                DROP TABLE IF EXISTS capitals;
                CREATE TABLE capitals AS SELECT *, ST_Point(longitude, latitude) AS geom
                    FROM temp_table;
                """
        return super().setUpClass()

    def test_extensions_listing(self) -> None:
        """Test DuckDB extensions listing."""
        # starting with auto setup disabled shoud have empty extensions list
        ddb_wrapper = DuckDbTools()
        self.assertListEqual(ddb_wrapper.DDB_EXTENSIONS, [])

        packaged_extensions = ddb_wrapper.retrieve_duckdb_extensions()
        self.assertGreater(len(packaged_extensions), 0)
        self.assertListEqual(packaged_extensions, ddb_wrapper.DDB_EXTENSIONS)
        for extension in packaged_extensions:
            self.assertIsInstance(extension, DdbExtension)

        installed_extensions = ddb_wrapper.list_installed_extensions()
        for extension in installed_extensions:
            self.assertIsInstance(extension, str)

        loaded_extensions = ddb_wrapper.list_loaded_extensions()
        for extension in loaded_extensions:
            self.assertIsInstance(extension, str)

        # test install and load
        if "spatial" not in installed_extensions:
            ddb_wrapper.install_spatial_extension()
            # refresh var
            installed_extensions = ddb_wrapper.list_installed_extensions()
            self.assertIn("spatial", installed_extensions)
        if "spatial" not in loaded_extensions:
            ddb_wrapper.load_spatial_extension()
            # refresh var
            loaded_extensions = ddb_wrapper.list_loaded_extensions()
            self.assertIn("spatial", loaded_extensions)

    def test_extensions_listing_auto_setup(self) -> None:
        """Test DuckDB extensions listing."""
        # starting with auto setup disabled shoud have empty extensions list
        ddb_wrapper = DuckDbTools(auto_setup_spatial=True)
        self.assertGreater(len(ddb_wrapper.DDB_EXTENSIONS), 0)
        self.assertIn("spatial", ddb_wrapper.list_installed_extensions())
        self.assertIn("spatial", ddb_wrapper.list_loaded_extensions())

    def test_list_tables(self) -> None:
        ddb_wrapper = DuckDbTools(auto_setup_spatial=False)
        results = ddb_wrapper.run_sql(
            database_path=self.fixture_db_path, query_sql="list_tables"
        )
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_database_creation_using_conn(self) -> None:
        output_db = self.fixture_csv_path.with_name("tmp_test_db_creation_conn.db")
        ddb_wrapper = DuckDbTools(database_path=output_db, auto_setup_spatial=True)
        self.assertFalse(output_db.is_file())
        ddb_conn = ddb_wrapper.connect(read_only=False)
        self.assertTrue(output_db.is_file())
        self.assertIsInstance(ddb_conn, duckdb.DuckDBPyConnection, type(ddb_conn))
        self.assertTrue(ddb_wrapper.is_connection_alive())
        ddb_conn.sql(query=self.sql_query_loading_from_csv)
        self.assertTrue(ddb_wrapper.is_connection_alive())
        ddb_wrapper.close()
        self.assertFalse(ddb_wrapper.is_connection_alive())
        output_db.unlink(missing_ok=True)

    def test_database_creation_using_context(self) -> None:
        output_db = self.fixture_csv_path.with_name("tmp_test_db_creation_context.db")
        ddb_wrapper = DuckDbTools(database_path=output_db, auto_setup_spatial=True)

        results = ddb_wrapper.run_sql(
            read_only=False,
            requires_spatial=True,
            results_fetcher=None,
            query_sql=self.sql_query_loading_from_csv,
        )
        self.assertIsNone(results)
        self.assertFalse(ddb_wrapper.is_connection_alive())
        results = ddb_wrapper.run_sql(
            read_only=True,
            requires_spatial=False,
            query_sql="SELECT * FROM capitals LIMIT 5;",
        )
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertFalse(ddb_wrapper.is_connection_alive())
        output_db.unlink(missing_ok=True)

    def test_predefined_queries(self) -> None:
        output_db = self.fixture_csv_path.with_name("tmp_test_predefined_queries.db")
        ddb_wrapper = DuckDbTools(database_path=output_db)
        ddb_wrapper.run_sql(
            query_sql="spatial_install", read_only=False, results_fetcher=None
        )
        ddb_wrapper.run_sql(
            query_sql="spatial_load", read_only=False, results_fetcher=None
        )

        ddb_wrapper.run_sql(
            read_only=False,
            requires_spatial=True,
            results_fetcher=None,
            query_sql=self.sql_query_loading_from_csv,
        )
        results = ddb_wrapper.run_sql(
            read_only=True,
            requires_spatial=False,
            query_sql="SELECT * FROM capitals LIMIT 5;",
        )
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_database_must_exist_in_read_only(self):
        output_db = self.fixture_csv_path.with_name("tmp_test_error_not_found.db")
        ddb_wrapper = DuckDbTools(database_path=output_db)
        with self.assertRaises(FileNotFoundError):
            ddb_wrapper.run_sql(
                read_only=True,
                requires_spatial=True,
                results_fetcher=None,
                query_sql=self.sql_query_loading_from_csv,
            )

        with self.assertRaises(FileNotFoundError):
            ddb_wrapper.connect(
                read_only=True,
                requires_spatial=True,
            )

    def test_parse_uri(self) -> None:
        """Test URI parser."""
        ddb_wrapper = DuckDbTools(auto_setup_spatial=True)

        test_uri = f"path={self.fixture_db_path} table=cities epsg=4326"

        parsed_uri = ddb_wrapper.parse_uri(test_uri)

        self.assertEqual(parsed_uri[0], str(self.fixture_db_path))
        self.assertEqual(parsed_uri[1], "cities")
        self.assertEqual(parsed_uri[2], "4326")


if __name__ == "__main__":
    unittest.main()
