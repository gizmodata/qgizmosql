from __future__ import annotations

import weakref
from pathlib import Path

import duckdb
from qgis.core import (
    Qgis,
    QgsAbstractFeatureIterator,
    QgsAbstractFeatureSource,
    QgsCoordinateReferenceSystem,
    QgsDataProvider,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsWkbTypes,
)
from qgis.PyQt.Qt import QVariant

from qduckdb.toolbelt.log_handler import PlgLogger

mapping_duckdb_qgis_geometry = {
    "POINT": QgsWkbTypes.Point,
    "LINESTRING": QgsWkbTypes.LineString,
    "POLYGON": QgsWkbTypes.Polygon,
    # ...
}

mapping_duckdb_qgis_type = {
    "BIGINT": QVariant.Int,
    "INTEGER": QVariant.Int,
    "VARCHAR": QVariant.String,
    "DOUBLE": QVariant.Double,
}


class DuckdbProvider(QgsVectorDataProvider):
    def __init__(
        self,
        uri="",
        # uri_model = path=/home/path/my_db.db table=the_table
        providerOptions=QgsDataProvider.ProviderOptions(),
        flags=QgsDataProvider.ReadFlags(),
    ):
        super().__init__(uri)
        self._is_valid = False
        self._uri = uri
        self._wkb_type = None
        self._extent = None
        self._column_geom = None
        self._fields = None
        self._feature_count = None
        self._path, self._table = self._parse_uri(uri)
        if not self._path or not self._table:
            PlgLogger.log(
                'Wrong uri. Excepted : "path=/home/path/my_db table=the_table"',
                log_level=Qgis.Critical,
                duration=10,
                push=False,
            )
            return

        if not Path(self._path).exists():
            PlgLogger.log(
                "Databse not exists, wrong path",
                log_level=Qgis.Critical,
                duration=10,
                push=False,
            )
            return

        self.connect_database()
        self.get_geometry_column()
        if not self._column_geom:
            return

        self._provider_options = providerOptions
        self._flags = flags
        self._is_valid = True
        weakref.finalize(self, self.disconnect_database)

    @classmethod
    def providerKey(cls):
        """Returns the memory provider key"""
        return "duckdb"

    @classmethod
    def description(cls):
        """Returns the memory provider description"""
        return "DuckDB"

    @classmethod
    def createProvider(cls, uri, providerOptions, flags=QgsDataProvider.ReadFlags()):
        return DuckdbProvider(uri, providerOptions, flags)

    def capabilities(self) -> QgsVectorDataProvider.Capabilities:
        return (
            QgsVectorDataProvider.CreateSpatialIndex | QgsVectorDataProvider.SelectAtId
        )

    def featureCount(self):
        """returns the number of entities in the table"""
        if not self._feature_count:
            if not self._is_valid:
                self._feature_count = 0
            else:
                self._feature_count = self._con.sql(
                    "select count(*) from cities"
                ).fetchone()[0]

        return self._feature_count

    def disconnect_database(self):
        """Disconnects the database"""
        if self._con:
            self._con.close()
            self._con = None

    def name(self) -> str:
        return self.providerKey()

    def isValid(self):
        return self._is_valid

    def connect_database(self):
        """Connects the database and loads the spatial extension"""
        self._con = duckdb.connect(self._path, read_only=True)
        self._con.sql("LOAD spatial ;")

    def wkbType(self) -> QgsWkbTypes:
        """Detects the geometry type of the table, converts and return it to QgsWkbTypes"""
        if not self._wkb_type:
            if not self._is_valid:
                self._wkb_type = QgsWkbTypes.Unknown
            else:
                str_geom_duckdb = self._con.sql(
                    f"select st_geometrytype({self._column_geom}) from {self._table}"
                ).fetchone()[0]

                if str_geom_duckdb in mapping_duckdb_qgis_geometry:
                    geometry_type = mapping_duckdb_qgis_geometry[str_geom_duckdb]
                else:
                    PlgLogger.log(
                        f"Geometry type {str_geom_duckdb} not supported",
                        log_level=Qgis.Critical,
                        duration=10,
                        push=False,
                    )
                    self._wkb_type = QgsWkbTypes.Unknown
                    return self._wkb_type

                self._wkb_type = geometry_type

        return self._wkb_type

    def extent(self) -> QgsRectangle:
        """Calculates the extent of the bend and returns a QgsRectangle"""
        # TODO : Replace by ST_Extent when the function is implemented
        if not self._extent:
            if not self._is_valid:
                self._extent = QgsRectangle()
            else:
                list_x = []
                list_y = []

                str_geom_duckdb = self._con.sql(
                    f"select st_geometrytype({self._column_geom}) from {self._table}"
                ).fetchone()[0]

                geom_wkt = self._con.sql(
                    f"select st_astext({self._column_geom}) from {self._table}"
                ).fetchall()

                for tuples in geom_wkt:
                    for elem in tuples[0].split(", "):
                        elem = elem.replace(f"{str_geom_duckdb} (", "")
                        elem = elem.replace("(", "")
                        elem = elem.replace(")", "")
                        list_x.append(float(elem.split(" ")[0]))
                        list_y.append(float(elem.split(" ")[1]))

                self._extent = QgsRectangle(
                    min(list_x), min(list_y), max(list_x), max(list_y)
                )

        return self._extent

    def updateExtents(self):
        """Update extent"""
        return self._extent.setMinimal()

    def get_geometry_column(self) -> str:
        """Returns the name of the geometry column"""
        if not self._column_geom:
            cols = self._con.sql(
                "SELECT column_name FROM information_schema.columns "
                f"WHERE table_name = '{self._table}' AND data_type = 'GEOMETRY'"
            ).fetchone()
            if cols:
                self._column_geom = cols[0]

        return self._column_geom

    def fields(self) -> QgsFields:
        """Detects field name and type. Converts the type into a QVariant, and returns a"""
        """ QgsFields containing Qgs Fields."""
        if not self._fields:
            self._fields = QgsFields()
            if self._is_valid:
                field_info = self._con.sql(
                    "select column_name, data_type from "
                    f"information_schema.columns WHERE table_name = '{self._table}' AND "
                    " data_type not in ('GEOMETRY', 'WKB_BLOB')"
                ).fetchall()

                for field_name, field_type in field_info:
                    qgs_field = QgsField(
                        field_name, mapping_duckdb_qgis_type[field_type]
                    )
                    self._fields.append(qgs_field)

        return self._fields

    @staticmethod
    def _parse_uri(uri: str) -> [str | None, str | None]:
        """Parse the uri and return the path to the database and the name of the table"""
        path = None
        table = None
        for variable in uri.split(" "):
            try:
                key, value = variable.split("=")
                if key == "path":
                    path = value
                elif key == "table":
                    table = value
            except ValueError:
                pass

        return path, table

    def dataSourceUri(self, expandAuthConfig=False):
        """Returns the data source specification: database path and
        table name.

        :param bool expandAuthConfig: expand credentials (unused)
        :returns: the data source uri
        """
        return self._uri

    def crs(self):
        # Duckdb does not currently allow you to provide a crs, the user will have to
        # indicate the crs.
        return QgsCoordinateReferenceSystem()

    def featureSource(self):
        return DuckdbFeatureSource(self)

    def storageType(self):
        return "DuckDB local database"

    @property
    def get_table(self) -> str:
        """Get the table name

        :return: table name
        :rtype: str
        """
        return self._table

    def uniqueValues(self, fieldIndex) -> list:
        """Returns the unique values of a field

        :param fieldIndex: Index of field
        :type fieldIndex: int
        """
        column_name = self.fields().field(fieldIndex).name()
        results = set()
        for elem in self._con.sql(
            f"select distinct {column_name} from {self._table};"
        ).fetchall():
            results.add(elem[0])

        return results

    def getFeatures(self, request=QgsFeatureRequest()) -> QgsFeature:
        """Return next feature"""
        return QgsFeatureIterator(
            DuckdbFeatureIterator(DuckdbFeatureSource(self), request)
        )

    @property
    def con(self) -> duckdb.DuckDBPyConnection:
        """Start DuckDB cursor"""
        if not self._is_valid:
            return None

        return self._con.cursor()


class DuckdbFeatureSource(QgsAbstractFeatureSource):
    def __init__(self, provider):
        """Constructor"""
        super().__init__()
        self._provider = provider

        self._expression_context = QgsExpressionContext()
        self._expression_context.appendScope(QgsExpressionContextUtils.globalScope())
        self._expression_context.appendScope(
            QgsExpressionContextUtils.projectScope(QgsProject.instance())
        )
        self._expression_context.setFields(self._provider.fields())
        if self._provider.subsetString():
            self._subset_expression = QgsExpression(self._provider.subsetString())
            self._subset_expression.prepare(self._expression_context)
        else:
            self._subset_expression = None

    def getFeatures(self, request) -> QgsFeatureIterator:
        return QgsFeatureIterator(DuckdbFeatureIterator(self, request))

    def get_provider(self):
        return self._provider


class DuckdbFeatureIterator(QgsAbstractFeatureIterator):
    def __init__(self, source: DuckdbFeatureSource, request):
        """Constructor"""
        # TODO Request has not yet been implemented
        super().__init__(request)
        self._provider = source.get_provider()

        if not self._provider.isValid():
            return

        table = self._provider.get_table
        geom_column = self._provider.get_geometry_column()

        list_field_names = []
        for field in self._provider.fields():
            list_field_names.append(field.name())

        fields_name_for_query = ", ".join(list_field_names)
        self.index_geom_column = len(list_field_names)

        self._result = self._provider.con.execute(
            f"select {fields_name_for_query}, st_astext({geom_column}) from {table}"
        )
        self._index = 0

    def fetchFeature(self, f: QgsFeature) -> bool:
        """fetch next feature, return true on success

        :param f: Next feature
        :type f: QgsFeature
        :return: True if success
        :rtype: bool
        """
        next_result = self._result.fetchone()

        if not next_result or not self._provider.isValid():
            f.setValid(False)
            return False

        self._index += 1
        f.setFields(self._provider.fields())
        f.setValid(self._provider.isValid())
        geometry = QgsGeometry.fromWkt(next_result[self.index_geom_column])
        f.setGeometry(geometry)
        f.setId(self._index)

        for enum in range(self.index_geom_column):
            f.setAttribute(enum, next_result[enum])

        return True

    def __iter__(self) -> DuckdbFeatureIterator:
        """Returns self as an iterator object"""
        self._index = 0
        return self

    def __next__(self) -> QgsFeature:
        """Returns the next value till current is lower than high"""
        f = QgsFeature()
        if not self.nextFeature(f):
            raise StopIteration
        else:
            return f

    def rewind(self) -> bool:
        """reset the iterator to the starting position"""
        # virtual bool rewind() = 0;
        if self._index < 0:
            return False
        self._index = 0
        return True

    def close(self) -> bool:
        """end of iterating: free the resources / lock"""
        # virtual bool close() = 0;
        self._index = -1
        return True
