from qgis.core import QgsProviderRegistry
from qgis.testing import start_app, unittest

from .utilities import register_provider_if_necessary


class TestQDuckDBProviderMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Run before all tests"""
        super(TestQDuckDBProviderMetadata, cls).setUpClass()

        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

    def test_encode_uri(self):
        duckdbProviderMetadata = QgsProviderRegistry.instance().providerMetadata("duckdb")

        db_path = "/home/foo/project/database.path"
        table = "mytable"
        epsg = 4326

        expected_uri = f"path={db_path} table={table} epsg={epsg}"

        parts = {
            "path": db_path,
            "table": table,
            "epsg": epsg
        }
        abs_uri = duckdbProviderMetadata.encodeUri(parts)
        self.assertEqual(abs_uri, expected_uri)
