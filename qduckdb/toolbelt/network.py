# Standard
from urllib.parse import urlparse

# qgis
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

# Plugin
from qduckdb.toolbelt.log_handler import PlgLogger


def get_filename_from_url(url: str) -> str:
    """Method that returns the name of the downloaded file. This method finds the file name in the header.

    :param url: File url
    :type url: str
    :return: Filename
    :rtype: str
    """
    try:
        request = QgsBlockingNetworkRequest()
        request.head(QNetworkRequest(QUrl(url)))
        content_disposition = (
            request.reply().rawHeader(b"Content-Disposition").data().decode("utf-8")
        )

        if "filename=" in content_disposition:
            filename = content_disposition.split('filename="')[1].split('"')[0]
        else:
            parsed_url = urlparse(url)
            filename = parsed_url.path.split("/")[-1]

    except Exception as exc:
        PlgLogger.log(
            message="Unable to determine the name of the remote file, a default name will be applied. Trace: {}".format(
                exc
            ),
            log_level=1,
            push=True,
        )
        filename = "Remote parquet file"

    return filename
