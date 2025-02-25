from pathlib import Path

from qgis.testing import unittest

from qduckdb.toolbelt.utils import check_file_exists, is_valid_url


class TestUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parquet_test = Path(__file__).parent.parent.joinpath(
            "fixtures/points.parquet"
        )

    def test_check_file_exists(self) -> None:
        self.assertTrue(check_file_exists(str(self.parquet_test)))

    def test_is_valid_url(self) -> None:
        """Test is_valid_url method"""
        self.assertTrue(is_valid_url("http://example.com/file.txt"))
        self.assertFalse(is_valid_url("gignac"))
