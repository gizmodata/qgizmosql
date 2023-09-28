import unittest
from pathlib import Path

from qgis.core import (
    QgsFields,
    QgsProviderMetadata,
    QgsProviderRegistry,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.Qt import QVariant

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

    def test_get_capabilities(self) -> None:
        provider = DuckdbProvider()
        self.assertEqual(
            provider.capabilities(),
            QgsVectorDataProvider.CreateSpatialIndex | QgsVectorDataProvider.SelectAtId,
        )

    def test_register_same_provider_twice(self) -> None:
        """Test that a provider cannot be registered twice"""
        r = QgsProviderRegistry.instance()
        metadata = QgsProviderMetadata(
            DuckdbProvider.providerKey(),
            DuckdbProvider.description(),
            DuckdbProvider.createProvider,
        )
        self.assertFalse(r.registerProvider(metadata))

    def test_valid(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")

        correct_uri = f"path={db_path} table=cities"
        provider = DuckdbProvider(uri=correct_uri)
        self.assertTrue(provider.isValid())
        self.assertEqual(provider.dataSourceUri(), correct_uri)

        # Test table without geom
        provider = DuckdbProvider(uri=f"path={db_path} table=table_no_geom")
        self.assertFalse(provider.isValid())

    def test_wrong_uri(self) -> None:
        provider = DuckdbProvider(uri="zidane")
        self.assertFalse(provider.isValid())

    def test_geom_mapping(self) -> None:
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

        # MultiPolygon
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=test_multi")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.MultiPolygon)

        # Geom with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

        # Table without geom
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=tabke_no_geom")
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_extent(self) -> None:
        # Test linestring layer
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=highway")
        self.assertIsInstance(provider.extent(), QgsRectangle)
        self.assertEqual(
            provider.extent(),
            QgsRectangle(
                -0.7579893469810486,
                48.084476470947266,
                -0.7552331686019897,
                48.08263397216797,
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

    def test_fields(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(0).name(), "id")
        self.assertEqual(provider.fields().field(0).type(), 2)

        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=test_multi")
        self.assertIsInstance(provider.fields(), QgsFields)
        fields = provider.fields()
        self.assertEqual(fields[0].name(), "id")
        self.assertEqual(fields[0].type(), QVariant.Int)
        self.assertEqual(fields[1].type(), QVariant.Int)
        self.assertEqual(fields[2].type(), QVariant.String)
        self.assertEqual(fields[3].type(), QVariant.Double)
        self.assertEqual(fields[4].type(), QVariant.Bool)

        # Fields with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.fields().count(), 0)

    def test_get_geometry_column(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertEqual(provider.get_geometry_column(), "geom")

    def test_table_without_geom_column(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=table_no_geom")
        self.assertEqual(provider.get_geometry_column(), None)
        self.assertEqual(
            provider.extent().asWktPolygon(), "POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_featureCount(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")
        provider = DuckdbProvider(uri=f"path={db_path} table=cities")
        self.assertEqual(provider.featureCount(), 3)

        # Count with wrong uri
        provider = DuckdbProvider(uri="path=wrong/uri/biuycdzohd.db table=zidane")
        self.assertEqual(provider.featureCount(), 0)

    def test_get_features(self) -> None:
        db_path = Path(__file__).parent.joinpath("data/base_test.db")

        vl = QgsVectorLayer(f"path={db_path} table=cities", "test", "duckdb")
        self.assertTrue(vl.isValid())

        features = vl.getFeatures()

        count_feature = 0
        for feature in features:
            count_feature += 1
            self.assertEqual(feature.geometry().wkbType(), QgsWkbTypes.Point)
            list_type_field = []
            for field in feature.fields():
                list_type_field.append(field.type())
            self.assertEqual(list_type_field[0], QVariant.Int)
            self.assertEqual(list_type_field[1], QVariant.String)

        self.assertEqual(count_feature, 3)


if __name__ == "__main__":
    unittest.main()
