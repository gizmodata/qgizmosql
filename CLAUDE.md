# CLAUDE.md — qgizmosql

Notes for future Claude Code sessions working on this repo.

## What this is

QGIS plugin that exposes a [GizmoSQL](https://gizmodata.com/gizmosql)
(Arrow Flight SQL) server as a read-only vector data provider. Forked from
[QDuckDB](https://gitlab.com/Oslandia/qgis/qduckdb) (GPLv2+, Oslandia); the
DuckDB embedded-file connection layer was replaced with an ADBC client via
[`adbc-driver-gizmosql`](https://pypi.org/project/adbc-driver-gizmosql/).

**License: GPLv2+** (inherited from QDuckDB — any derivative stays GPL).

**Current status:** v0.1.0 released, `experimental=True` in metadata.txt. Smoke-
tested on QGIS 4.0.1 / Qt6 / macOS with password auth + TLS. Custom-SQL mode,
OAuth/SSO, and QGIS 3.x LTR are NOT yet validated.

## Repo layout

```
qgizmosql/
├── qgizmosql/                  # the plugin itself
│   ├── __init__.py             # classFactory → QgizmosqlPlugin
│   ├── plugin_main.py          # QGIS plugin lifecycle, menu, toolbar, provider registration
│   ├── metadata.txt            # QGIS plugin manifest
│   ├── provider/
│   │   ├── gizmosql_wrapper.py          # GizmoSqlTools + GizmoSqlConnConfig + _ConnectionAdapter
│   │   ├── gizmosql_provider.py         # GizmoSqlProvider (QgsVectorDataProvider)
│   │   ├── gizmosql_provider_metadata.py# encodeUri/decodeUri
│   │   ├── gizmosql_feature_source.py   # GizmoSqlFeatureSource
│   │   ├── gizmosql_feature_iterator.py # GizmoSqlFeatureIterator (row-at-a-time)
│   │   └── mappings.py                  # DuckDB → Qt type maps (names still `*_duckdb_*` — cosmetic)
│   ├── gui/
│   │   ├── dlg_add_gizmosql_layer.py    # programmatic add-layer dialog (no .ui file)
│   │   └── dlg_settings.py              # (untouched from upstream, mostly unused)
│   ├── toolbelt/                        # logger, preferences, network helpers (from upstream)
│   └── resources/images/logo_gizmosql.png
├── tests/unit/test_wrapper.py  # 15 pure-Python tests (URI parse/build, config, round-trip)
├── .github/workflows/ci.yml    # lint + unit + package + release (on v* tag)
└── setup.cfg                   # flake8 config
```

## Key design decisions (don't re-litigate without reason)

- **URI scheme**: `gizmosql://host:port?use_tls=1&tls_skip_verify=0&auth_type=password&authcfg=<id>&schema=...&table=...&epsg=...&sql=...`.
  Owned by `GizmoSqlTools.parse_uri` / `.build_uri` — `GizmoSqlProviderMetadata` delegates to them.
- **Credentials**: go through **QGIS Auth Manager** (`authcfg=<id>` in the URI). `build_uri` suppresses raw `username=`/`password=` when `authcfg` is set — raw creds must never land in a saved project file.
- **OAuth/SSO** (`auth_type=external`) is labelled **"Enterprise Edition"** in the dialog. The user-facing GizmoSQL OAuth feature requires a commercial license — don't default to it.
- **`.sql()` compat shim**: `_ConnectionAdapter` + `_QueryResult` in `gizmosql_wrapper.py` expose a DuckDB-like `.sql(q).fetchone()/.fetchall()/.description` over the ADBC cursor. This was the only way to port `gizmosql_provider.py` / `gizmosql_feature_iterator.py` from upstream QDuckDB without a mass rewrite. If you rewrite the provider against ADBC-native APIs, you can drop the shim.
- **Feature iterator**: still row-at-a-time (`cursor.fetchone()` in a loop). Upstream used `duckdb` cursor; we kept the same shape. Switching to Arrow record-batch streaming (`cursor.fetch_record_batch_reader`) is the obvious perf win but requires refactoring the QGIS `QgsAbstractFeatureIterator` plumbing — deferred.
- **Primary key detection**: pure `information_schema.table_constraints` join, not `duckdb_constraints()` (server-internal table function not reliably available).
- **Geometry detection in custom-SQL mode**: uses `DESCRIBE <subquery>` (DuckDB-specific). Works because GizmoSQL runs DuckDB server-side.
- **Embedded deps**: CI installs `adbc-driver-gizmosql` + `pyarrow` into `qgizmosql/embedded_external_libs/` at ZIP-build time. The wrapper adds that dir to `sys.path` at import time. `embedded_external_libs/` is `.gitignore`d — only the ZIP artifact contains it.

## Gotchas we've paid for (don't repeat)

- **QGIS 4 metadata**: `qgisMinimumVersion=3.34.6` causes QGIS 4 to reject the plugin as "not compatible" even if `qgisMaximumVersion` is high. Our `metadata.txt` uses `qgisMinimumVersion=4.0.0` as a workaround — drop back once we actually test on 3.x LTR (likely need separate metadata for a dual 3.x/4.x release).
- **Qt6 scoped enums**: in QGIS 4 / PyQt6, use `QDialogButtonBox.StandardButton.Close` and `QDialogButtonBox.ButtonRole.AcceptRole`, not the unscoped forms. Same applies to other Qt enums — always prefer fully-scoped in new dialog code.
- **QGIS bundled Python on macOS has a broken `PYTHONHOME` layout** (stdlib at `Contents/Frameworks/lib/python3.12` but `sys.prefix` expects `Contents/lib/python3.12`). Don't try to use QGIS's bundled pip to install into site-packages — install into `embedded_external_libs/` instead. Any system Python 3.12 with matching wheels works.
- **QGIS 4 profile dir** is `~/Library/Application Support/QGIS/QGIS4/profiles/default/` on macOS (not `QGIS3`).
- **`__pycache__` and `.pyc`** slipped into commits twice before I added them to `.gitignore`. Check `git status` before committing anything under `qgizmosql/`.

## Smoke-test recipe (manual, macOS)

1. Start server:
   ```bash
   docker run --name gizmosql --detach --rm --tty --init \
     --publish 31337:31337 \
     --env TLS_ENABLED=1 \
     --env GIZMOSQL_USERNAME=gizmosql_user \
     --env GIZMOSQL_PASSWORD=gizmosql_password \
     --pull missing gizmodata/gizmosql:latest
   ```
2. Seed a tiny spatial table (see commit history around 2026-04-24 for the exact snippet — `smoke.cities` with 5 points).
3. Install deps into plugin dir:
   ```bash
   python3.12 -m pip install --target qgizmosql/embedded_external_libs \
     adbc-driver-gizmosql pyarrow
   ```
4. Symlink into QGIS 4 profile:
   ```bash
   ln -sfn "$PWD/qgizmosql" \
     "$HOME/Library/Application Support/QGIS/QGIS4/profiles/default/python/plugins/qgizmosql"
   ```
5. In QGIS: create a Basic-auth config (Settings → Options → Authentication), enable the plugin, use the toolbar icon to open the dialog, Host=localhost, Port=31337, TLS on, Skip TLS verify on, pick the authcfg, Connect, add layer.

## Release process

`git tag -a vX.Y.Z -m "..."` + `git push origin vX.Y.Z`. CI `release` job:
- Rewrites `metadata.txt` `version=` to match the tag
- Installs runtime deps into `embedded_external_libs/`
- Zips the plugin
- Creates a GitHub Release with auto-generated notes and the ZIP attached

**Submission to [plugins.qgis.org](https://plugins.qgis.org/plugins/add/)** is a manual
web upload requiring osgeo.org SSO — can't be automated from CI. Not yet done.

## TODO

**Blocking a 1.0.0 release**
- [ ] Smoke-test custom-SQL mode (`DESCRIBE <subquery>` path — `gizmosql_provider.py:get_geometry_column`, `fields`)
- [ ] Smoke-test against QGIS 3.34 LTR — likely needs separate metadata (QDuckDB kept two branches)
- [ ] Submit to plugins.qgis.org and pass review
- [ ] Remove `experimental=True` from `metadata.txt`

**Nice-to-haves**
- [ ] Arrow record-batch streaming in the feature iterator (perf win for big layers)
- [ ] QGIS-environment integration tests in CI (`pytest-qgis` or a headless QGIS Docker image)
- [ ] OAuth/SSO manual smoke test — needs GizmoSQL Enterprise Edition server
- [ ] Rename `mappings.py` symbols `*_duckdb_*` → `*_type_*` for clarity (cosmetic)
- [ ] "Saved connections" — currently the user re-types host/port every time. Use `QgsSettings` to remember recent servers
- [ ] Replace upstream `docs/` (still mostly QDuckDB content) with a slim GizmoSQL-focused set, or drop entirely if the README is enough
- [ ] Write/improve connection error messages — the ADBC driver's exceptions are unhelpful for the common cases (wrong password, TLS mismatch, wrong host)
- [ ] Bundle spatial fixtures (Natural Earth, etc.) into the Docker seed so smoke tests have more interesting geometry than 5 points

**Cleanup candidates**
- `qgizmosql/toolbelt/network.py` — only used by the (deleted) parquet dialog; could be removed
- `qgizmosql/gui/dlg_settings.py` — upstream settings page, mostly unused in our fork. Decide: remove or wire up for "saved connections"
- `docs/` — still mostly QDuckDB content

## Useful commands

```bash
# Run unit tests locally
python3.12 -m unittest tests.unit.test_wrapper -v

# Lint
python3.12 -m flake8 qgizmosql

# Watch most recent CI run
gh run list --repo gizmodata/qgizmosql --limit 1
gh run watch <run-id> --repo gizmodata/qgizmosql

# Reload plugin in QGIS after code change: disable + re-enable it in
# Plugins → Manage and Install Plugins (QGIS caches imports on load).
# For fast iteration, install the "Plugin Reloader" plugin.
```
