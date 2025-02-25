from pathlib import Path
from urllib.parse import urlparse

from qduckdb.toolbelt.log_handler import PlgLogger


def check_file_exists(path: str) -> bool:
    """Checks if a file exists at the given path.

    If the file does not exist, a warning is logged using `PlgLogger.log()`.

    :param path: The file path to check.
    :type path: str
    :return: True if the file exists, False otherwise.
    :rtype: bool
    """
    if not Path(path).exists():
        PlgLogger.log(
            "The parquet file {} does not exist.".format(path),
            log_level=2,
            duration=10,
            push=True,
        )
        return False
    return True


def is_valid_url(url: str) -> bool:
    """Checks if the given URL is valid by ensuring it contains a scheme and a netloc.

    :param url: The URL to validate.
    :type url: str
    :return: True if the URL has both a scheme and a netloc, otherwise False.
    :rtype: bool
    """
    parsed = urlparse(url)
    if not bool(parsed.scheme) and not bool(parsed.netloc):
        PlgLogger.log(
            "{} is not a valid URL".format(url),
            log_level=2,
            duration=10,
            push=True,
        )
        return False
    return True
