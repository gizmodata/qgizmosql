import unittest
from pathlib import Path

from qgis.core import (
    QgsFields,
    QgsProviderMetadata,
    QgsProviderRegistry,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsWkbTypes,
)

from qduckdb.duckdb_provider import DuckdbProvider

db_path = Path(__file__).parent.joinpath("data/base_test.db")


class TestQDuckDBProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Run before all tests"""
        super(TestQDuckDBProvider, cls).setUpClass()
        # Register the provider
        r = QgsProviderRegistry.instance()
        metadata = QgsProviderMetadata(
            DuckdbProvider.providerKey(),
            DuckdbProvider.description(),
            DuckdbProvider.createProvider,
        )
        assert r.registerProvider(metadata)
        assert r.providerMetadata(DuckdbProvider.providerKey()) == metadata

    def test_get_capabilities(self):
        provider = DuckdbProvider()
        assert (
            provider.capabilities()
            == QgsVectorDataProvider.CreateSpatialIndex
            | QgsVectorDataProvider.SelectAtId
        )

    def test_register_same_provider_twice(self):
        """Test that a provider cannot be registered twice"""
        r = QgsProviderRegistry.instance()
        metadata = QgsProviderMetadata(
            DuckdbProvider.providerKey(),
            DuckdbProvider.description(),
            DuckdbProvider.createProvider,
        )
        self.assertFalse(r.registerProvider(metadata))

    def test_valid(self):
        db_path = Path(__file__).parent.joinpath("data/base_test.db")

        correct_uri = f"path={db_path} table=cities"
        provider = DuckdbProvider(uri=correct_uri)
        self.assertTrue(provider.isValid())
        self.assertEqual(provider.dataSourceUri(), correct_uri)

        # Test table without geom
        provider = DuckdbProvider(uri=f"path={db_path} table=table_no_geom")
        self.assertFalse(provider.isValid())

    def test_wrong_uri(self):
        provider = DuckdbProvider(uri="zidane")
        self.assertFalse(provider.isValid())

    def test_geom_mapping(self):
        # Point
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Point)

        # Linestring
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=highway")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.LineString)

        # Polygon
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=building")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Polygon)

        # Geom with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

        # Table without geom
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=tabke_no_geom")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_extent(self):
        # Test linestring layer
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=highway")
        self.assertIsInstance(provider.extent(), QgsRectangle)
        self.assertEqual(
            provider.extent(),
            QgsRectangle(
                -0.75798929999999998,
                48.08263490000000218,
                -0.75523320000000005,
                48.08447269999999918,
            ),
        )

        # Test point layer
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertIsInstance(provider.extent(), QgsRectangle)
        self.assertEqual(
            provider.extent(),
            QgsRectangle(
                2.15899000000000019,
                41.38879000000000019,
                7.68681999999999999,
                45.0704899999999995,
            ),
        )

        # Extend with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(
            provider.extent().asWktPolygon(), "POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))"
        )

    def test_fields(self):
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(0).name(), "geoname_id")
        self.assertEqual(provider.fields().field(0).type(), 2)

        # Fields with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.fields().count(), 0)

    def test_get_geometry_column(self):
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertEqual(provider.get_geometry_column()[0], "geom")

    def test_table_without_geom_column(self):
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=table_no_geom")
        self.assertEqual(provider.get_geometry_column(), None)
        self.assertEqual(
            provider.extent().asWktPolygon(), "POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_featureCount(self):
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertEqual(provider.featureCount(), 3)

        # Count with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.featureCount(), 0)


if __name__ == "__main__":
    unittest.main()
