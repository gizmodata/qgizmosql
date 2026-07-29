# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **Now runs on `adbc-driver-gizmosql` 2.0**, powered by the new native Go
  [GizmoSQL ADBC driver](https://github.com/gizmodata/gizmosql-adbc). Same
  Python API as 1.x, with DDL/DML immediate execution, `RETURNING` support,
  `gizmosql://` URIs, and OAuth/SSO provided by the shared Go driver library
  used across all languages. Pins bumped in `requirements/embedded.txt`
  (`adbc-driver-gizmosql>=2.0.0`, `pyarrow>=25`) and
  `qgizmosql/requirements.txt` (`adbc-driver-gizmosql==2.0.0`,
  `pyarrow==25.0.0`).
- `gizmosql_wrapper.py` now imports `DatabaseOptions` from
  `adbc_driver_gizmosql` itself instead of `adbc_driver_flightsql` — the 2.0
  driver no longer depends on `adbc-driver-flightsql`, so the old import
  would break in the offline ZIP. The test stubs and the CI integration job
  drop `adbc-driver-flightsql` accordingly.
- If you have a local `qgizmosql/embedded_external_libs/` from a previous
  install (it is git-ignored, populated per-machine), refresh it:
  `python -m pip install --no-deps -U -r requirements/embedded.txt -t qgizmosql/embedded_external_libs`.
- Raised remaining requirements floors to current stable versions:
  `flake8-builtins>=3.1,<4` (cap `<3` was stale — 3.x is current),
  `flake8-isort>=7,<8`, `flake8-qgis>=2.1,<3` (cap `<2` stale),
  `isort>=8,<9` (cap `<6` stale), `pre-commit>=4,<5`,
  `myst-parser>=5,<6`, `sphinx-autobuild==2025.*`,
  `sphinx-copybutton>=0.5,<1`, `sphinx-rtd-theme>=3,<4`,
  `sphinx-design>=0.7,<1` (cap `<0.6` stale), `qgis-plugin-ci>=2.10,<3`,
  `pytest-cov>=7`, `packaging>=26`; CI integration job now installs
  `gizmosql>=1.35.1,<2` and `cryptography>=49`.
- Bumped GitHub Actions to current majors: `actions/checkout` v4 → v7,
  `actions/setup-python` v5 → v7, `actions/upload-artifact` v4 → v7,
  `actions/download-artifact` v4 → v8, `softprops/action-gh-release` v2 → v3.

## [0.4.2] - 2026-05-10

### Changed

- Switched the integration-test fixture from a Docker-managed
  `gizmodata/gizmosql:latest` container to the
  [`gizmosql`](https://pypi.org/project/gizmosql/) PyPI package's
  managed subprocess. The fixture now mints a session-scoped
  self-signed TLS cert via `cryptography` and passes it through
  `--tls`, preserving the `grpc+tls://` connection contract. The
  three-mode docstring (Docker SDK / pre-running server / CI services)
  collapses to a single mode — the package picks a free port on every
  run, so the prior port-juggling (41337/41338) and `GIZMOSQL_TEST_*`
  env-var indirection are no longer needed. The `services: gizmosql`
  block in CI is removed; the integration step pip-installs `gizmosql`
  + `cryptography` instead. Local development no longer requires
  Docker.

## [0.4.0] - 2026-04-28

### Added

- The connection dialog's table picker now shows tables qualified by catalog (`catalog.schema.table`), and the GizmoSQL `_gizmosql_system` internal catalog (along with `information_schema` / `pg_catalog`) is filtered out.
- The provider URI now accepts an optional `catalog=` parameter; both `parse_uri` and `build_uri` round-trip it. When absent, the provider lazily resolves the connection's `current_database()` so single-catalog deployments are unchanged.
- All `information_schema` lookups in the provider (column list, primary key, geometry probe, view detection) are now bound by `table_catalog` as well as `table_schema` and `table_name`, so picking a table from a non-default catalog returns rows from the correct catalog instead of silently falling back to the connection's default.
- Integration test suite under `tests/integration/` with a session-scoped pytest fixture that spins up `gizmodata/gizmosql:latest` via the Docker SDK on **non-default host ports** (41337/41338) so it coexists with a developer's local GizmoSQL on the standard 31337/31338. Reuses an existing server on the test port if one is already up. Mirrored by a CI `integration` job in `.github/workflows/ci.yml` using GitHub Actions `services:` (no Docker SDK needed in CI).
- `tests/_stubs.py`: shared qgis / ADBC stub installer used by unit and integration tests.
- New unit coverage: catalog parsing/round-trip in `parse_uri`/`build_uri`; the SQL-string shape of `SQL_QUERIES["list_tables"]`; the dialog's qualified-table-name parser (`split_qualified_table`).

## [0.3.1] - 2026-04-28

### Fixed

- CI publish-plugin job: switched from the legacy XML-RPC `/plugins/RPC2/` upload (which only accepts the account password and 403'd on PATs) to the v2 token endpoint `POST /plugins/api/qgizmosql/version/add/` with `Authorization: Bearer <JWT>`. Treats HTTP 201 as success and surfaces the response body on failure.
- CI gating: `release` now `needs: [package, package-offline, publish-plugin]` so a failed plugins.qgis.org upload no longer leaves a public GitHub Release pointing at a tag that didn't ship to the store.
- CI ordering: `actions/checkout@v4` now runs before `actions/download-artifact@v4` in `publish-plugin` (checkout's clean step was wiping the freshly-downloaded `dist/qgizmosql.zip`).

## [0.3.0] - 2026-04-28

### Changed

- Lowered `qgisMinimumVersion` from `4.0.0` to `3.40.0` so the plugin installs on the current QGIS LTR (3.40 *Bratislava*) in addition to latest stable. The provider already branches on `Qgis.QGIS_VERSION_INT` to use `QVariant` types on QGIS < 3.38, so QMetaType-only call sites continue to work on 3.40+. Closes #1.

### Added

- CI now publishes the slim plugin ZIP to [plugins.qgis.org](https://plugins.qgis.org/plugins/qgizmosql/) automatically on every `v*` tag, using `secrets.QGIS_PLUGIN_TOKEN` (Personal Access Token) and `vars.QGIS_PLUGIN_USERNAME` for HTTP basic auth against the official `plugin_upload.py` XML-RPC endpoint.
- README badge linking to the plugin's page on plugins.qgis.org.
- README: optional `INIT_SQL_COMMANDS` snippet that seeds a 5-row `cities` `GEOMETRY` table inside the GizmoSQL container so first-time users have something to add as a layer immediately.

### Removed

- README: dropped the manual `INSTALL spatial; LOAD spatial;` hint — GizmoSQL loads the DuckDB `spatial` extension automatically on startup.

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
