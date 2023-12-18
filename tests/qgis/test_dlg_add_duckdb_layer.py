from pathlib import Path

from qgis.core import QgsProject
from qgis.testing import start_app, unittest

from qduckdb.gui.dlg_add_duckdb_layer import LoadDuckDBLayerDialog

from .utilities import register_provider_if_necessary


class TestDlgAddDuckdbLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.dialog = LoadDuckDBLayerDialog()
        cls.db_path_test = Path(__file__).parent.parent.joinpath(
            "fixtures/base_test.db"
        )
        cls.wrong_db_path = Path("wrong/path/zidane.db")

    def setUp(self):
        self.assertTrue(self.db_path_test.exists())

    def test_get_path(self) -> None:
        """Check that the database path is correctly returned"""
        # Good path
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.assertEqual(self.dialog.db_path(), self.db_path_test)
        # Wrong path
        self.dialog._db_path_input.setFilePath(self.wrong_db_path.as_posix())
        self.assertEqual(self.dialog.db_path(), self.wrong_db_path)

    def test_list_table_in_db(self) -> None:
        """We test that the list of tables in the database is correctly returned"""
        self.assertIsInstance(self.dialog, LoadDuckDBLayerDialog)
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.assertEqual(
            self.dialog.list_table_in_db(),
            [
                "table_with_primary_key",
                "table_no_geom",
                "cities",
                "highway",
                "building",
                "test_multi",
            ],
        )

    def test_push_add_layer_button(self) -> None:
        """Test that a layer has been added to the canvas"""
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.dialog._table_combobox.setCurrentText("highway")
        self.dialog._db_path_input.setFilePath(self.db_path_test.as_posix())
        self.dialog._push_add_layer_button()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("highway"))

    def test_lock_button_with_wrong_path(self) -> None:
        """We test that the button remains locked when the wrong base is entered."""
        self.dialog._db_path_input.setFilePath(self.wrong_db_path.as_posix())
        self.assertFalse(self.dialog._add_layer_btn.isEnabled())
