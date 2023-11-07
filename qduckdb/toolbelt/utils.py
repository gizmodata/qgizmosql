from pathlib import Path, WindowsPath


def resolve_path(path: Path) -> Path:
    """This utility function is used to avoid an issue when reading a
       file from a windows network share (for example a samba share).

       If the path is something like 'Z:\\share\\database.db',
       path.resolve() changes it into '//ip_adress/share/database.db'
       which duckdbs.connect() call interperts into
       'c:\\users\\user\\documents\\\\ip_adress\\share\\database.db'
       In that case, the best solution is not to resolve the path.

    :param path: a path
    :type query_sql: Path

    :return: resolved path
    :rtype: Path
    """
    path_resolved = path.resolve()
    if isinstance(path_resolved, WindowsPath) and str(path_resolved).startswith("\\"):
        return path

    return path_resolved
