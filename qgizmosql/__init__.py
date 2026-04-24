#! python3  # noqa: E265

# ----------------------------------------------------------
# Copyright (C) 2015 Martin Dobias
# ----------------------------------------------------------
# Licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# --------------------------------------------------------------------


def classFactory(iface):
    """Load the plugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .plugin_main import QduckdbPlugin

    return QduckdbPlugin(iface)


def serverClassFactory(serverIface):
    """Load the plugin server class.

    :param serverIface: A QGIS server interface instance.
    :type serverIface: QgsServerInterface
    """
    from .plugin_main import QduckdbServerPlugin

    return QduckdbServerPlugin(serverIface)
