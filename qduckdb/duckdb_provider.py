import weakref
from pathlib import Path

import duckdb
from qgis.core import (
    Qgis,
    QgsAbstractFeatureIterator,
    QgsAbstractFeatureSource,
    QgsCoordinateReferenceSystem,
    QgsDataProvider,
    QgsField,
    QgsFields,
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

        geometryColumns = self.get_geometry_column()
        if not geometryColumns:
            return
        else:
            self._column_geom = geometryColumns[0]

        self._provider_options = providerOptions
        self._flags = flags
        self._is_valid = True
        weakref.finalize(self, self.disconnect)

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

    def disconnect(self):
        """Disconnects the database"""
        self._con.close()

    def isValid(self):
        return self._is_valid

    def connect_database(self):
        """Connects the database and loads the spatial extension"""
        self._con = duckdb.connect(self._path)
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
        return self._con.sql(
            "select column_name from information_schema.columns "
            f"WHERE table_name = '{self._table}' AND data_type = 'GEOMETRY'"
        ).fetchone()

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

    def dataSourceUri(self):
        return self._uri

    def crs(self):
        # Duckdb does not currently allow you to provide a crs, the user will have to
        # indicate the crs.
        return QgsCoordinateReferenceSystem()

    def featureSource(self):
        return DuckDBFeatureSource(self)

    def storageType(self):
        return "DuckDB local database"

    def uniqueValues(self, fieldIndex):
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


class DuckDBFeatureIterator(QgsAbstractFeatureIterator):
    pass


class DuckDBFeatureSource(QgsAbstractFeatureSource):
    pass
