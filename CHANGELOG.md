# CHANGELOG

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

<!--

Unreleased

## version_tag - YYYY-DD-mm

### Added

### Changed

### Removed

-->

## 0.7.2 - 2024-05-16

- Some micro optimizations on duckdb_feature_iterator !111

## 0.7.1 - 2024-05-03

- Use QgsFeatureRequest class syntax for enums !109

## 0.7.0 - 2024-05-03

- Plugin package with Python 3.12, now the minimum version of QGIS to use the plugin is 3.34.6 !106
- Implement subsetstring : is now possible to create a filter on a DuckDB layer !103
- Improve performance of the sql query by using rowid pseudocolumn instead of row_number !86

## 0.6.3 - 2024-05-02

- Add support for NoGeometry Flag on QgsFeatureRequest !98
- Log sql request when debug mode is on !98
- Following the packaging of qgis windows in python 3.12 the maximum version required to use the plugin is currently QGIS 3.34.5.

## 0.6.2 - 2024-04-18

- Update DuckDB version to 0.10.2 !100

## 0.6.1 - 2024-04-08

- Retrieve geometry as wkb instead of wkt. !97
- Support for json-type fields !94
- Provider : Add support for SubsetOfAttributes flag. !87

## 0.6.0 - 2024-03-26

- Misc typo fixes !83
- Update test to QGIS 3.34 !84
- Fix unique values in metadata provider !88
- Update DuckDB version to 0.10.1 !89
- Add a disclaimer about binary dependency and explicitly disable qt6 support !91

## 0.5.0 - 2024-03-08

- Loading a layer with an sql query !78
- Correctly read paths from a network share !76

## 0.4.1 - 2024-02-14

- Upgrade DuckDB version 0.9.2 to 0.10

## 0.4.0 - 2023-12-19

- Enable relative database path for QGIS projects !70

## 0.3.1 - 2023-12-06

- Fix the bug related to importing QGIS Server with the windows version which does not contain
QGIS server.

## 0.3.0 - 2023-12-06

- Adding support for the plugin by QGIS Server !68

## 0.2.0-beta1 - 2023-11-17

- First version to be published on the official QGIS plugins repository
- Add a QGIS provider to read a DuckDB database !2 !3 !4 !9 !11 !12 !14 !21 !22 !24 !34
- Creating a user interface to use the provider !15
- Centralizing DuckDB calls in a wrapper !48 !49 !50 !51 !52
- Windows packaging that includes the duckdb dependency !53

## 0.1.0 - 2023-09-08

- First release
- Generated with the [QGIS Plugins templater](https://oslandia.gitlab.io/qgis/template-qgis-plugin/)
