# Standard
from typing import Optional
from urllib.parse import urlparse

# qgis
from qgis.core import Qgis, QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

# Plugin
from qgizmosql.__about__ import __title__, __version__
from qgizmosql.toolbelt.log_handler import PlgLogger


def build_request(
    url: Optional[QUrl] = None,
    http_content_type: str = "application/json",
    http_user_agent: str = f"{__title__}/{__version__}",
) -> QNetworkRequest:
    """Build request object using plugin settings.

    :param url: request url, defaults to None
    :type url: QUrl, optional
    :param http_content_type: content type, defaults to "application/json"
    :type http_content_type: str, optional
    :param http_user_agent: http user agent, defaults to f"{__title__}/{__version__}"
    :type http_user_agent: str, optional

    :return: network request object.
    :rtype: QNetworkRequest
    """
    # create network object
    qreq = QNetworkRequest(url=url)

    # headers
    headers = {
        b"Accept": bytes(http_content_type, "utf8"),
        b"User-Agent": bytes(http_user_agent, "utf8"),
    }
    for k, v in headers.items():
        qreq.setRawHeader(k, v)

    return qreq


def get_filename_from_url(url: str) -> str:
    """Method that returns the name of the downloaded file. This method finds the file name in the header.

    :param url: File url
    :type url: str
    :return: Filename
    :rtype: str
    """
    try:
        request = QgsBlockingNetworkRequest()
        request.head(build_request(QUrl(url)))
        content_disposition = (
            request.reply().rawHeader(b"Content-Disposition").data().decode("utf-8")
        )

    except Exception as exc:
        PlgLogger.log(
            message="Error retrieving downloaded file name. Trace: {}".format(exc),
            log_level=Qgis.MessageLevel.Warning,
            push=True,
        )

    if content_disposition:
        if "filename=" in content_disposition:
            filename = content_disposition.split('filename="')[1].split('"')[0]
        else:
            parsed_url = urlparse(url)
            filename = parsed_url.path.split("/")[-1]

        PlgLogger.log(
            message="The file name is: {}".format(filename),
            log_level=Qgis.MessageLevel.Success,
            push=False,
        )

    else:
        PlgLogger.log(
            message="Unable to determine the name of the remote file, a default name will be applied.",
            log_level=Qgis.MessageLevel.Warning,
            push=True,
        )
        filename = "Remote parquet file"

    return filename
