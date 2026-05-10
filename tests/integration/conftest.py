"""Shared fixtures for qgizmosql integration tests.

The GizmoSQL server is started as a managed subprocess via the
[`gizmosql`](https://pypi.org/project/gizmosql/) PyPI package — no
Docker required. ``gizmosql.Server(...)`` auto-picks a free port so
the test server can coexist with a developer's local GizmoSQL on the
default 31337/31338 without any port juggling.

Pure-Python tests (no QGIS, no native deps) live in ``tests/unit``;
this directory is exclusively for tests that talk to a real server.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Iterator

import pytest


GIZMOSQL_USERNAME = "gizmosql_user"
GIZMOSQL_PASSWORD = "gizmosql_password"


def _generate_self_signed_tls_cert(out_dir: Path) -> tuple[Path, Path]:
    """Mint a self-signed RSA cert + key for ``localhost`` so the
    GizmoSQL test server's Flight SQL endpoint is reachable over
    ``grpc+tls://``."""
    from cryptography import x509  # noqa: PLC0415
    from cryptography.hazmat.primitives import hashes, serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: PLC0415
    from cryptography.x509.oid import NameOID  # noqa: PLC0415

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = out_dir / "tls_cert.pem"
    key_path = out_dir / "tls_key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


@pytest.fixture(scope="session")
def gizmosql_server(tmp_path_factory) -> Iterator:
    """Start a GizmoSQL server as a managed subprocess for the session."""
    gizmosql = pytest.importorskip(
        "gizmosql",
        reason="install `pip install gizmosql` to run integration tests",
    )

    tls_dir = tmp_path_factory.mktemp("tls")
    tls_dir.chmod(0o700)
    tls_cert, tls_key = _generate_self_signed_tls_cert(tls_dir)

    with gizmosql.Server(
        username=GIZMOSQL_USERNAME,
        password=GIZMOSQL_PASSWORD,
        extra_args=["--tls", str(tls_cert), str(tls_key)],
        extra_env={"PRINT_QUERIES": "0"},
    ) as srv:
        yield srv


@pytest.fixture(scope="session")
def gizmosql_host(gizmosql_server) -> str:
    return gizmosql_server.host


@pytest.fixture(scope="session")
def gizmosql_port(gizmosql_server) -> int:
    return gizmosql_server.port


@pytest.fixture(scope="session")
def gizmosql_credentials() -> dict:
    """Username / password / TLS skip flag the test server is configured with."""
    return {
        "username": GIZMOSQL_USERNAME,
        "password": GIZMOSQL_PASSWORD,
        "tls_skip_verify": True,
    }


@pytest.fixture(scope="session")
def gizmosql_conn_config(
    gizmosql_host: str,
    gizmosql_port: int,
    gizmosql_credentials: dict,
):
    """A ready-to-use ``GizmoSqlConnConfig`` against the test server."""
    # Install qgis stubs before importing the wrapper (it pulls in qgis.core
    # at module top level, which won't exist on a CI box without QGIS).
    _tests_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _tests_root not in sys.path:
        sys.path.insert(0, _tests_root)
    from _stubs import install as _install_stubs

    _install_stubs()

    from qgizmosql.provider.gizmosql_wrapper import GizmoSqlConnConfig

    return GizmoSqlConnConfig(
        host=gizmosql_host,
        port=gizmosql_port,
        use_tls=True,
        tls_skip_verify=gizmosql_credentials["tls_skip_verify"],
        username=gizmosql_credentials["username"],
        password=gizmosql_credentials["password"],
        auth_type="password",
    )
