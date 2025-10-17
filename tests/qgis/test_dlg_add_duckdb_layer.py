from pathlib import Path

from qgis.core import QgsProject, QgsWkbTypes
from qgis.testing import start_app, unittest

from qduckdb.gui.dlg_add_duckdb_layer import LoadDuckDBLayerDialog

from .utilities import cleanup_qgis_modules, register_provider_if_necessary


class TestDlgAddDuckdbLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.dialog = LoadDuckDBLayerDialog()
        cls.db_path_test = Path(__file__).parent.parent.joinpath(
            "fixtures/unitests_database.db"
        )
        cls.wrong_db_path = Path("wrong/path/zidane.db")

    def setUp(self):
        self.assertTrue(self.db_path_test.exists())

    @classmethod
    def tearDownClass(cls):
        cleanup_qgis_modules()

    def test_get_path(self) -> None:
        """Check that the database path is correctly returned"""
        # Good path
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.assertEqual(self.dialog.db_path, self.db_path_test)
        # Wrong path
        self.dialog._db_path_input.setFilePath(self.wrong_db_path.as_posix())
        self.assertEqual(self.dialog.db_path, self.wrong_db_path)

    def test_list_table_in_db(self) -> None:
        """We test that the list of tables in the database is correctly returned"""
        self.assertIsInstance(self.dialog, LoadDuckDBLayerDialog)
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.assertEqual(
            self.dialog.list_table_in_db().sort(),
            [
                "building",
                "cities",
                "highway",
                "table_no_geom",
                "table_with_primary_key",
                "test_multi",
            ].sort(),
        )

    def test_push_add_layer_button(self) -> None:
        """Test that a layer has been added to the canvas"""
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.dialog._table_combobox.setCurrentText("main.highway")
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.dialog._push_add_layer_button()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("main.highway"))

    def test_lock_button_with_wrong_path(self) -> None:
        """We test that the button remains locked when the wrong base is entered."""
        self.dialog._db_path_input.setFilePath(self.wrong_db_path.as_posix())
        self.assertFalse(self.dialog._add_layer_btn.isEnabled())

    def test_sql_query(self) -> None:
        """Test dialog with custom sql query"""
        self.dialog._sql.setChecked(True)
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.dialog._sql_query.setText(
            "SELECT * FROM cities where name = 'Marseille' ;"
        )
        self.dialog._push_add_layer_button()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("query"))
        layer = QgsProject.instance().mapLayersByName("query")[0]
        assert len(layer) == 1
        features = list(layer.getFeatures())
        assert len(features) == 1
        feature = features[0]
        assert feature["name"] == "Marseille"
        assert layer.geometryType() == QgsWkbTypes.PointGeometry
