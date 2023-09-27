from qgis.PyQt.Qt import QVariant

mapping_duckdb_qgis_type = {
    "BIGINT": QVariant.Int,
    "INTEGER": QVariant.Int,
    "VARCHAR": QVariant.String,
    "DOUBLE": QVariant.Double,
    "BOOLEAN": QVariant.Bool,
    "DATE": QVariant.Date,
    "TIMESTAMP": QVariant.DateTime,
}
