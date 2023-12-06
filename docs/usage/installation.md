# Installation

## Requirements

The plugin's logic is mainly based on on the [DuckDB API's Pyton client](https://duckdb.org/docs/api/python/overview.html), which is not distributed with QGIS.

### Linux

> Typically on Ubuntu 22.04 with Python 3.10

Open a terminal and install dependencies from the Python Package Index (PyPi):

```sh
python3 -m pip install qduckdb "duckdb==0.9.2"
```

### Windows: embedded package

It's quite a challenge to install it on QGIS for Windows, because QGIS uses its own Python interpreter and doesn't make it easy to use packages manager (`pip`).

To make it easier for Windows end-users, we did our best to embed the dependencies within the released version of the plugin (during CI), inside the `embedded_external_libs` folder.

Technically, the plugin tries to:

1. import packages from the Python interpreter used by QGIS (system on Linux, specific on Windows)
1. if it does not succeed, then it adds the `embedded_external_libs` subfolder to the `PYTHONPATH` and then import packages from it
1. it it still fails, then the plugin is disabled and the user is warned with a button leading him to here:

![Dependencies missing](../static/dependencies_missing_warning.png)

**BUT** there are some caveats because those packages require to be compiled with the same exact Python version than the one used by QGIS and sometimes the QGIS packagers change the Python version...

### MacOS

Note that on MacOS QGIS uses its own python, not the system's.

Open a terminal and install dependencies from the Python Package Index (PyPi) on QGIS python :

```sh
/Applications/QGIS.app/Contents/MacOS/bin/python3.9 -m pip install "duckdb==0.9.2"
```

### Manual installation

Then, if the plugin fails to import a package, you can try to install it manually using the `pip` command.

> Mainly tested on Windows 10.0.19044.

1. Launch the `OSGeo4W Shell`. Look for it in your Windows Search or directly into your QGIS install folder:
    - installed with the _all inclusive_ standalone `.msi`: `C:\Program Files\QGIS`
    - installed with the OSGeo4W with default settings: `C:\OSGeo4W`
1. Run (example with QGIS LTR installed):

  ```batch
  python-qgis-ltr -m pip install -U pip
  python-qgis-ltr -m pip install -U setuptools wheel
  python-qgis-ltr -m pip install -U "duckdb==0.9.2"
  ```

:::{important}
**Remember** to look at the [`requirements/embedded.txt`](https://gitlab.com/Oslandia/qgis/qduckdb/-/blob/main/requirements/embedded.txt) file to make sure you are not missing any package and using the correct versions. The above command is just an example, a pattern.
:::

----

## Plugin

## Stable version (recommended)

This plugin is published on the official QGIS plugins repository: <https://plugins.qgis.org/plugins/qduckdb/>.

## Beta versions released

Enable experimental extensions in the QGIS plugins manager settings panel.

## Earlier development version

If you define yourself as early adopter or a tester and can't wait for the release, the plugin is automatically packaged for each commit to main, so you can use this address as repository URL in your QGIS extensions manager settings:

```url
https://oslandia.gitlab.io/qgis/qduckdb/plugins.xml
```

Be careful, this version can be unstable.
