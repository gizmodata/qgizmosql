from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QMetaType, QVariant

mapping_duckdb_qgis_geometry = {
    "LINESTRING": QgsWkbTypes.Type.LineString,
    "MULTILINESTRING": QgsWkbTypes.Type.MultiLineString,
    "MULTIPOINT": QgsWkbTypes.Type.MultiPoint,
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

# Use to keep QGIS 3.34 compatibility
deprecate_mapping_duckdb_qgis_type = {
    "BIGINT": QVariant.Int,
    "BOOLEAN": QVariant.Bool,
    "DATE": QVariant.Date,
    "TIME": QVariant.Time,
    "DOUBLE": QVariant.Double,
    "FLOAT": QVariant.Double,
    "INTEGER": QVariant.Int,
    "TIMESTAMP": QVariant.DateTime,
    "VARCHAR": QVariant.String,
    # Type used for custom sql when table is not created
    # Not difference betwenn float and integer so all the numeric field are NUMBER
    "NUMBER": QVariant.Double,
    "STRING": QVariant.String,
    "Date": QVariant.Date,
    "bool": QVariant.Bool,
    "JSON": QVariant.String,
    "DATETIME": QVariant.DateTime,
}
