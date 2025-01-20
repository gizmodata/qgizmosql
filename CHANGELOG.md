# CHANGELOG

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

<!--

Unreleased

## version_tag - YYYY-DD-mm

### Added

### Changed

### Removed

-->

## 1.2.1 - 2025-01-20

- Support DATETIME field type !145

## 1.2.0 - 2024-12-23

- Fixed a bug when a table name contained a special character !138
- Proivder now supports DuckDB extensions !142

## 1.1.0 - 2024-12-02

- It's now possible to execute any sql query with the provider (instead of simple select from where) !133

## 1.0.1 - 2024-11-04

- Upgrade to DuckDB version 1.1.3 !132

## 1.0.0 - 2024-09-26

- First stable version
- Enhanced custom sql query function, crash cases are managed in exceptions !124
- Fixed the bug that prevented loading a view !123
- Upgrade to DuckDB version 1.1.1 !129
- Correctly support DATE, TIME and DATETIME fields types !131
- The provider now supports tables without geometries !127
- Fix bug on tables containing a primary key !130

## 0.8.1 - 2024-06-12

- Fix bug with tables containing a primary key !118

## 0.8.0 - 2024-06-10

- Update DuckDB version to 1.0.0 !117
- Handle columns name with space in provider !116

## 0.7.3 - 2024-05-24

- Update DuckDB version to 0.10.3 !114
- Some micro optimizations on UI !113

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
