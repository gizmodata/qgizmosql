from qgis.core import QgsWkbTypes
from qgis.PyQt.QtCore import QVariant

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
