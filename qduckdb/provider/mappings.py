from qgis.core import QgsWkbTypes
from qgis.PyQt.Qt import QVariant

mapping_duckdb_qgis_geometry = {
    "LINESTRING": QgsWkbTypes.LineString,
    "MULTILINESTRING": QgsWkbTypes.MultiLineString,
    "MULTIPOINT": QgsWkbTypes.MultiPolygon,
    "MULTIPOLYGON": QgsWkbTypes.MultiPolygon,
    "POINT": QgsWkbTypes.Point,
    "POLYGON": QgsWkbTypes.Polygon,
    # ...
}

mapping_duckdb_qgis_type = {
    "BIGINT": QVariant.Int,
    "BOOLEAN": QVariant.Bool,
    "DATE": QVariant.Date,
    "DOUBLE": QVariant.Double,
    "INTEGER": QVariant.Int,
    "TIMESTAMP": QVariant.DateTime,
    "VARCHAR": QVariant.String,
    # Type used for custom sql when table is not created
    # Not difference betwenn float and integer so all the numeric field are NUMBER
    "NUMBER": QVariant.Double,
    "STRING": QVariant.String,
    "Date": QVariant.Date,
    "bool": QVariant.Bool,
}
