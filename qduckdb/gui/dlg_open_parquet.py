# standard
import shlex
from pathlib import Path

# PyQGIS
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsProviderRegistry,
    QgsVectorLayer,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import OverrideCursor

# plugin
from qduckdb.__about__ import DIR_PLUGIN_ROOT
from qduckdb.provider.protocols import PROTOCOLS
from qduckdb.toolbelt.network import get_filename_from_url
from qduckdb.toolbelt.utils import check_file_exists, is_valid_url


class OpenParquetDialog(QDialog):
    def __init__(self, parent=None):
        """Dialog to choose one or several parquet file and load it as a vector layer with the duckdb provider"""

        # init module and ui
        super().__init__(parent)
        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)

        # icon
        self.setWindowIcon(
            QIcon(str(DIR_PLUGIN_ROOT.joinpath("resources/images/parquet.png")))
        )
        self.pb_open.setIcon(
            QIcon(str(DIR_PLUGIN_ROOT.joinpath("resources/images/parquet.png")))
        )

        self.qfw_local_file.setFilter("Parquet (*.parquet)")
        self.pb_open.clicked.connect(self.load_parquet)

    @property
    def get_file_path(self) -> list[str]:
        """Returns the local file path as a list of parsed arguments.

        :return: A list of parsed file path components.
        :rtype: list[str]
        """
        return shlex.split(self.qfw_local_file.filePath())

    def load_parquet(self) -> None:
        """
        Loads a Parquet file (local or remote) and adds it as a vector layer to the map.
        """

        duckdbProviderMetadata = QgsProviderRegistry.instance().providerMetadata(
            "duckdb"
        )

        for parquet in self.get_file_path:
            # Is URL
            if any(parquet.startswith(proto) for proto in PROTOCOLS):
                if not is_valid_url(parquet):
                    continue
                layer_name = get_filename_from_url(parquet)

            # Local file
            else:
                if not check_file_exists(parquet):
                    continue
                layer_name = Path(parquet).name

            uri_parts = self._get_uri_parts(parquet)
            self._add_layer_to_project(duckdbProviderMetadata, uri_parts, layer_name)

    def _get_uri_parts(self, path: str) -> dict:
        """
        Returns URI parts for the Parquet file.

        :param path: File path or URL of the Parquet file.
        :return: URI parts including SQL and EPSG.
        :rtype: dict
        """
        return {
            "path": "",
            "sql": f"SELECT * FROM read_parquet('{path}')",
            "epsg": self.crs.authid().replace("EPSG:", ""),
        }

    def _add_layer_to_project(
        self, provider_metadata, uri_parts, layer_name: str
    ) -> None:
        """
        Adds a vector layer to the map project.

        :param provider_metadata: Provider metadata for encoding the URI.
        :param uri_parts: URI parts for the Parquet file.
        :param layer_name: Name of the layer.
        """
        with OverrideCursor(Qt.WaitCursor):
            uri = provider_metadata.encodeUri(uri_parts)
            layer = QgsVectorLayer(uri, layer_name, "duckdb")
            QgsProject.instance().addMapLayer(layer)

        self.close()

    @property
    def crs(self) -> QgsCoordinateReferenceSystem:
        """Returns the projection selected by the user

        :return: The currently selected coordinate reference system.
        :rtype: QgsCoordinateReferenceSystem
        """
        return self.qw_crs.crs()
