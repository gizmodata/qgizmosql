# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
