# standard
import shlex
from pathlib import Path
from urllib.parse import urlparse

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
from qduckdb.toolbelt.log_handler import PlgLogger


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

        # Radio buttons source behavior
        self.on_source_change()
        self.rb_local_file.clicked.connect(self.on_source_change)
        self.rb_remote_file.clicked.connect(self.on_source_change)

        self.qfw_local_file.setFilter("Parquet (*.parquet)")
        self.pb_open.clicked.connect(self.load_parquet)

    @property
    def get_file_path(self) -> list[str]:
        """Returns the local file path as a list of parsed arguments.

        :return: A list of parsed file path components.
        :rtype: list[str]
        """
        return shlex.split(self.qfw_local_file.filePath())

    @property
    def get_file_url(self) -> str:
        """Returns the remote file URL as a string.

        :return: The remote file URL.
        :rtype: str
        """
        raw_url = self.le_remote_url.text()
        return raw_url

    def load_parquet(self) -> None:
        """
        Loads a Parquet file (local or remote) and adds it as a vector layer to the map.
        """

        duckdbProviderMetadata = QgsProviderRegistry.instance().providerMetadata(
            "duckdb"
        )

        if self.rb_local_file.isChecked():
            for parquet in self.get_file_path:
                if not self.check_parquet_exists(parquet):
                    continue
                uri_parts = self._get_uri_parts(parquet)
                layer_name = Path(parquet).name

        elif self.rb_remote_file.isChecked():
            if not self.is_valid_url(self.get_file_url):
                PlgLogger.log(
                    self.tr("{} is not a valid URL".format(self.get_file_url)),
                    log_level=2,
                    duration=10,
                    push=True,
                )
                return
            uri_parts = self._get_uri_parts(self.get_file_url)
            layer_name = "Remote parquet file"

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

    def check_parquet_exists(self, path: str) -> bool:
        """Checks if a Parquet file exists at the given path.

        If the file does not exist, a warning is logged using `PlgLogger.log()`.

        :param path: The file path to check.
        :type path: str
        :return: True if the file exists, False otherwise.
        :rtype: bool
        """
        if not Path(path).exists():
            PlgLogger.log(
                self.tr("The parquet file {} does not exist.".format(path)),
                log_level=2,
                duration=10,
                push=True,
            )
            return False
        return True

    def on_source_change(self) -> None:
        """Manages the behavior of radio buttons for file source selection.

        This method activates or deactivates the corresponding fields according to the
        user's choice between a local file and a remote URL.
        between a local file and a remote URL.
        """
        if self.rb_local_file.isChecked():
            self.qfw_local_file.setVisible(True)
            self.le_remote_url.setVisible(False)

        elif self.rb_remote_file.isChecked():
            self.qfw_local_file.setVisible(False)
            self.le_remote_url.setVisible(True)

    def is_valid_url(self, url: str) -> bool:
        """Checks if the given URL is valid by ensuring it contains a scheme and a netloc.

        :param url: The URL to validate.
        :type url: str
        :return: True if the URL has both a scheme and a netloc, otherwise False.
        :rtype: bool
        """
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
