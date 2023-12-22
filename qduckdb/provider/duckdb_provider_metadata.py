import re
from typing import Dict

from qgis.core import Qgis, QgsProject, QgsProviderMetadata, QgsReadWriteContext

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
        matches = re.findall(r'(\w+)="(.*?)"', uri)
        params = {key: value for key, value in matches}

        if "path" in params and Qgis.QGIS_VERSION_INT < 33000:
            # The logic to parse an uri and convert the path from
            # relative to absolute is:
            # 1. call `QGsVectorLayer::decodedSource()` to parse the
            # uri and convert the path with `readPath`
            # 2. call `QgsProviderMetadata.decodeUri()` to parse the uri
            # which already contains an absolute path.
            #
            # However, prior to QGIS 3.30, this does not work for duckdb
            # provider. Indeed, the behavior of each provider was
            # hardcoded in the function `QGsVectorLayer::decodedSource()`
            # and it could not handle duckdb provider.
            # Since, QGIS 3.30, this has been delegated to
            # QgsProviderMetadata::relativeToAbsoluteUri. This allows
            # each provider to have its own behavior and fix the issue
            # for duckdb provider.
            #
            # Since it is not possible to override
            # QGsVectorLayer::decodedSource(), prior to QGIS 3.30, the
            # uri used to call `decodeUri` contains a
            # relative path instead of an absolute one. By calling
            # `readPath`, this solves the issue.
            params["path"] = (
                QgsProject.instance().pathResolver().readPath(params["path"])
            )

        return params

    def encodeUri(self, parts: Dict[str, str]) -> str:
        """Reassembles a provider data source URI from its component paths
        (e.g. file path, layer name).

        :param Dict[str, str] parts: parts as returned by decodeUri
        :returns: uri as string
        """
        table_name = parts["table"]
        path = parts["path"]
        epsg = parts["epsg"]
        uri = f'path="{path}";table="{table_name}";epsg="{epsg}"'
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
