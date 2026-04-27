"""Runtime dependency installer for qgizmosql.

The QGIS plugin store caps uploads at 25 MB, so we cannot bundle pyarrow +
adbc-driver-gizmosql (~60 MB per platform, three platforms). Instead, on first
launch we prompt the user to install them into the plugin's
``embedded_external_libs/`` directory using the QGIS Python interpreter's pip.

Subsequent launches find the deps on sys.path (the wrapper adds
``embedded_external_libs/`` via ``site.addsitedir``) and skip the prompt.
"""

# standard
from __future__ import annotations

import shutil
import site
import sys
from pathlib import Path
from typing import Optional

# PyQGIS
from qgis.PyQt.QtCore import Qt, QProcess
from qgis.PyQt.QtWidgets import (
    QApplication,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

# plugin
from qgizmosql.__about__ import DIR_PLUGIN_ROOT
from qgizmosql.toolbelt.log_handler import PlgLogger

EMBEDDED_LIBS_DIR: Path = DIR_PLUGIN_ROOT / "embedded_external_libs"
REQUIREMENTS_FILE: Path = DIR_PLUGIN_ROOT / "requirements.txt"


def _find_python_interpreter() -> str:
    """Locate a real Python interpreter to drive pip with.

    On macOS, ``sys.executable`` inside QGIS points at the **QGIS binary
    itself**, not at a Python interpreter — so launching it as a subprocess
    starts another QGIS instance which (mis)interprets every pip CLI arg as
    a data-source path. Find the bundled python3.X sibling instead.
    """
    minor = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path(sys.executable).with_name(minor),
        Path(sys.executable).parent / minor,
        Path(sys.exec_prefix) / "bin" / minor,
    ]
    for c in candidates:
        if c.is_file() and c.name.lower().startswith("python"):
            return str(c)
    on_path = shutil.which(minor) or shutil.which("python3")
    if on_path:
        return on_path
    # Last resort: hand back sys.executable. The caller will surface the
    # subsequent failure to the user with a clear manual-install fallback.
    return sys.executable


def _deps_importable() -> bool:
    # Probe every entry in requirements.txt, not just the headline packages.
    # adbc_driver_gizmosql imports the importlib_resources backport at
    # connect time; if a partial system install has adbc + pyarrow but is
    # missing the backport, we'd silently skip the prompt and fail later.
    site.addsitedir(str(EMBEDDED_LIBS_DIR))
    try:
        import adbc_driver_gizmosql  # noqa: F401
        import importlib_resources  # noqa: F401
        import pyarrow  # noqa: F401
    except ImportError:
        return False
    return True


def _pip_install(parent: Optional[QWidget]) -> bool:
    EMBEDDED_LIBS_DIR.mkdir(parents=True, exist_ok=True)
    python_exe = _find_python_interpreter()
    args = [
        "-m",
        "pip",
        "install",
        "--target",
        str(EMBEDDED_LIBS_DIR),
        "--upgrade",
        "--no-input",
        "--disable-pip-version-check",
        "--requirement",
        str(REQUIREMENTS_FILE),
    ]

    progress = QProgressDialog(
        "Downloading pyarrow + adbc-driver-gizmosql (~60 MB)…\n"
        "This only happens once.",
        None,  # no cancel button — pip is not safely interruptible
        0,
        0,
        parent,
    )
    progress.setWindowTitle("qgizmosql: installing dependencies")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.show()

    # QProcess instead of subprocess.run so the Qt event loop keeps spinning
    # while pip downloads — otherwise the modal dialog appears frozen for
    # the full ~60 MB download and users assume QGIS hung.
    proc = QProcess(parent)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.start(python_exe, args)

    output_chunks: list[str] = []
    while proc.state() != QProcess.ProcessState.NotRunning:
        QApplication.processEvents()
        if proc.waitForReadyRead(50):
            output_chunks.append(bytes(proc.readAll()).decode("utf-8", "replace"))

    # Drain anything left in the buffers after the process exits.
    output_chunks.append(bytes(proc.readAll()).decode("utf-8", "replace"))
    progress.close()

    output = "".join(output_chunks)
    exit_code = proc.exitCode()
    if proc.exitStatus() != QProcess.ExitStatus.NormalExit or exit_code != 0:
        PlgLogger.log(
            message=f"pip install failed (exit {exit_code}):\n{output}",
            log_level=2,  # Critical
            push=True,
        )
        QMessageBox.critical(
            parent,
            "qgizmosql: dependency install failed",
            "Could not install pyarrow / adbc-driver-gizmosql.\n\n"
            f"pip exit code: {exit_code}\n\n"
            "See the QGIS Python console / message log for full output. "
            "You can also install manually:\n\n"
            f"  {python_exe} -m pip install --target \\\n"
            f"    {EMBEDDED_LIBS_DIR} \\\n"
            f"    -r {REQUIREMENTS_FILE}",
        )
        return False

    return True


def ensure_dependencies(parent: Optional[QWidget] = None) -> bool:
    """Make sure pyarrow + adbc-driver-gizmosql are importable.

    On first run, prompts the user to install them into the plugin's
    ``embedded_external_libs/`` directory.

    :param parent: parent widget for the prompt/progress dialogs
    :return: True if deps are importable after this call, False otherwise
    """
    if _deps_importable():
        return True

    answer = QMessageBox.question(
        parent,
        "qgizmosql: install dependencies?",
        "qgizmosql needs <b>pyarrow</b> and <b>adbc-driver-gizmosql</b> "
        "(~60 MB) to talk to a GizmoSQL server.<br><br>"
        "They will be downloaded into the plugin folder using QGIS's Python "
        "(no system-wide changes).<br><br>"
        "Install them now?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return False

    if not _pip_install(parent):
        return False

    if not _deps_importable():
        QMessageBox.critical(
            parent,
            "qgizmosql: dependencies still missing",
            "pip reported success but the packages could not be imported. "
            "See the QGIS message log for details.",
        )
        return False

    return True
