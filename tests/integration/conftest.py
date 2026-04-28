"""Shared fixtures for qgizmosql integration tests.

Three execution modes — all expose the same fixtures:

* **Local dev with Docker SDK installed**: a session-scoped fixture starts
  a ``gizmodata/gizmosql:latest`` container on a *non-default* host port
  (so it can coexist with a GizmoSQL the developer is already running on
  31337), polls its logs for readiness, and tears it down at session end.

* **Local dev with a server already up on the host**: if ``$GIZMOSQL_TEST_PORT``
  (default 41337) is already listening, the fixture reuses it and skips
  Docker entirely. Mirrors the pattern in ``ibis-sqlflite/tests/conftest.py``.

* **CI (GitHub Actions ``services:``)**: when ``GIZMOSQL_TEST_HOST`` is set
  in the environment, the fixture is a no-op — a sidecar container is
  already running and reachable at ``$GIZMOSQL_TEST_HOST:$GIZMOSQL_TEST_PORT``.

Pure-Python tests (no QGIS, no native deps) live in ``tests/unit``;
this directory is exclusively for tests that talk to a real server.
"""

from __future__ import annotations

import os
import socket
import sys
import time
from typing import Iterator

import pytest

# Use non-default host ports so the test container can coexist with a
# regular GizmoSQL the developer is already running locally on the
# defaults. The container internally keeps its own defaults (31337 Flight
# SQL, 31338 health-check); only the *published* host port shifts.
# (OAuth port 31339 is Enterprise-only and not exposed by tests.)
GIZMOSQL_HOST_PORT = 41337
GIZMOSQL_HEALTH_HOST_PORT = 41338
GIZMOSQL_CONTAINER_PORT = 31337
GIZMOSQL_HEALTH_CONTAINER_PORT = 31338
GIZMOSQL_IMAGE = "gizmodata/gizmosql:latest"
GIZMOSQL_USERNAME = "gizmosql_user"
GIZMOSQL_PASSWORD = "gizmosql_password"
CONTAINER_NAME = "qgizmosql-test"
READY_LOG = "GizmoSQL server - started"


def _port_is_listening(port: int, host: str = "localhost") -> bool:
    """Return True if something is already accepting TCP on ``host:port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def _wait_for_log(container, ready: str, timeout: int = 60) -> None:
    """Poll a docker-py Container until ``ready`` shows up in its logs."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ready in container.logs().decode("utf-8", errors="replace"):
            return
        time.sleep(1)
    raise TimeoutError(
        f"GizmoSQL container did not log {ready!r} within {timeout}s"
    )


@pytest.fixture(scope="session")
def gizmosql_host() -> str:
    """Hostname tests should connect to. ``localhost`` for both modes."""
    return os.environ.get("GIZMOSQL_TEST_HOST", "localhost")


@pytest.fixture(scope="session")
def gizmosql_port() -> int:
    """Host-side TCP port that the Flight SQL endpoint is exposed on."""
    return int(os.environ.get("GIZMOSQL_TEST_PORT", str(GIZMOSQL_HOST_PORT)))


@pytest.fixture(scope="session")
def gizmosql_server(gizmosql_port: int) -> Iterator[None]:
    """Ensure a GizmoSQL server is running before any test executes.

    * CI: ``GIZMOSQL_TEST_HOST`` is set → trust the harness, yield.
    * Local with server already running on the configured port → reuse, yield.
    * Otherwise → spin up a container via the Docker SDK and clean up on exit.
    """
    if os.environ.get("GIZMOSQL_TEST_HOST"):
        # Sidecar container in GitHub Actions is already up.
        yield
        return

    if _port_is_listening(gizmosql_port):
        # Developer already has a GizmoSQL listening on the test port — reuse.
        yield
        return

    docker = pytest.importorskip(
        "docker",
        reason="install `pip install docker` to run integration tests locally",
    )
    client = docker.from_env()

    # Best-effort: remove a stale container from a previous interrupted run,
    # but reuse one that's still healthy.
    try:
        existing = client.containers.get(CONTAINER_NAME)
        if existing.status == "running":
            yield
            return
        existing.remove(force=True)
    except Exception:
        pass

    container = client.containers.run(
        image=GIZMOSQL_IMAGE,
        name=CONTAINER_NAME,
        detach=True,
        remove=True,
        tty=True,
        init=True,
        ports={
            f"{GIZMOSQL_CONTAINER_PORT}/tcp": gizmosql_port,
            f"{GIZMOSQL_HEALTH_CONTAINER_PORT}/tcp": GIZMOSQL_HEALTH_HOST_PORT,
        },
        environment={
            "GIZMOSQL_USERNAME": GIZMOSQL_USERNAME,
            "GIZMOSQL_PASSWORD": GIZMOSQL_PASSWORD,
            "TLS_ENABLED": "1",
            "PRINT_QUERIES": "0",
            "DATABASE_FILENAME": ":memory:",
        },
    )
    try:
        _wait_for_log(container, READY_LOG)
        yield
    finally:
        try:
            container.stop()
        except Exception:
            pass


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
    gizmosql_server: None,
    gizmosql_host: str,
    gizmosql_port: int,
    gizmosql_credentials: dict,
):
    """A ready-to-use ``GizmoSqlConnConfig`` against the test container."""
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
