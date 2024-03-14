from __future__ import annotations

import weakref

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsDataProvider,
    QgsFeature,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsWkbTypes,
)

from qduckdb.provider import duckdb_feature_iterator, duckdb_feature_source
from qduckdb.provider.mappings import (
    mapping_duckdb_qgis_geometry,
    mapping_duckdb_qgis_type,
)
from qduckdb.toolbelt.log_handler import PlgLogger

# conditional imports
try:
    import duckdb

    from qduckdb.provider.duckdb_wrapper import DuckDbTools

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

    from qduckdb.provider.duckdb_wrapper import DuckDbTools

    PlgLogger.log(
        message=f"Dependencies loaded from embedded external libs: {duckdb.__version__=}"
    )


class DuckdbProvider(QgsVectorDataProvider):
    def __init__(
        self,
        uri="",
        # uri_model = path=/home/path/my_db.db table=the_table
        providerOptions=QgsDataProvider.ProviderOptions(),
        flags=QgsDataProvider.ReadFlags(),
    ):
        super().__init__(uri)

        self.ddb_wrapper = DuckDbTools(auto_setup_spatial=True)

        self._is_valid = False
        self._uri = uri
        self._wkb_type = None
        self._extent = None
        self._column_geom = None
        self._fields = None
        self._feature_count = None
        self._primary_key = None
        self._is_custom_SQL = False
        try:
            self._path, self._table, self._epsg, self._sql = self.ddb_wrapper.parse_uri(
                uri
            )

        except (FileNotFoundError, ValueError) as exc:
            self._is_valid = False
            PlgLogger.log(message=exc)
            return

        if self._epsg:
            self._crs = QgsCoordinateReferenceSystem.fromEpsgId(int(self._epsg))
        else:
            self._crs = QgsCoordinateReferenceSystem()

        self.connect_database()

        if self._sql and not self._table:
            self._from_clause = f"({self._sql})"
        else:
            self._from_clause = self._table

        self.get_geometry_column()
        if not self._column_geom:
            return

        self._provider_options = providerOptions
        self._flags = flags
        self._is_valid = True
        weakref.finalize(self, self.disconnect_database)

    @classmethod
    def providerKey(cls) -> str:
        """Returns the memory provider key"""
        return "duckdb"

    @classmethod
    def description(cls) -> str:
        """Returns the memory provider description"""
        return "DuckDB"

    @classmethod
    def createProvider(cls, uri, providerOptions, flags=QgsDataProvider.ReadFlags()):
        return DuckdbProvider(uri, providerOptions, flags)

    def capabilities(self) -> QgsVectorDataProvider.Capabilities:
        return (
            QgsVectorDataProvider.CreateSpatialIndex | QgsVectorDataProvider.SelectAtId
        )

    def featureCount(self) -> int:
        """returns the number of entities in the table"""
        if not self._feature_count:
            if not self._is_valid:
                self._feature_count = 0
            else:
                self._feature_count = self._con.sql(
                    f"select count(*) from {self._from_clause}"
                ).fetchone()[0]

        return self._feature_count

    def disconnect_database(self):
        """Disconnects the database"""
        if self._con and self.isValid():
            self._con.close()
            self._con = None

    def name(self) -> str:
        """Return the name of provider

        :return: Name of provider
        :rtype: str
        """
        return self.providerKey()

    def isValid(self) -> bool:
        return self._is_valid

    def connect_database(self):
        """Connects the database and loads the spatial extension"""
        self._con = self.ddb_wrapper.connect(read_only=True, requires_spatial=True)

    def wkbType(self) -> QgsWkbTypes:
        """Detects the geometry type of the table, converts and return it to
        QgsWkbTypes.
        """
        if not self._wkb_type:
            if not self._is_valid:
                self._wkb_type = QgsWkbTypes.Unknown
            else:
                str_geom_duckdb = self._con.sql(
                    f"select st_geometrytype({self._column_geom}) from {self._from_clause}"
                ).fetchone()[0]

                if str_geom_duckdb in mapping_duckdb_qgis_geometry:
                    geometry_type = mapping_duckdb_qgis_geometry[str_geom_duckdb]
                else:
                    PlgLogger.log(
                        self.tr(
                            "Geometry type {} not supported".format(str_geom_duckdb)
                        ),
                        log_level=2,
                        duration=15,
                        push=True,
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
                PlgLogger.log(
                    message="Using empty extent because geometry is not valid",
                    log_level=4,
                )
            else:
                extent_bounds = self._con.sql(
                    query=f"select min(st_xmin({self._column_geom})), "
                    f"min(st_ymin({self._column_geom})), "
                    f"max(st_xmax({self._column_geom})), "
                    f"max(st_ymax({self._column_geom})) "
                    f"from {self._from_clause}"
                ).fetchone()

                self._extent = QgsRectangle(*extent_bounds)

                PlgLogger.log(
                    message="Extent calculated for {}: "
                    "xmin={}, xmax={}, ymin={}, ymax={}".format(
                        self._table, *extent_bounds
                    ),
                    log_level=4,
                )

        return self._extent

    def updateExtents(self) -> None:
        """Update extent"""
        return self._extent.setMinimal()

    def get_geometry_column(self) -> str:
        """Returns the name of the geometry column"""
        if not self._column_geom:
            if not self._sql:
                cols = self._con.sql(
                    "SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{self._table}' AND data_type = 'GEOMETRY'"
                ).fetchone()
                if cols:
                    self._column_geom = cols[0]
            else:
                description = self._con.sql(self._sql).description
                # Exemple : description = [('id', 'NUMBER'),('name', 'STRING'),('geom', 'BINARY')]
                for data in description:
                    if data[1] == "BINARY":
                        self._column_geom = data[0]
                        break

            if not self._column_geom:
                PlgLogger.log(
                    message=self.tr(
                        "The table does not contain any geometry columns, so the table cannot be displayed."
                    ),
                    log_level=2,
                    push=True,
                    duration=10,
                )

        return self._column_geom

    def primary_key(self) -> int:
        if not self._primary_key:
            if not self._sql:
                res = self._con.sql(
                    "SELECT constraint_column_indexes FROM duckdb_constraints() "
                    f"WHERE table_name='{self.get_table()}' "
                    "AND constraint_type = 'PRIMARY KEY';"
                ).fetchone()

                if res:
                    self._primary_key = res[0][0]
                else:
                    self._primary_key = -1
            else:
                self._primary_key = -1

        return self._primary_key

    def fields(self) -> QgsFields:
        """Detects field name and type. Converts the type into a QVariant, and returns a
        QgsFields containing QgsFields.
        """
        if not self._fields:
            self._fields = QgsFields()
            if self._is_valid:
                if not self._sql:
                    field_info = self._con.sql(
                        "select column_name, data_type from "
                        f"information_schema.columns WHERE table_name = '{self._table}' AND "
                        " data_type not in ('GEOMETRY', 'WKB_BLOB')"
                    ).fetchall()
                else:
                    field_info = []
                    description = self._con.sql(self._sql).description
                    for data in description:
                        if data[1] not in ["GEOMETRY", "BINARY", "WKB_BLOB"]:
                            field_info.append((data[0], data[1]))

                for field_name, field_type in field_info:
                    qgs_field = QgsField(
                        field_name, mapping_duckdb_qgis_type[field_type]
                    )
                    self._fields.append(qgs_field)

        return self._fields

    def dataSourceUri(self, expandAuthConfig=False):
        """Returns the data source specification: database path and
        table name.

        :param bool expandAuthConfig: expand credentials (unused)
        :returns: the data source uri
        """
        return self._uri

    def crs(self):
        return self._crs

    def featureSource(self):
        return duckdb_feature_source.DuckdbFeatureSource(self)

    def storageType(self):
        return "DuckDB local database"

    def get_table(self) -> str:
        """Get the table name

        :return: table name
        :rtype: str
        """
        if self._sql:
            return ""
        else:
            return self._table

    def uniqueValues(self, fieldIndex) -> set:
        """Returns the unique values of a field

        :param fieldIndex: Index of field
        :type fieldIndex: int
        """
        column_name = self.fields().field(fieldIndex).name()
        results = set()
        for elem in self._con.sql(
            f"select distinct {column_name} from {self._from_clause};"
        ).fetchall():
            results.add(elem[0])

        return results

    def getFeatures(self, request=QgsFeatureRequest()) -> QgsFeature:
        """Return next feature"""
        return QgsFeatureIterator(
            duckdb_feature_iterator.DuckdbFeatureIterator(
                duckdb_feature_source.DuckdbFeatureSource(self), request
            )
        )

    def con(self) -> duckdb.DuckDBPyConnection | None:
        """Start DuckDB cursor"""
        if not self._is_valid:
            return None

        return self._con.cursor()

    def subsetString(self) -> str:
        return ""

    def setSubsetString(self, subsetString: str) -> bool:
        return False

    def supportsSubsetString(self) -> bool:
        # FIXME: the provider does not handle subsets at the moment
        return False
