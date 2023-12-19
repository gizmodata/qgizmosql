from typing import Dict

from qgis.core import QgsProject, QgsProviderMetadata, QgsReadWriteContext

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

        # readPath ensures to have an absolute path whether 'path' is absolute or not
        qgis_db_path = QgsProject.instance().pathResolver().readPath(path)
        return {"path": qgis_db_path, "table": table, "epsg": epsg}

    def encodeUri(self, parts: Dict[str, str]) -> str:
        """Reassembles a provider data source URI from its component paths
        (e.g. file path, layer name).

        :param Dict[str, str] parts: parts as returned by decodeUri
        :returns: uri as string
        """
        uri = f"path={parts['path']} table={parts['table']} epsg={parts['epsg']}"
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
