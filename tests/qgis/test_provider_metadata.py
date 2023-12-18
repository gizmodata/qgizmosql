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

        cls.provider_metadata = QgsProviderRegistry.instance().providerMetadata("duckdb")

        cls.db_path = "/home/foo/project/database.path"
        cls.table = "mytable"
        cls.epsg = 4326
        cls.expected_uri = f"path={cls.db_path} table={cls.table} epsg={cls.epsg}"

    def test_encode_uri(self):
        parts = {
            "path": self.db_path,
            "table": self.table,
            "epsg": self.epsg
        }
        uri = self.provider_metadata.encodeUri(parts)
        self.assertEqual(uri, self.expected_uri)

    def test_decode_uri(self):
        parts = self.provider_metadata.decodeUri(self.expected_uri)
        self.assertEqual(parts["path"], self.db_path)
        self.assertEqual(parts["table"], self.table)
        self.assertEqual(int(parts["epsg"]), self.epsg)
