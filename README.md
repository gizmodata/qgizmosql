# qgizmosql — QGIS plugin for GizmoSQL

Browse and visualize spatial data from a **[GizmoSQL](https://gizmodata.com/gizmosql)** server directly in QGIS — no raw DuckDB file required. Connect to a remote (or local) GizmoSQL Arrow Flight SQL service, pick a table, and add it as a QGIS layer.

> **Status: 🚧 Early development.** This plugin is being forked from [QDuckDB](https://gitlab.com/Oslandia/qgis/qduckdb) (Oslandia, GPLv2+) and is having its DuckDB embedded-file connection layer swapped for the **[`adbc-driver-gizmosql`](https://pypi.org/project/adbc-driver-gizmosql/)** client, which speaks Arrow Flight SQL to a GizmoSQL server. Track progress in [Issues](https://github.com/gizmodata/qgizmosql/issues).

[![Download latest](https://img.shields.io/github/v/release/gizmodata/qgizmosql?label=download%20latest%20ZIP&color=2ea44f)](https://github.com/gizmodata/qgizmosql/releases/latest/download/qgizmosql.zip)
[![CI](https://github.com/gizmodata/qgizmosql/actions/workflows/ci.yml/badge.svg)](https://github.com/gizmodata/qgizmosql/actions/workflows/ci.yml)
[![License: GPL v2+](https://img.shields.io/badge/License-GPLv2%2B-blue.svg)](LICENSE)

> **Install in QGIS:** click the green badge above to grab `qgizmosql.zip`, then in QGIS go to **Plugins → Manage and Install Plugins → Install from ZIP** and pick the file.

---

## Why qgizmosql?

A user of GizmoSQL asked for this in [gizmosql#160](https://github.com/gizmodata/gizmosql/issues/160):

> We use GizmoSQL for storing geospatial data. When it comes to visualizing the data on a map, DataGrips' geo viewer does not scale well and lacks GIS tools. QDuckDB exists, but it requires access to the raw DuckDB file. A QGIS plugin that connects to GizmoSQL directly would help GizmoSQL gain foothold in the GIS community.

`qgizmosql` is exactly that.

| | QDuckDB | **qgizmosql** |
|---|---|---|
| Data access | Local DuckDB file | Remote (or local) GizmoSQL server |
| Transport | In-process DuckDB | Arrow Flight SQL (gRPC + TLS) |
| Auth | n/a (file) | Password **or** OAuth/SSO (browser flow) |
| Multi-user | ❌ | ✅ |
| Spatial engine | DuckDB `spatial` ext. | Same — runs server-side on GizmoSQL |

---

## Quickstart

### 1. Prerequisites

- **QGIS ≥ 3.34.6** (with Python 3.12 bundled — `3.34.5` and earlier are not supported)
- A running **GizmoSQL server** — see the 30-second Docker recipe below
- Network access from your QGIS machine to the GizmoSQL server (default port `31337`)

### 2. Start a GizmoSQL server (skip if you already have one)

The fastest way to get a server running locally — with a TPC-H sample database pre-loaded:

```bash
docker run --name gizmosql \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 31337:31337 \
           --env TLS_ENABLED="1" \
           --env GIZMOSQL_USERNAME="gizmosql_user" \
           --env GIZMOSQL_PASSWORD="gizmosql_password" \
           --env PRINT_QUERIES="1" \
           --pull missing \
           gizmodata/gizmosql:latest
```

To load the DuckDB `spatial` extension on startup, add `--env INIT_SQL="INSTALL spatial; LOAD spatial;"` (or run those statements from your first query).

### 3. Install the QGIS plugin

**From the QGIS Plugin Repository** (once published):

1. In QGIS: **Plugins → Manage and Install Plugins…**
2. Search for `qgizmosql` and click **Install**

**From a ZIP (pre-release / development)**:

1. Download the latest `qgizmosql-*.zip` from [Releases](https://github.com/gizmodata/qgizmosql/releases)
2. In QGIS: **Plugins → Manage and Install Plugins… → Install from ZIP**
3. Select the ZIP and click **Install Plugin**

The plugin bundles `adbc-driver-gizmosql` and its dependencies on Windows, so no manual `pip install` is needed. On macOS/Linux, if QGIS's Python doesn't already have the driver, the plugin will install it to its own subdirectory on first activation.

### 4. Connect and add a layer

1. **Plugins → qgizmosql → Add GizmoSQL Layer**
2. Fill in the connection dialog:
   - **URI:** `grpc+tls://localhost:31337`
   - **Auth type:** `Password` or `OAuth / SSO`
   - **Username / Password** (for password auth) — e.g. `gizmosql_user` / `gizmosql_password`
   - **☑ Skip TLS verification** (only for self-signed local certs)
3. Click **Connect** — the plugin lists schemas and tables from the server
4. Pick a table with a geometry column, choose the geometry column, and click **Add Layer**

The table is streamed to QGIS as Arrow record batches and rendered as a vector layer. Feature requests (filters, bbox, attribute selection) are pushed down to GizmoSQL as SQL.

---

## PyQGIS usage (scripting)

You can also add layers programmatically from the QGIS Python console:

```python
from qgis.core import QgsVectorLayer, QgsProject

uri = (
    "grpc+tls://localhost:31337"
    "?username=gizmosql_user"
    "&password=gizmosql_password"
    "&tls_skip_verify=true"
    "&table=public.my_spatial_table"
    "&geom_column=geom"
)
layer = QgsVectorLayer(uri, "my_spatial_table", "gizmosql")
QgsProject.instance().addMapLayer(layer)
```

For OAuth/SSO, replace the username/password with `auth_type=external` — a browser window will open for login.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: adbc_driver_gizmosql` in QGIS | Restart QGIS after installing the plugin. On macOS/Linux, check the plugin log for the install path. |
| `TLS handshake failed` | For local self-signed certs, enable **Skip TLS verification**. For production, provide a CA bundle path. |
| `Connection refused` | Confirm the server is up. With the Docker command above, `docker ps` should show `gizmosql` running on `0.0.0.0:31337`. |
| No tables listed | Confirm the user has `SELECT` on `information_schema`. Try `SELECT * FROM information_schema.tables` via the [GizmoSQL CLI](https://github.com/gizmodata/gizmosql-public). |
| Geometry column not detected | qgizmosql looks for columns of type `GEOMETRY` (DuckDB spatial) or WKB `BLOB` columns. Cast with `ST_AsWKB(geom)` if needed. |

---

## Development

```bash
git clone https://github.com/gizmodata/qgizmosql
cd qgizmosql
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/development.txt
pip install --no-deps -U -r requirements/embedded.txt -t qgizmosql/embedded_external_libs
```

Symlink the `qgizmosql/` directory into your QGIS profile's `python/plugins/` folder to test your changes live.

See [CONTRIBUTING.md](CONTRIBUTING.md) for coding conventions (forked from QDuckDB: black, isort, flake8, pre-commit).

---

## Credits

- Forked from **[QDuckDB](https://gitlab.com/Oslandia/qgis/qduckdb)** by [Oslandia](https://oslandia.com) — originally funded by [IFREMER](https://www.ifremer.fr/). All original authors and copyright notices are preserved.
- **GizmoSQL** by [GizmoData](https://gizmodata.com) — an Arrow Flight SQL server built on DuckDB.
- **[ADBC](https://arrow.apache.org/adbc/)** — Apache Arrow Database Connectivity.

## License

GPLv2+ (inherited from QDuckDB). See [LICENSE](LICENSE).

## Get in touch

- Report bugs / request features: [GitHub Issues](https://github.com/gizmodata/qgizmosql/issues)
- Email: [philip@gizmodata.com](mailto:philip@gizmodata.com)
