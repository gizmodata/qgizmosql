# standard
from pathlib import Path

# PyQGIS
from qgis.core import (
    QgsApplication,
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
from qduckdb.provider.duckdb_wrapper import DuckDbTools
from qduckdb.provider.extension import community_extensions, core_extensions
from qduckdb.toolbelt.log_handler import PlgLogger


class LoadDuckDBLayerDialog(QDialog):
    def __init__(self, parent=None):
        """Dialog to choice duckdb file and layer to load in canevas with the
        duckdb provider"""
        # init module and ui
        super().__init__(parent)

        self.list_table = None

        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)

        # attributes
        self.ddb_wrapper = DuckDbTools(auto_setup_spatial=True)

        # icon
        self.setWindowIcon(
            QIcon(str(DIR_PLUGIN_ROOT.joinpath("resources/images/logo_duckdb.png")))
        )
        self._add_layer_btn.setIcon(QgsApplication.getThemeIcon("mActionAddLayer.svg"))

        # extensions
        list_extension = community_extensions + core_extensions
        list_extension.sort()
        self._cbb_extension.addItems(list_extension)

        # widgets and signals connection
        self._db_path_input.fileChanged.connect(self._add_list_table_name_to_combobox)
        self._db_path_input.fileChanged.connect(self.change_mode)
        self._table_combobox.currentTextChanged.connect(self._unlock_add_layer)
        self._sql_query.textChanged.connect(self._unlock_add_layer)
        self._add_layer_btn.clicked.connect(self._push_add_layer_button)
        self._add_layer_btn.setEnabled(False)

        self._table.setChecked(True)
        self._sql.clicked.connect(self.change_mode)
        self._sql.clicked.connect(self._unlock_add_layer)
        self._table.clicked.connect(self.change_mode)
        self._table.clicked.connect(self._add_list_table_name_to_combobox)
        self._table.clicked.connect(self._unlock_add_layer)

        self.label_sql.setEnabled(False)
        self._sql_query.setEnabled(False)
        self.label_extension.setEnabled(False)
        self._cbb_extension.setEnabled(False)

    def change_mode(self):
        """Interface behavior when radio buttons are used to switch between full table
        mode and custom sql query mode"""

        if self._table.isChecked():
            self._table_combobox.setEnabled(True)
            self._sql_query.setEnabled(False)
            self.label_sql.setEnabled(False)
            self.label_table.setEnabled(True)
            self._cbb_extension.setEnabled(False)
            self.label_extension.setEnabled(False)

        if self._sql.isChecked():
            self._table_combobox.setEnabled(False)
            self._sql_query.setEnabled(True)
            self.label_sql.setEnabled(True)
            self.label_table.setEnabled(False)
            self._cbb_extension.setEnabled(True)
            self.label_extension.setEnabled(True)

    @property
    def db_path(self) -> Path | None:
        """Return the db path specified entered in the appropriate field as pathlib.Path
            object.

        :return: path to the file picked by the user through the UI. This may return None if no database is provided in the ihm.
        :rtype: Path
        """

        if not self._db_path_input.filePath():
            return None
        else:
            return Path(self._db_path_input.filePath())

    def crs(self) -> QgsCoordinateReferenceSystem:
        """Return the crs will"""
        return self.projection.crs()

    def list_table_in_db(self) -> list[str]:
        """return list of table

        :return: List of table
        :rtype: list
        """
        if not self._db_path_input.filePath():
            return []

        try:
            if not self.list_table:
                self.list_table = self.ddb_wrapper.run_sql(
                    database_path=self.db_path,
                    query_sql="list_tables",
                    requires_spatial=False,
                    results_fetcher="fetchall",
                )

            return [result[0] for result in self.list_table]

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
        self.ddb_wrapper.database_path = self.db_path

        # update table list
        self._table_combobox.clear()
        self.list_table = None
        self._table_combobox.addItems(self.list_table_in_db())

    def _push_add_layer_button(self) -> None:
        if self.db_path and not self.db_path.exists():
            PlgLogger.log(
                self.tr("The database {} does not exist.".format(self.db_path)),
                log_level=2,
                duration=10,
                push=True,
            )
            return
        if not self._table_combobox.currentText() and self._table.isChecked():
            PlgLogger.log(
                "No table selected.",
                log_level=2,
                duration=10,
                push=True,
            )
            return

        epsg = self.crs().authid()
        epsg = epsg.replace("EPSG:", "")
        duckdbProviderMetadata = QgsProviderRegistry.instance().providerMetadata(
            "duckdb"
        )

        table_name = ""
        sql_query = ""
        if self._sql.isChecked() and self._sql_query.text():
            sql_query = self._sql_query.text()
            table_name = "query"
        else:
            table_name = self._table_combobox.currentText()

        extension = ",".join(self._cbb_extension.checkedItems())

        uri_parts = {
            "path": str(self.db_path) if self.db_path else "",
            "sql": sql_query,
            "table": table_name,
            "epsg": epsg,
            "extension": extension,
        }
        uri = duckdbProviderMetadata.encodeUri(uri_parts)
        layer = QgsVectorLayer(uri, table_name, "duckdb")
        QgsProject.instance().addMapLayer(layer)

    def _unlock_add_layer(self) -> None:
        """Unlock the add layer button if a database is valid and a table is selected
        or valid sql query is input"""

        if self._table.isChecked():
            if self._table_combobox.currentText() and self.db_path.exists():
                self._add_layer_btn.setEnabled(True)
            else:
                self._add_layer_btn.setEnabled(False)

        if self._sql.isChecked():
            if not self.db_path and "select" in self._sql_query.text().lower():
                self._add_layer_btn.setEnabled(True)
            elif (
                self.db_path
                and self.db_path.exists()
                and "select" in self._sql_query.text().lower()
            ):
                self._add_layer_btn.setEnabled(True)

            else:
                self._add_layer_btn.setEnabled(False)
