from typing import Dict

from qgis.core import QgsProviderMetadata, QgsReadWriteContext

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
        # Anticipate the case where a separator is trailing at the beginning or end of a uri.
        uri = uri.strip("|")

        result = {}
        for element in uri.split("|"):
            key, value = element.split("=", 1)
            result[key] = value.strip('"')
        return result

    def encodeUri(self, parts: Dict[str, str]) -> str:
        """Reassembles a provider data source URI from its component paths
        (e.g. file path, layer name).

        :param Dict[str, str] parts: parts as returned by decodeUri
        :returns: uri as string
        """
        sql_query = parts.get("sql", "")
        if sql_query:
            sql_part = f'sql="{sql_query}"'
        else:
            table_name = parts["table"]
            schema = parts.get("schema", "main")
            sql_part = f'table="{table_name}"|schema="{schema}"'

        path = parts["path"]
        epsg = parts["epsg"]
        uri = f'path="{path}"|{sql_part}|epsg="{epsg}"'
        if "extension" in parts:
            extension = parts["extension"]
            uri = f'{uri}|extension="{extension}"'
        return uri

    def absoluteToRelativeUri(self, uri: str, context: QgsReadWriteContext) -> str:
        """Convert an absolute uri to a relative one

        The uri is parsed and then the path converted to a relative path by writePath
        Then, a new uri with a relative path is encoded.

        This only works for QGIS 3.30 and above as it did not exist before.
        Before this version, it is not possible to save an uri as relative in a project.

        :example:

        uri = f"path=/home/test/gis/insee/bureaux_vote.db table=cities epsg=4326"
        relative_uri = f"path=./bureaux_vote.db table=cities epsg=4326"

        :param str uri: uri to convert
        :param QgsReadWriteContext context: qgis context
        :returns: uri with a relative path
        """
        decoded_uri = self.decodeUri(uri)
        decoded_uri["path"] = context.pathResolver().writePath(decoded_uri["path"])
        return self.encodeUri(decoded_uri)

    def relativeToAbsoluteUri(self, uri: str, context: QgsReadWriteContext) -> str:
        """Convert a relative uri to an absolute one

        The uri is parsed and then the path converted to an absolute path by readPath
        Then, a new uri with an absolute path is encoded.

        This only works for QGIS 3.30 and above as it did not exist before.

        :example:

        uri = f"path=./bureaux_vote.db table=cities epsg=4326"
        absolute_uri = f"path=/home/test/gis/insee/bureaux_vote.db table=cities epsg=4326"

        :param str uri: uri to convert
        :param QgsReadWriteContext context: qgis context
        :returns: uri with an absolute path
        """
        decoded_uri = self.decodeUri(uri)
        decoded_uri["path"] = context.pathResolver().readPath(decoded_uri["path"])
        return self.encodeUri(decoded_uri)
