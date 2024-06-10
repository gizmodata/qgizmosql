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

from .utilities import compare_rectangles, register_provider_if_necessary

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
        cls.wrong_db_path = 'path="wrong/path/zidane.db"'

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
        correct_uri = f'path="{self.db_path_test}";table="cities";epsg="4326"'
        provider = DuckdbProvider(uri=correct_uri)
        self.assertTrue(provider.isValid())
        self.assertEqual(provider.dataSourceUri(), correct_uri)

        # Test table without geom
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="table_no_geom";epsg="4326"'
        )
        self.assertFalse(provider.isValid())

    def test_wrong_uri(self) -> None:
        provider = DuckdbProvider(uri='path="wrong/path/zidane.db"')
        self.assertFalse(provider.isValid())

    def test_geom_mapping(self) -> None:
        # Point
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Point)
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from cities limit 1";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Point)

        # Linestring
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="highway";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.LineString)
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from highway limit 1";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.LineString)

        # Polygon
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="building";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Polygon)
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from building limit 1";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Polygon)

        # MultiPolygon
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="test_multi";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.MultiPolygon)

        # Geom with wrong uri
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="zidane";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

        # Table without geom
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="table_no_geom";epsg="4326"'
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_extent(self) -> None:
        # Test linestring layer
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="highway";epsg="4326"'
        )
        self.assertIsInstance(provider.extent(), QgsRectangle)
        expected_extent = QgsRectangle(-0.75799, 48.08263, -0.75523, 48.08447)
        self.assertTrue(compare_rectangles(provider.extent(), expected_extent))

        # Test point layer
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertIsInstance(provider.extent(), QgsRectangle)
        expected_extent = QgsRectangle(2.15899, 41.38879, 7.68682, 45.07049)
        self.assertTrue(compare_rectangles(provider.extent(), expected_extent))

        # Extent with wrong uri
        provider = DuckdbProvider(uri='path="wrong/path/zidane.db"')
        self.assertEqual(
            provider.extent().asWktPolygon(), QgsRectangle().asWktPolygon()
        )

    def test_fields(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(0).name(), "id")
        self.assertEqual(provider.fields().field(0).type(), QVariant.Int)

        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="test_multi";epsg="4326"'
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        fields = provider.fields()
        self.assertEqual(fields[0].name(), "id")
        self.assertEqual(fields[0].type(), QVariant.Int)
        self.assertEqual(fields[1].type(), QVariant.Int)
        self.assertEqual(fields[2].type(), QVariant.String)
        self.assertEqual(fields[3].type(), QVariant.Double)
        self.assertEqual(fields[4].type(), QVariant.Bool)

        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select name, geom from cities limit 1";epsg="4326"'
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        fields = provider.fields()
        self.assertEqual(fields[0].name(), "name")
        self.assertEqual(fields[0].type(), QVariant.String)

        # Fields with wrong uri
        provider = DuckdbProvider(uri='path="wrong/uri/biuycdzohd.db";table="zidane"')
        self.assertEqual(provider.fields().count(), 0)

    def test_get_geometry_column(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(provider.get_geometry_column(), "geom")

        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from cities limit 2";epsg="4326"'
        )
        self.assertEqual(provider.get_geometry_column(), "geom")

    def test_table_without_geom_column(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="table_no_geom";epsg="4326"'
        )
        self.assertEqual(provider.get_geometry_column(), None)
        self.assertEqual(
            provider.extent().asWktPolygon(), QgsRectangle().asWktPolygon()
        )
        self.assertEqual(provider.wkbType(), QgsWkbTypes.Unknown)

    def test_featureCount(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(provider.featureCount(), 3)

        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from cities limit 2";epsg="4326"'
        )
        self.assertEqual(provider.featureCount(), 2)

        # Count with wrong uri
        provider = DuckdbProvider(uri='path="wrong/uri/biuycdzohd.db";table="zidane"')
        self.assertEqual(provider.featureCount(), 0)

    def test_unique_values(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(len(provider.fields()), 2)

        values = provider.uniqueValues(1)
        self.assertEqual(values, {"Barcelona", "Marseille", "Turin"})

        values = provider.uniqueValues(1, 1)
        self.assertEqual(values, {"Barcelona"})

    def test_get_features(self) -> None:
        v1 = QgsVectorLayer(
            f'path="{self.db_path_test}";table="cities";epsg="4326"', "test", "duckdb"
        )
        v2 = QgsVectorLayer(
            f'path="{self.db_path_test}";sql="select id::int as id, name, geom from cities limit 3";epsg="4326"',
            "test",
            "duckdb",
        )
        for v in [v1, v2]:
            self.assertTrue(v.isValid())

            features = v.getFeatures()

            count_feature = 0
            for feature in features:
                count_feature += 1
                self.assertEqual(feature.geometry().wkbType(), QgsWkbTypes.Point)
                list_type_field = []
                for field in feature.fields():
                    list_type_field.append(field.type())
                if v == v1:
                    self.assertEqual(list_type_field[0], QVariant.Int)
                if v == v2:
                    self.assertEqual(list_type_field[0], QVariant.Double)
                self.assertEqual(list_type_field[1], QVariant.String)
                self.assertEqual(feature.id(), count_feature)

            self.assertEqual(count_feature, 3)

    def test_rowid_in_sql_subquery(self) -> None:
        layer_without_rowid = QgsVectorLayer(
            f'path="{self.db_path_test}";sql="select name, geom from cities limit 3";epsg="4326"',
            "test_without_id",
            "duckdb",
        )
        self.assertTrue(layer_without_rowid.isValid())

        layer_with_rowid = QgsVectorLayer(
            f'path="{self.db_path_test}";sql="select rowid, name, geom from cities limit 3";epsg="4326"',
            "test_without_id",
            "duckdb",
        )
        self.assertTrue(layer_with_rowid.isValid())

        count_feature = 0
        for feature_without_rowid, feature_with_rowid in zip(
            layer_without_rowid.getFeatures(), layer_with_rowid.getFeatures()
        ):
            count_feature += 1
            self.assertEqual(feature_without_rowid.id(), count_feature)
            self.assertEqual(feature_without_rowid.id(), feature_with_rowid.id())

            self.assertEqual(feature_with_rowid.fields().field(0).name(), "name")
            self.assertEqual(feature_without_rowid.fields().field(0).name(), "name")
            self.assertEqual(
                feature_without_rowid.attributes(), feature_with_rowid.attributes()
            )

            self.assertEqual(feature_without_rowid.attributeCount(), 1)
            self.assertEqual(feature_with_rowid.attributeCount(), 1)

        self.assertEqual(count_feature, 3)

    def test_attributes(self):
        # No sql subquery, it should return all the fields
        vector_layer1 = QgsVectorLayer(
            f'path="{self.db_path_test}";table="cities";epsg="4326"', "test", "duckdb"
        )

        # check fields
        fields = vector_layer1.fields()
        self.assertTrue(len(fields), 2)
        self.assertEqual(fields.field(0).name(), "id")
        self.assertEqual(fields.field(0).type(), QVariant.Int)
        self.assertEqual(fields.field(1).name(), "name")
        self.assertEqual(fields.field(1).type(), QVariant.String)

        expected_attributes = [
            [2995469, "Marseille"],
            [3128760, "Barcelona"],
            [3165524, "Turin"],
        ]
        # check attributes
        for idx, feature in enumerate(vector_layer1.getFeatures()):
            self.assertEqual(feature.attributes(), expected_attributes[idx])

        # A sql subquery, it should only return the fields from the subquery
        vector_layer2 = QgsVectorLayer(
            f'path="{self.db_path_test}";sql="select name, geom from cities limit 3";epsg="4326"',
            "test",
            "duckdb",
        )

        # check fields
        fields = vector_layer2.fields()
        self.assertTrue(len(fields), 1)
        self.assertEqual(fields.field(0).name(), "name")
        self.assertEqual(fields.field(0).type(), QVariant.String)

        expected_attributes = [
            ["Marseille"],
            ["Barcelona"],
            ["Turin"],
        ]
        # check attributes
        for idx, feature in enumerate(vector_layer2.getFeatures()):
            self.assertEqual(feature.attributes(), expected_attributes[idx])

    def test_attributes_subset_of_attributes(self):
        """
        Check that the iterator works when a request has set
        the SubsetOfAttributes flag
        """
        vector_layer = QgsVectorLayer(
            f'path="{self.db_path_test}";table="cities";epsg="4326"', "test", "duckdb"
        )

        # check fields
        fields = vector_layer.fields()
        self.assertTrue(len(fields), 2)
        self.assertEqual(fields.field(0).name(), "id")
        self.assertEqual(fields.field(0).type(), QVariant.Int)
        self.assertEqual(fields.field(1).name(), "name")
        self.assertEqual(fields.field(1).type(), QVariant.String)

        # no subset set
        # all the attributes are returned
        request = QgsFeatureRequest()
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [2995469, "Marseille"])

        # set subset by idx
        # only the selected ids are set - others are None
        request.setSubsetOfAttributes([1])
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [None, "Marseille"])

        request.setSubsetOfAttributes([0])
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [2995469, None])

        request.setSubsetOfAttributes([0, 1])
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [2995469, "Marseille"])

        request.setSubsetOfAttributes([])
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [None, None])

        # set subset by field name
        # only the selected names are set - others are None
        request = QgsFeatureRequest()
        request.setSubsetOfAttributes(["id"], fields)
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [2995469, None])

        request.setSubsetOfAttributes(["name"], fields)
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [None, "Marseille"])

        request.setSubsetOfAttributes(["id", "name"], fields)
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(attributes, [2995469, "Marseille"])

    def test_crs(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(provider.crs().authid(), "EPSG:4326")
        self.assertIsInstance(provider.crs(), QgsCoordinateReferenceSystem)

    def test_primary_key(self) -> None:
        # table does not have a primary key
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertEqual(provider.primary_key(), -1)
        features = list(provider.getFeatures())
        self.assertEqual(len(features), 3)
        self.assertEqual(features[0].id(), 1)
        self.assertEqual(features[1].id(), 2)
        self.assertEqual(features[2].id(), 3)

        # table has a primary key
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="table_with_primary_key";epsg="4326"'
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
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        list_point = [
            "Point (5.38107000000000024 43.29695000000000249)",
            "Point (2.15899000000000019 41.38879000000000019)",
            "Point (7.68681999999999999 45.0704899999999995)",
        ]

        feats = provider.getFeatures()
        for i, feat in enumerate(feats):
            self.assertEqual(feat.geometry().asWkt(), list_point[i])

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
            geom = QgsGeometry.fromWkt(list_point[i])
            geom.transform(transform)
            self.assertNotEqual(feat.geometry().asWkt(), list_point[i])
            self.assertEqual(feat.geometry().asWkt(), geom.asWkt())

    def test_filter_rect(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
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

    def test_filter_expression(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )

        request = QgsFeatureRequest()
        values = [feat["name"] for feat in provider.getFeatures(request)]
        self.assertEqual(values, ["Marseille", "Barcelona", "Turin"])

        request.setFilterExpression("name ILIKE 'Barcelona'")
        values = [feat["name"] for feat in provider.getFeatures(request)]
        self.assertEqual(values, ["Barcelona"])

        request.setFilterExpression("name not ILIKE 'Barcelona'")
        values = [feat["name"] for feat in provider.getFeatures(request)]
        self.assertEqual(values, ["Marseille", "Turin"])

    def test_filter_fid_and_fids(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
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
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
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

    def test_sql_query(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";sql="select * from cities limit 1";epsg="4326"'
        )

        self.assertTrue(provider._sql, "select * from cities limit 1")

    def test_no_geometry_flag(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )

        # With NoGeometry flag
        req = QgsFeatureRequest()
        req.setFlags(QgsFeatureRequest.Flag.NoGeometry)
        self.assertTrue(req.flags() & QgsFeatureRequest.Flag.NoGeometry)
        features = list(provider.getFeatures(req))
        self.assertTrue(len(features) > 0)
        self.assertTrue(features[0].isValid())
        self.assertFalse(features[0].hasGeometry())

        # Without NoGeometry flag
        req = QgsFeatureRequest()
        self.assertFalse(req.flags() & QgsFeatureRequest.Flag.NoGeometry)
        features = list(provider.getFeatures(req))
        self.assertTrue(len(features) > 0)
        self.assertTrue(features[0].isValid())
        self.assertTrue(features[0].hasGeometry())

    def test_subset_string(self) -> None:
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";table="cities";epsg="4326"'
        )
        self.assertTrue(provider.supportsSubsetString())

        # With valid filter
        self.assertTrue(provider.setSubsetString("name='Marseille'"))
        provider.setSubsetString("name='Marseille'")
        req = QgsFeatureRequest()
        features = list(provider.getFeatures(req))
        self.assertTrue(len(features) == 1)

        # With wrong filter
        self.assertFalse(provider.setSubsetString("toto"))

    def test_fields_with_space(self) -> None:
        # Entire table
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";epsg="4326";table="table_with_column_space"'
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(1).name(), "The Name")

        # SQL Query
        provider = DuckdbProvider(
            uri=f'path="{self.db_path_test}";epsg="4326";sql="select id, "The Name", geom from table_with_column_space"'
        )
        self.assertIsInstance(provider.fields(), QgsFields)
        self.assertEqual(provider.fields().field(1).name(), "The Name")

    def test_float_type(self):
        """
        Check that FLOAT columns are converted by the provider.
        """
        vector_layer = QgsVectorLayer(
            f'path="{self.db_path_test}";table="table_with_float";epsg="4326"',
            "test",
            "duckdb",
        )

        # check fields
        fields = vector_layer.fields()
        self.assertEqual(fields.field(1).name(), "test_float")
        self.assertEqual(fields.field(1).type(), QVariant.Double)
        request = QgsFeatureRequest()
        attributes = next(vector_layer.getFeatures(request)).attributes()
        self.assertEqual(round(attributes[1], 3), 2458.254)


if __name__ == "__main__":
    unittest.main()
