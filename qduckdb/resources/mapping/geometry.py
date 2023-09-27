from qgis.core import QgsWkbTypes

mapping_duckdb_qgis_geometry = {
    "POINT": QgsWkbTypes.Point,
    "LINESTRING": QgsWkbTypes.LineString,
    "POLYGON": QgsWkbTypes.Polygon,
    "MULTIPOINT": QgsWkbTypes.MultiPolygon,
    "MULTILINESTRING": QgsWkbTypes.MultiLineString,
    "MULTIPOLYGON": QgsWkbTypes.MultiPolygon,
    # ...
}
