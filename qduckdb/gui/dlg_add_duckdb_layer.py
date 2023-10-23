from pathlib import Path

import duckdb
from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from qduckdb.toolbelt.log_handler import PlgLogger


class LoadDuckDBLayerDialog(QDialog):
    def __init__(self, parent=None):
        """Dialog to choice duckdb file and layer to load in canevas with the
        duckdb provider"""
        # init module and ui
        super().__init__(parent)
        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)
        self._db_path_input.fileChanged.connect(self._add_list_table_name_to_combobox)
        self._table_combobox.currentTextChanged.connect(self._unlock_add_layer)
        self._add_layer_btn.clicked.connect(self._push_add_layer_button)
        self._add_layer_btn.setEnabled(False)

    def db_path(self) -> str:
        """Return the db path specified entered in the appropriate field"""
        return self._db_path_input.filePath()

    def crs(self) -> QgsCoordinateReferenceSystem:
        """Return the crs will"""
        return self.projection.crs()

    def list_table_in_db(self) -> list[str]:
        """return list of table

        :return: List of table
        :rtype: list
        """
        try:
            con = duckdb.connect(self.db_path())
        except duckdb.IOException:
            PlgLogger.log(
                "This is not a valid database DuckDB",
                log_level=Qgis.Critical,
                duration=10,
                push=True,
            )
            return []

        list_table = []
        for elem in con.sql(
            "SELECT table_name from information_schema.tables"
        ).fetchall():
            list_table.append(elem[0])
        con.close()

        return list_table

    def _add_list_table_name_to_combobox(self) -> None:
        """Add list of table to combobox"""
        self._table_combobox.clear()
        self._table_combobox.addItems(self.list_table_in_db())

    def _push_add_layer_button(self) -> None:
        if not Path(self.db_path()).exists():
            PlgLogger.log(
                "The database does not exist.",
                log_level=Qgis.Critical,
                duration=10,
                push=True,
            )
            return
        if not self._table_combobox.currentText():
            PlgLogger.log(
                "No table selected.",
                log_level=Qgis.Critical,
                duration=10,
                push=True,
            )
            return
        epsg = self.crs().authid()
        epsg = epsg.replace("EPSG:", "")
        uri = f"path={self.db_path()} table={self._table_combobox.currentText()} epsg={epsg}"
        layer = QgsVectorLayer(uri, self._table_combobox.currentText(), "duckdb")
        QgsProject.instance().addMapLayer(layer)

    def _unlock_add_layer(self) -> None:
        """Unlock the add layer button if a database is valid and a table is selected"""
        if self._table_combobox.currentText() and Path(self.db_path()).exists():
            self._add_layer_btn.setEnabled(True)
        else:
            self._add_layer_btn.setEnabled(False)
