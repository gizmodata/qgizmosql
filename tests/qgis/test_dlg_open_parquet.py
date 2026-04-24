from pathlib import Path

from qgis.core import QgsProject
from qgis.testing import start_app, unittest

from qgizmosql.gui.dlg_open_parquet import OpenParquetDialog
from qgizmosql.toolbelt.utils import check_file_exists, is_valid_url

from .utilities import cleanup_qgis_modules, register_provider_if_necessary


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

    @classmethod
    def tearDownClass(cls):
        cleanup_qgis_modules()

    def setUp(self):
        self.assertTrue(self.parquet_test.exists())

    def test_get_path(self) -> None:
        """Check that the parquet path is correctly returned"""
        self.dialog.qfw_local_file.setFilePath(self.parquet_test.as_posix())
        self.assertEqual(self.dialog.get_file_path, [str(self.parquet_test)])

    def test_open_local_parquet(self) -> None:
        """Test that a layer has been added to the canvas"""
        self.dialog.qfw_local_file.setFilePath(self.parquet_test.as_posix())
        self.assertTrue(check_file_exists(self.parquet_test))
        self.dialog.load_parquet()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("points.parquet"))

    def test_open_remote_parquet(self) -> None:
        """Test that a layer has been added to the canvas"""
        parquet_url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/qualite-de-lair-france/exports/parquet?lang=fr&timezone=Europe%2FBerlin"
        self.dialog.qfw_local_file.setFilePath(parquet_url)
        self.assertTrue(is_valid_url(parquet_url))
        self.dialog.load_parquet()
        project = QgsProject.instance()
        self.assertTrue(project.mapLayersByName("qualite-de-lair-france.parquet"))

    def test_paths(self) -> None:
        # Windows path
        path = r"\\Server\data\parquet\2025\sample.parquet"
        excepted = [r"\\Server\data\parquet\2025\sample.parquet"]
        self.dialog.qfw_local_file.setFilePath(path)
        self.assertEqual(self.dialog.get_file_path, excepted)

        # Multiple Windows path
        path = r'"\\Server\data\parquet\2025\sample.parquet" "C:\Users\data\sample.parquet"'
        excepted = [
            r"\\Server\data\parquet\2025\sample.parquet",
            r"C:\Users\data\sample.parquet",
        ]
        self.dialog.qfw_local_file.setFilePath(path)
        self.assertEqual(self.dialog.get_file_path, excepted)

        # Unix paths
        path = '"/home/gignac/data/sample.parquet"'
        excepted = ["/home/gignac/data/sample.parquet"]
        self.dialog.qfw_local_file.setFilePath(path)
        self.assertEqual(self.dialog.get_file_path, excepted)

        # Multiple unix paths
        path = '"/home/gignac/data/sample.parquet" "/etc/data/drogba.parquet"'
        excepted = ["/home/gignac/data/sample.parquet", "/etc/data/drogba.parquet"]
        self.dialog.qfw_local_file.setFilePath(path)
        self.assertEqual(self.dialog.get_file_path, excepted)
