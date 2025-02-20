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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog

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

        self.qfw_parquet.setFilter("Parquet (*.parquet)")
        self.pb_open.clicked.connect(self.load_parquet)

    @property
    def get_file_path(self) -> list[str]:
        return shlex.split(self.qfw_parquet.filePath())

    def load_parquet(self) -> None:
        duckdbProviderMetadata = QgsProviderRegistry.instance().providerMetadata(
            "duckdb"
        )
        for parquet in self.get_file_path:
            if not self.check_parquet_exists(parquet):
                continue
            uri_parts = {
                "path": "",
                "sql": f"SELECT * FROM read_parquet('{parquet}')",
                "epsg": self.crs.authid().replace("EPSG:", ""),
            }

            layer_name = Path(parquet).name
            uri = duckdbProviderMetadata.encodeUri(uri_parts)
            layer = QgsVectorLayer(uri, layer_name, "duckdb")
            QgsProject.instance().addMapLayer(layer)

    @property
    def crs(self) -> QgsCoordinateReferenceSystem:
        """Returns the projection selected by the user

        :return: The currently selected coordinate reference system.
        :rtype: QgsCoordinateReferenceSystem
        """
        return self.qw_crs.crs()

    def check_parquet_exists(self, path: str) -> bool:
        if not Path(path).exists():
            PlgLogger.log(
                self.tr("The parquet file {} does not exist.".format(path)),
                log_level=2,
                duration=10,
                push=True,
            )
            return False
        return True
