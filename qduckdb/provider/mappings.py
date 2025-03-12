from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QMetaType

mapping_duckdb_qgis_geometry = {
    "LINESTRING": QgsWkbTypes.Type.LineString,
    "MULTILINESTRING": QgsWkbTypes.Type.MultiLineString,
    "MULTIPOINT": QgsWkbTypes.Type.MultiPolygon,
    "MULTIPOLYGON": QgsWkbTypes.Type.MultiPolygon,
    "POINT": QgsWkbTypes.Type.Point,
    "POLYGON": QgsWkbTypes.Type.Polygon,
    # ...
}

mapping_duckdb_qgis_type = {
    "BIGINT": QMetaType.Type.Int,
    "BOOLEAN": QMetaType.Type.Bool,
    "DATE": QMetaType.Type.QDate,
    "TIME": QMetaType.Type.QTime,
    "DOUBLE": QMetaType.Type.Double,
    "FLOAT": QMetaType.Type.Double,
    "INTEGER": QMetaType.Type.Int,
    "TIMESTAMP": QMetaType.Type.QDateTime,
    "VARCHAR": QMetaType.Type.QString,
    # Type used for custom sql when table is not created
    # No difference between float and integer so all numeric fields are NUMBER
    "NUMBER": QMetaType.Type.Double,
    "STRING": QMetaType.Type.QString,
    "Date": QMetaType.Type.QDate,
    "bool": QMetaType.Type.Bool,
    "JSON": QMetaType.Type.QString,
    "DATETIME": QMetaType.Type.QDateTime,
}
