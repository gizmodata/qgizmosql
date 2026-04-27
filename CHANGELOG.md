# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.12] - 2026-04-27

### Changed

- Feature iterator now streams Arrow record batches (`cursor.fetch_record_batch_reader()`) instead of pulling rows one at a time via `dbapi.fetchone()`. Each batch is materialised once with `Array.to_pylist()`; per-row access becomes a plain Python list lookup. Skips per-row dbapi bookkeeping and avoids the underlying driver re-walking the same Arrow buffers for every cell. Bigger layers feel snappier; the gain grows with row count.

### Fixed

- Set the Flight SQL gRPC max-receive-message-size to 1 GiB (`adbc.flight.sql.client_option.with_max_msg_size`) on every connection, replacing gRPC's 16 MB default. Previously, fetching a wide or large layer would fail with `ResourceExhausted: grpc: received message larger than max` partway through the cursor (#2). Overridable via the `QGIZMOSQL_MAX_FLIGHT_MSG_SIZE` env var if a deployment ever needs more than 1 GiB.

## [0.2.11] - 2026-04-27

### Fixed

- After pip-install completes, `_deps_importable()` now calls `importlib.invalidate_caches()` before re-probing. The first probe (before install) populates `sys.path_importer_cache` with negative-result entries for `embedded_external_libs/`, and those stale entries kept making the second probe fail even after pip wrote the files — leaving "Plugin disabled" errors with deps clearly on disk.
- `_deps_importable()` no longer logs the expected first-probe failure as `Critical`. Only the post-install probe — which would indicate a real install problem — surfaces as a critical log entry. Adds a `log_failure` flag for callers that need the diagnostic.
- On macOS, after pip succeeds the installer now runs `codesign --force --sign -` over every native `.so` / `.dylib` under `embedded_external_libs/`. Strips publisher Team IDs so QGIS (which has the `disable-library-validation` entitlement) can dlopen the native deps without macOS rejecting them.
- `_load_provider_imports()` now logs the underlying exception and full traceback when the provider/dialog imports fail, instead of just disabling the plugin with a generic "Error importing dependencies" message.
- Add-layer dialog now applies the initial Table-vs-SQL widget enabled state at construction. Previously the table combo stayed disabled until the user manually toggled the radio (the `setChecked(True)` call fired before `connect()`, so the `toggled` signal never reached the handler).
- Re-clicking the toolbar action now `raise_()`s and `activateWindow()`s the add-layer dialog, so it comes back to the front when hidden behind the main QGIS window (macOS in particular — `show()` alone is a no-op when the dialog is technically already visible).

## [0.2.10] - 2026-04-27

### Fixed

- `dependencies.py` now logs pip failures with `Qgis.MessageLevel.Critical` (the proper enum) instead of a raw `int`. QGIS 4 / Qt6 rejects ints with `TypeError: argument 'level' has unexpected type 'int'`, which was masking the actual pip-failure message.
- Pass `PYTHONHOME` and `PYTHONPATH` to the pip subprocess via `QProcessEnvironment`. QGIS's bundled `python3.12` on macOS can't bootstrap standalone — its stdlib lives at `Contents/Frameworks/lib/python3.12` while a fresh interpreter would expect `Contents/lib/python3.12`. Inheriting the running interpreter's prefix + path lets pip find its own stdlib + pip module.

## [0.2.9] - 2026-04-27

### Fixed

- `dependencies.py` no longer launches a second QGIS instance when invoking pip. On macOS, `sys.executable` inside QGIS's embedded Python points at the **QGIS binary itself**, not at a Python interpreter — so `QProcess.start(sys.executable, ['-m', 'pip', ...])` was launching QGIS again with `-m`, `pip`, `install`, `--target`, … as arguments, which the second QGIS dutifully tried to open as data sources. New `_find_python_interpreter()` helper locates the bundled `python<X.Y>` sibling next to `sys.executable` (or falls back to PATH) and uses that for the subprocess.

## [0.2.8] - 2026-04-27

### Fixed

- The first-launch dependency installer no longer freezes QGIS while pip downloads. `dependencies.py` now drives pip via `QProcess` and pumps the Qt event loop in a `QApplication.processEvents()` while-loop, so the `QProgressDialog` stays responsive for the full ~60 MB download instead of looking like a hang.
- Pass `--no-input --disable-pip-version-check` to pip so it can never block on a prompt or stall on a version check that wants user input.

## [0.2.7] - 2026-04-27

### Fixed

- The first-launch dependency check in `dependencies.py` now probes `importlib_resources` in addition to `adbc_driver_gizmosql` and `pyarrow`. On systems where a partial install of the headline packages exists elsewhere on `sys.path` but is missing the backport, the previous check silently returned success — leaving the user with a working plugin UI that crashed on Connect with `No module named 'importlib_resources'`.

## [0.2.6] - 2026-04-27

### Fixed

- First-launch dependency install now succeeds end-to-end on systems that already have a partial `adbc_driver_gizmosql` install elsewhere on `sys.path`. Two changes:
  - `qgizmosql/requirements.txt` now pins `importlib_resources==7.1.0` — the `adbc_driver_gizmosql` package imports the backport explicitly, but pip's resolver skips it on Python ≥ 3.9, so the installer was leaving systems half-broken.
  - `qgizmosql/provider/gizmosql_wrapper.py` now unconditionally prepends `embedded_external_libs/` to `sys.path` before importing `adbc_driver_gizmosql` (previously only on import failure). Guarantees freshly-installed transitive deps are found even when a partial copy of the parent package exists elsewhere.

## [0.2.5] - 2026-04-27

### Changed

- Refactor 7 multi-line binary expressions (introduce intermediate variables) so neither W503 nor W504 fires — plugins.qgis.org enforces both, which are mutually exclusive at any operator/line boundary.
- Local CI now also gates on both W503 and W504.

## [0.2.4] - 2026-04-27

### Changed

- Adopt modern PEP 8 line-break-before-binary-operator style (W503 ignored, W504 enforced) to match plugins.qgis.org's flake8 config.

## [0.2.3] - 2026-04-27

### Added

- Mirror the plugins.qgis.org automated review checks in local CI:
  - Bandit security scan, gated on Medium+ severity (matches their threshold).
  - Detect Python files marked executable (`+x` permission).

### Changed

- Drop W503 from flake8 ignore list and fix violations.

### Fixed

- Strip executable bits from `__init__.py`, `plugin_main.py`, `gui/dlg_settings.py`, `toolbelt/log_handler.py`, `toolbelt/preferences.py`.

## [0.2.2] - 2026-04-27

### Security

- Annotate remaining trust-boundary SQL sites in `uniqueValues` and `setSubsetString` with `# nosec B608` and rationale.

## [0.2.1] - 2026-04-27

### Security

- SQL injection hardening (response to plugins.qgis.org Bandit B608 findings):
  - `_safe_identifier()` validates table, schema, and column names against `^[A-Za-z_][A-Za-z0-9_]*$` at construction time.
  - Three `information_schema` queries (geometry column, primary key, fields) now use bind parameters via `cursor.execute(operation=…, parameters=[…])`.
  - Identifier-only and explicit-trust-boundary sites annotated with `# nosec B608` plus a comment naming the trust boundary.

## [0.2.0] - 2026-04-27

### Changed

- Switch dependency strategy from "bundled" to "installed at first launch":
  - New `qgizmosql/dependencies.py` prompts the user via `QMessageBox` and runs `pip install --target embedded_external_libs/ -r requirements.txt` using QGIS's own Python.
  - `qgizmosql/requirements.txt` pins `adbc-driver-gizmosql==1.1.5` and `pyarrow==23.0.1`.
- Slim plugin ZIP (~250 KB) is the artifact submitted to plugins.qgis.org; a per-platform offline-install ZIP (linux-x86_64, macos-arm64, windows-x86_64) is also built and attached to each GitHub release.
- Drop deprecated `supportsQt6=True` from `metadata.txt` (QGIS 4 compatibility now follows from `qgisMaximumVersion`).

### Added

- Include `LICENSE` (GPLv2+) inside the plugin ZIP — required by plugins.qgis.org.

## [0.1.1] - 2026-04-24

### Added

- CI: ship an unversioned `qgizmosql.zip` alongside the versioned asset so `releases/latest/download/qgizmosql.zip` resolves without knowing the version.

## [0.1.0] - 2026-04-24

### Added

- Initial fork from [QDuckDB](https://gitlab.com/Oslandia/qgis/qduckdb) with the DuckDB embedded-file connection layer swapped for an Arrow Flight SQL client via [`adbc-driver-gizmosql`](https://pypi.org/project/adbc-driver-gizmosql/).
- QGIS provider key `gizmosql` — open a remote (or local) GizmoSQL server as a read-only QGIS vector data source.
- Add-layer dialog: host / port / TLS options, Password or OAuth/SSO (Enterprise) auth type, `QgsAuthConfigSelect` for encrypted credential storage, table picker or custom-SQL mode, CRS picker.
- Credentials are resolved via the QGIS Auth Manager at connect time — raw passwords never land in saved project URIs.
- GitHub Actions CI: flake8 lint, unit tests for the URI parser + connection config, and a buildable plugin ZIP artifact. Tagged releases (`v*`) attach the ZIP to a GitHub Release.

### Removed (from upstream QDuckDB)

- Embedded-DuckDB-file mode, open-Parquet-file dialog, DuckDB extension manager, force-download/httpfs handling — all irrelevant for a remote Flight SQL server.
- GitLab CI config, now replaced by GitHub Actions.

### Credits

Forked from QDuckDB by Oslandia (Florent Fougeres, Jean Felder, Julien Moura), originally funded by IFREMER. Licensed GPLv2+ (inherited).
