from qgis.testing import unittest

from qduckdb.toolbelt.network import get_filename_from_url


class TestNetwork(unittest.TestCase):
    def test_get_filename_from_url(self) -> None:
        """test_get_filename_from_url"""

        # URL is a file
        self.assertEqual(
            get_filename_from_url(
                "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/qualite-de-lair-france/exports/parquet?lang=fr&timezone=Europe%2FBerlin"
            ),
            "qualite-de-lair-france.parquet",
        )

        # URL is not a file
        self.assertEqual(
            get_filename_from_url("https://qgis.org/"),
            "Remote parquet file",
        )

        # Wrong URL
        self.assertEqual(
            get_filename_from_url("http://this-url-not-exist.net/foo/bar/"),
            "Remote parquet file",
        )
