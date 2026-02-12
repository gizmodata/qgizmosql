import re
import sys
import urllib.request
from typing import Optional

from qgis.core import QgsProviderRegistry, QgsRectangle

from qduckdb.provider.duckdb_provider import DuckdbProvider
from qduckdb.provider.duckdb_provider_metadata import DuckdbProviderMetadata


def get_overtures_maps_latest_release() -> Optional[str]:
    """
    Return the latest release date of overtures maps data
    """
    URL = "https://overturemaps-us-west-2.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=release/"

    with urllib.request.urlopen(URL) as response:
        xml_text = response.read().decode("utf-8")

    releases = re.findall(r"release/(\d{4}-\d{2}-\d{2}\.\d+)/", xml_text)

    if not releases:
        return None

    return max(releases)


def cleanup_qgis_modules():
    """Unload qgis modules once a unit test module finished
    This allows to isolate unit test processes and avoid test which do not
    work well with start_app (the ones using 'setFilterRect')
    """
    qgis_modules = [mod for mod in list(sys.modules.keys()) if "qgis" in mod]
    for mod in qgis_modules:
        del sys.modules[mod]


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
