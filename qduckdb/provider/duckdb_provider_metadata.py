from qgis.core import QgsProviderMetadata

from qduckdb.provider.duckdb_provider import DuckdbProvider


class DuckdbProviderMetadata(QgsProviderMetadata):
    def __init__(self):
        super().__init__(
            DuckdbProvider.providerKey(),
            DuckdbProvider.description(),
            DuckdbProvider.createProvider,
        )
