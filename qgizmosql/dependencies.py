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

import importlib
import os
import subprocess

# PyQGIS
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt, QProcess, QProcessEnvironment
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


def _deps_importable(log_failure: bool = False) -> bool:
    # Probe every entry in requirements.txt, not just the headline packages.
    # adbc_driver_gizmosql imports the importlib_resources backport at
    # connect time; if a partial system install has adbc + pyarrow but is
    # missing the backport, we'd silently skip the prompt and fail later.
    site.addsitedir(str(EMBEDDED_LIBS_DIR))
    # The first probe (before pip install) populates sys.path_importer_cache
    # with "no such module here" entries for embedded_external_libs/. After
    # pip writes the files, those cached negatives still apply unless we
    # explicitly invalidate the importer caches.
    importlib.invalidate_caches()
    try:
        import adbc_driver_gizmosql  # noqa: F401
        import importlib_resources  # noqa: F401
        import pyarrow  # noqa: F401
    except Exception as exc:  # noqa: BLE001  — dlopen errors aren't ImportError
        if log_failure:
            import traceback

            PlgLogger.log(
                message=(
                    "qgizmosql: dep probe failed after install:\n"
                    f"{exc!r}\n\n"
                    f"{traceback.format_exc()}"
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
        return False
    return True


def _adhoc_sign_native_libs(target: Path) -> None:
    """Re-sign every .so / .dylib under *target* with the ad-hoc identity.

    macOS Library Validation refuses to load dylibs into a hardened-runtime
    process when their code signature carries a Team ID different from the
    host process's. Stripping the publisher signature and re-signing ad-hoc
    (`codesign -s -`) clears the Team ID, leaving the file as a valid
    unsigned-but-validly-formatted Mach-O — which Library Validation
    accepts.
    """
    targets = list(target.rglob("*.so")) + list(target.rglob("*.dylib"))
    for f in targets:
        try:
            subprocess.run(
                ["codesign", "--force", "--sign", "-", str(f)],
                check=False,
                capture_output=True,
            )
        except Exception as exc:  # noqa: BLE001
            PlgLogger.log(
                message=f"codesign re-sign failed for {f}: {exc}",
                log_level=Qgis.MessageLevel.Warning,
                push=False,
            )


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

    # On macOS, QGIS's bundled python can't bootstrap standalone (PYTHONHOME
    # layout has stdlib at Contents/Frameworks/lib/python3.12 but sys.prefix
    # would otherwise look in Contents/lib/python3.12). Inherit the running
    # interpreter's sys.prefix and sys.path so the subprocess can find its
    # stdlib + pip.
    env = QProcessEnvironment.systemEnvironment()
    env.insert("PYTHONHOME", sys.prefix)
    env.insert("PYTHONPATH", os.pathsep.join(p for p in sys.path if p))
    proc.setProcessEnvironment(env)

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

    # On macOS, native wheels (pyarrow, adbc-driver-manager) are signed by
    # their PyPI publishers. macOS Library Validation refuses to load
    # third-party-signed dylibs into a notarized QGIS process, so we re-sign
    # them ad-hoc to clear the publisher Team ID. No-op on Linux/Windows.
    if exit_code == 0 and sys.platform == "darwin":
        _adhoc_sign_native_libs(EMBEDDED_LIBS_DIR)

    if proc.exitStatus() != QProcess.ExitStatus.NormalExit or exit_code != 0:
        PlgLogger.log(
            message=f"pip install failed (exit {exit_code}):\n{output}",
            log_level=Qgis.MessageLevel.Critical,
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
        PlgLogger.log(
            message="qgizmosql: deps already importable; skipping prompt.",
            log_level=Qgis.MessageLevel.Info,
            push=False,
        )
        return True
    PlgLogger.log(
        message="qgizmosql: deps not importable; prompting user to install.",
        log_level=Qgis.MessageLevel.Info,
        push=False,
    )

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

    if not _deps_importable(log_failure=True):
        QMessageBox.critical(
            parent,
            "qgizmosql: dependencies still missing",
            "pip reported success but the packages could not be imported. "
            "See the QGIS message log for details.",
        )
        return False

    return True
