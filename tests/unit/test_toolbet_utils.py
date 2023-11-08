#! python3  # noqa E265

import unittest
from pathlib import Path, WindowsPath
from sys import platform as opersys
from unittest.mock import patch

from qduckdb.toolbelt.utils import resolve_path


def mock_resolve(path: Path) -> Path:
    if not isinstance(path, WindowsPath) or (
        isinstance(path, WindowsPath) and not str(path).startswith("Z:")
    ):
        return path.resolve_backup()

    return Path("//192.158.1.51") / path.relative_to("Z:/")


class TestToolbetUtils(unittest.TestCase):
    @unittest.skipIf(opersys != "win32", "Test specific to Windows.")
    def test_resolve_path_win32(self):
        Path.resolve_backup = Path.resolve
        with patch("pathlib.Path.resolve", mock_resolve):
            path_local = Path(r"C:\\users\user\data\database.db")
            self.assertEqual(resolve_path(path_local), path_local)

            path_network = Path(r"Z:\\share\\database.db")
            self.assertEqual(resolve_path(path_network), path_network)

    @unittest.skipIf(opersys == "win32", "Test specific to Unix.")
    def test_resolve_path_unix(self):
        Path.resolve_backup = Path.resolve
        with patch("pathlib.Path.resolve", mock_resolve):
            path = Path("/home/foo/data/database.db")
            self.assertEqual(resolve_path(path), path)


if __name__ == "__main__":
    unittest.main()
