from qgis.core import QgsProviderRegistry

from qduckdb.provider.duckdb_provider import DuckdbProvider
from qduckdb.provider.duckdb_provider_metadata import DuckdbProviderMetadata


def register_provider_if_necessary():
    """Load duckdb provider if it has not already been loaded"""
    registry = QgsProviderRegistry.instance()
    if "duckdb" in registry.providerList():
        # provider has already been loaded, exit
        return

    # load the provider
    duckdb_metadata = DuckdbProviderMetadata()
    assert registry.registerProvider(duckdb_metadata)
    assert registry.providerMetadata(DuckdbProvider.providerKey()) == duckdb_metadata
