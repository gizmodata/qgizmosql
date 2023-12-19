from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsFields,
    QgsGeometry,
    QgsProject,
    QgsProviderRegistry,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.Qt import QVariant
from qgis.testing import unittest

from qduckdb.provider.duckdb_provider import DuckdbProvider
from qduckdb.provider.duckdb_provider_metadata import DuckdbProviderMetadata

from .utilities import register_provider_if_necessary

db_path = Path(__file__).parent.joinpath("data/base_test.db")


class TestQDuckDBProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Run before all tests"""
        super(TestQDuckDBProvider, cls).setUpClass()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.db_path_test = (
            Path(__file__).parent.parent.joinpath("fixtures/base_test.db").as_posix()
        )
        cls.wrong_db_path = "wrong/path/zidane.db"

    def test_get_capabilities(self) -> None:
        provider = DuckdbProvider()
        self.assertEqual(
            provider.capabilities(),
            QgsVectorDataProvider.CreateSpatialIndex | QgsVectorDataProvider.SelectAtId,
        )

    def test_register_same_provider_twice(self) -> None:
        """Test that a provider cannot be registered twice"""
        registry = QgsProviderRegistry.instance()
        duckdb_metadata = DuckdbProviderMetadata()
        self.assertFalse(registry.registerProvider(duckdb_metadata))

    def test_valid(self) -> None:
        correct_uri = f"path={self.db_path_test} table=cities epsg=4326"
        provider = DuckdbProvider(uri=correct_uri)
        self.assertTrue(provider.isValid())
        self.assertEqual(provider.dataSourceUri(), correct_uri)

        # Test table without geom
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=table_no_geom epsg=4326"
        )
        self.assertFalse(provider.isValid())

    def test_wrong_uri(self) -> None:
        provider = DuckdbProvider(uri="zidane")
        self.assertFalse(provider.isValid())

    def test_geom_mapping(self) -> None:
        # Point
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Point)

        # Linestring
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=highway epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.LineString)

        # Polygon
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=building epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Polygon)

        # MultiPolygon
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=test_multi epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.MultiPolygon)

        # Geom with wrong uri
        provider = DuckdbProvider(
            uri="path=wrong/uri/biuycdzohd.db table=zidane epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

        # Table without geom
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=tabke_no_geom epsg=4326"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_extent(self) -> None:
        # Test linestring layer
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=highway epsg=4326"
        )
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
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
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
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(0).name(), "id")
        self.assertEqual(provider.fields().field(0).type(), 2)

        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=test_multi epsg=4326"
        )
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
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertEqual(provider.get_geometry_column(), "geom")

    def test_table_without_geom_column(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=table_no_geom epsg=4326"
        )
        self.assertEqual(provider.get_geometry_column(), None)
        self.assertEqual(
            provider.extent().asWktPolygon(), "POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))"
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_featureCount(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertEqual(provider.featureCount(), 3)

        # Count with wrong uri
        provider = DuckdbProvider(
            uri="path=wrong/uri/biuycdzohd.db table=zidane epsg=4326"
        )
        self.assertEqual(provider.featureCount(), 0)

    def test_get_features(self) -> None:
        vl = QgsVectorLayer(
            f"path={self.db_path_test} table=cities epsg=4326", "test", "duckdb"
        )
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
            self.assertEqual(feature.id(), count_feature)

        self.assertEqual(count_feature, 3)

    def test_crs(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertEqual(provider.crs().authid(), "EPSG:4326")
        self.assertIsInstance(provider.crs(), QgsCoordinateReferenceSystem)

    def test_primary_key(self) -> None:
        # table does not have a primary key
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        self.assertEqual(provider.primary_key(), -1)
        features = list(provider.getFeatures())
        self.assertEqual(len(features), 3)
        self.assertEqual(features[0].id(), 1)
        self.assertEqual(features[1].id(), 2)
        self.assertEqual(features[2].id(), 3)

        # table has a primary key
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=table_with_primary_key epsg=4326"
        )
        self.assertEqual(provider.primary_key(), 0)
        features = list(provider.getFeatures())
        self.assertEqual(len(features), 4)
        self.assertEqual(features[0].id(), 1)
        self.assertEqual(features[1].id(), 2)
        self.assertEqual(features[2].id(), 3)
        self.assertEqual(features[3].id(), 4)

    def test_output_crs(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        liste_point = [
            "Point (5.38107000000000024 43.29695000000000249)",
            "Point (2.15899000000000019 41.38879000000000019)",
            "Point (7.68681999999999999 45.0704899999999995)",
        ]

        feats = provider.getFeatures()
        for i, feat in enumerate(feats):
            self.assertEqual(feat.geometry().asWkt(), liste_point[i])

        request = QgsFeatureRequest()
        request.setDestinationCrs(
            QgsCoordinateReferenceSystem.fromEpsgId(3857),
            QgsProject.instance().transformContext(),
        )
        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
            QgsCoordinateReferenceSystem.fromEpsgId(3857),
            QgsProject.instance().transformContext(),
        )

        feats = provider.getFeatures(request)
        for i, feat in enumerate(feats):
            geom = QgsGeometry.fromWkt(liste_point[i])
            geom.transform(transform)
            self.assertNotEqual(feat.geometry().asWkt(), liste_point[i])
            self.assertEqual(feat.geometry().asWkt(), geom.asWkt())

    def test_filter_rect(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        request = QgsFeatureRequest()
        # All features
        request.setFilterRect(QgsRectangle(1, 40, 8, 46))
        self.assertEqual(len(list(provider.getFeatures(request))), 3)
        # Only one
        request.setFilterRect(QgsRectangle(4, 42, 6, 44))
        self.assertEqual(len(list(provider.getFeatures(request))), 1)
        # Empty
        request.setFilterRect(QgsRectangle(20, 92, 21, 93))
        self.assertEqual(len(list(provider.getFeatures(request))), 0)

    def test_subset_string(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=table_with_primary_key epsg=4326"
        )
        self.assertFalse(provider.supportsSubsetString())

    def test_filter_fid_and_fids(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )

        # Fid
        req = QgsFeatureRequest()
        req.setFilterFid(2)
        self.assertEqual(req.filterType(), req.FilterFid)
        features = list(provider.getFeatures(req))
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id(), 2)

        # Fids
        req = QgsFeatureRequest()
        req.setFilterFids([1, 2])
        self.assertEqual(req.filterType(), req.FilterFids)
        features = list(provider.getFeatures(req))
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0].id(), 1)
        self.assertEqual(features[1].id(), 2)

    def test_filter_fids_and_rect(self) -> None:
        provider = DuckdbProvider(
            uri=f"path={self.db_path_test} table=cities epsg=4326"
        )
        request = QgsFeatureRequest()

        request.setFilterFids([3])
        features = list(provider.getFeatures(request))
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id(), 3)

        # only the first city is in this extent
        # the request should not return any result
        request.setFilterRect(QgsRectangle(4, 42, 6, 44))
        features = list(provider.getFeatures(request))
        self.assertEqual(len(features), 0)

        # only the first city is returned
        request.setFilterFids([1, 2])
        features = list(provider.getFeatures(request))
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].id(), 1)

        # this extent covers the 3 cities
        # The request should retrieve city 1 and 2
        request.setFilterRect(QgsRectangle(0, 0, 50, 50))
        features = list(provider.getFeatures(request))
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0].id(), 1)
        self.assertEqual(features[1].id(), 2)


if __name__ == "__main__":
    unittest.main()
