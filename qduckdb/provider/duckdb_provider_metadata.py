from typing import Dict

from qgis.core import QgsProviderMetadata

from qduckdb.provider.duckdb_provider import DuckdbProvider


class DuckdbProviderMetadata(QgsProviderMetadata):
    def __init__(self):
        super().__init__(
            DuckdbProvider.providerKey(),
            DuckdbProvider.description(),
            DuckdbProvider.createProvider,
        )

    def decodeUri(self, uri: str) -> Dict[str, str]:
        """Breaks a provider data source URI into its component paths
        (e.g. file path, layer name).

        :param str uri: uri to convert
        :returns: dict of components as strings
        """
        path = ""
        table = ""
        epsg = ""
        for variable in uri.split(" "):
            try:
                key, value = variable.split("=")
                if key == "path":
                    path = value
                elif key == "table":
                    table = value
                elif key == "epsg":
                    epsg = value
            except ValueError:
                raise

        return {"path": path, "table": table, "epsg": epsg}

    def encodeUri(self, parts: Dict[str, str]) -> str:
        """Reassembles a provider data source URI from its component paths
        (e.g. file path, layer name).

        :param Dict[str, str] parts: parts as returned by decodeUri
        :returns: uri as string
        """
        uri = f"path={parts['path']} table={parts['table']} epsg={parts['epsg']}"
        return uri
