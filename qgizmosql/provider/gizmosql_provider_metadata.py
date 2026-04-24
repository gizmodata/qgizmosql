"""QGIS provider metadata for the qgizmosql plugin.

The URI shape is owned by :mod:`qgizmosql.provider.gizmosql_wrapper` — see
``GizmoSqlTools.parse_uri`` / ``GizmoSqlTools.build_uri``. We delegate here so
there is a single source of truth for URI encoding/decoding.
"""

from typing import Dict
from urllib.parse import parse_qsl, urlencode, urlparse

from qgis.core import QgsProviderMetadata, QgsReadWriteContext

from qgizmosql.provider.gizmosql_provider import GizmoSqlProvider


class GizmoSqlProviderMetadata(QgsProviderMetadata):
    def __init__(self):
        super().__init__(
            GizmoSqlProvider.providerKey(),
            GizmoSqlProvider.description(),
            GizmoSqlProvider.createProvider,
        )

    def decodeUri(self, uri: str) -> Dict[str, str]:
        """Break the qgizmosql URI into a dict of string components."""
        parsed = urlparse(uri)
        result: Dict[str, str] = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if parsed.hostname:
            result["host"] = parsed.hostname
        if parsed.port:
            result["port"] = str(parsed.port)
        return result

    def encodeUri(self, parts: Dict[str, str]) -> str:
        """Reassemble a qgizmosql URI from a component dict.

        Required keys: ``host``. Optional: ``port`` (default 31337),
        ``use_tls``, ``tls_skip_verify``, ``auth_type``, ``authcfg``,
        ``username``, ``password``, ``schema``, ``table``, ``sql``, ``epsg``.
        """
        host = parts.get("host")
        if not host:
            raise ValueError("encodeUri: missing required 'host' part")
        port = parts.get("port", "31337")

        query = {k: v for k, v in parts.items() if k not in ("host", "port") and v}
        return f"gizmosql://{host}:{port}?{urlencode(query)}"

    def absoluteToRelativeUri(self, uri: str, context: QgsReadWriteContext) -> str:
        """No-op — qgizmosql URIs are remote (no filesystem path to rewrite)."""
        return uri

    def relativeToAbsoluteUri(self, uri: str, context: QgsReadWriteContext) -> str:
        return uri
