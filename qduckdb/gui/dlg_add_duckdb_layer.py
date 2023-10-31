# standard
from pathlib import Path

# PyQGIS
from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# plugin
from qduckdb.provider.duckdb_wrapper import DuckDbTools
from qduckdb.toolbelt.log_handler import PlgLogger


class LoadDuckDBLayerDialog(QDialog):
    def __init__(self, parent=None):
        """Dialog to choice duckdb file and layer to load in canevas with the
        duckdb provider"""
        # init module and ui
        super().__init__(parent)

        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)

        # attributes
        self.ddb_wrapper = DuckDbTools(auto_setup_spatial=True)

        # widgets and signals connection
        self._db_path_input.fileChanged.connect(self._add_list_table_name_to_combobox)
        self._table_combobox.currentTextChanged.connect(self._unlock_add_layer)
        self._add_layer_btn.clicked.connect(self._push_add_layer_button)
        self._add_layer_btn.setEnabled(False)

    def db_path(self) -> Path:
        """Return the db path specified entered in the appropriate field as pathlib.Path
            object.

        :return: path to the file picked by the user through the UI.
        :rtype: Path
        """
        return Path(self._db_path_input.filePath())

    def crs(self) -> QgsCoordinateReferenceSystem:
        """Return the crs will"""
        return self.projection.crs()

    def list_table_in_db(self) -> list[str]:
        """return list of table

        :return: List of table
        :rtype: list
        """
        try:
            query_results = self.ddb_wrapper.run_sql(
                database_path=self.db_path(),
                query_sql="list_tables",
                requires_spatial=False,
                results_fetcher="fetchall",
            )

            return [result[0] for result in query_results]
        except Exception as exc:
            PlgLogger.log(
                message="Unable to retrieve list of tables. Trace: {}".format(exc),
                log_level=2,
                push=True,
            )
            return []

    def _add_list_table_name_to_combobox(self) -> None:
        """Add list of table to combobox"""
        # set selected path as wrapper's default database path
        self.ddb_wrapper.database_path = self.db_path()

        # update table list
        self._table_combobox.clear()
        self._table_combobox.addItems(self.list_table_in_db())

    def _push_add_layer_button(self) -> None:
        if not self.db_path().exists():
            PlgLogger.log(
                self.tr("The database {} does not exist.".format(self.db_path())),
                log_level=2,
                duration=10,
                push=True,
            )
            return
        if not self._table_combobox.currentText():
            PlgLogger.log(
                "No table selected.",
                log_level=2,
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
        if self._table_combobox.currentText() and self.db_path().exists():
            self._add_layer_btn.setEnabled(True)
        else:
            self._add_layer_btn.setEnabled(False)
