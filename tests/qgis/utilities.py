from qgis.core import QgsProviderRegistry, QgsRectangle

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


def compare_rectangles(
    rect_a: QgsRectangle, rect_b: QgsRectangle, tol: float = 0.00001
) -> bool:
    """
    Check that two rectangle coordinates are equal
    within a specified tolerance
    """
    coords_funcs = [
        QgsRectangle.xMinimum,
        QgsRectangle.xMaximum,
        QgsRectangle.yMinimum,
        QgsRectangle.yMaximum,
    ]
    for coord_func in coords_funcs:
        if abs(float(coord_func(rect_a)) - float(coord_func(rect_b))) > tol:
            return False

    return True
