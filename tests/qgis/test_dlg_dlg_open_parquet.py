from pathlib import Path

from qgis.core import QgsProject
from qgis.testing import start_app, unittest

from qduckdb.gui.dlg_open_parquet import OpenParquetDialog

from .utilities import register_provider_if_necessary


class TestDlgOpenParquet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.dialog = OpenParquetDialog()
        cls.parquet_test = Path(__file__).parent.parent.joinpath(
            "fixtures/points.parquet"
        )

    def setUp(self):
        self.assertTrue(self.parquet_test.exists())

    def test_get_path(self) -> None:
        """Check that the parquet path is correctly returned"""
        self.dialog.qfw_parquet.setFilePath(self.parquet_test.as_posix())
        self.assertEqual(self.dialog.get_file_path, [str(self.parquet_test)])

    def test_check_parquet_exists(self) -> None:
        self.assertTrue(self.dialog.check_parquet_exists(str(self.parquet_test)))

    def test_open_parquet(self) -> None:
        """Test that a layer has been added to the canvas"""
        self.dialog.qfw_parquet.setFilePath(self.parquet_test.as_posix())
        self.dialog.load_parquet()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("points.parquet"))
