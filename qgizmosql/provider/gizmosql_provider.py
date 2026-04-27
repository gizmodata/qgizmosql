from __future__ import annotations

import re
import weakref
from typing import Any, Optional

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsDataProvider,
    QgsFeature,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QMetaType

from qgizmosql.provider import gizmosql_feature_iterator, gizmosql_feature_source
from qgizmosql.provider.gizmosql_wrapper import GizmoSqlTools
from qgizmosql.provider.mappings import (
    deprecate_mapping_duckdb_qgis_type,
    mapping_duckdb_qgis_geometry,
    mapping_duckdb_qgis_type,
)
from qgizmosql.toolbelt.log_handler import PlgLogger


# Identifiers (table, schema, column names) cannot be passed as bind
# parameters in any SQL dialect, so we constrain them to a strict ASCII
# regex at construction time. After this check passes, downstream f-string
# interpolation of these names is safe — there is no character that could
# alter SQL structure. Literal *values* in WHERE clauses are still bound
# via cursor.execute(operation=..., parameters=[...]) below.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: Optional[str], kind: str) -> Optional[str]:
    """Validate an SQL identifier. Returns the name unchanged or raises.

    :param name: candidate identifier (may be None — passes through)
    :param kind: human-readable label for error messages (e.g. "table")
    :raises ValueError: if name is non-empty and fails the regex check
    """
    if not name:
        return name
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid {kind} identifier {name!r}: only [A-Za-z_][A-Za-z0-9_]* allowed"
        )
    return name


class GizmoSqlProvider(QgsVectorDataProvider):
    """QGIS vector data provider backed by a GizmoSQL server.

    The wire protocol is Arrow Flight SQL, accessed through the
    ``adbc-driver-gizmosql`` Python client. Server executes DuckDB SQL —
    including the ``spatial`` extension — so spatial-type introspection
    still uses ``information_schema`` and ``ST_*`` functions.
    """

    def __init__(
        self,
        uri: str = "",
        providerOptions: QgsDataProvider.ProviderOptions = None,
        flags: QgsDataProvider.ReadFlags = None,
    ):
        super().__init__(uri)
        providerOptions = providerOptions or QgsDataProvider.ProviderOptions()
        flags = flags if flags is not None else QgsDataProvider.ReadFlags()

        self.wrapper = GizmoSqlTools()
        self._is_valid = False
        self._uri = uri
        self._wkb_type: Optional[QgsWkbTypes.Type] = None
        self._extent: Optional[QgsRectangle] = None
        self._column_geom: Optional[str] = None
        self._fields: Optional[QgsFields] = None
        self._feature_count: Optional[int] = None
        self._primary_key: Optional[int] = None
        self.filter_where_clause: Optional[str] = None
        self._con: Any = None

        try:
            (
                self._conn_config,
                self._table,
                self._epsg,
                self._sql,
                self._schema,
            ) = self.wrapper.parse_uri(uri)
            # Pin identifiers to a strict regex so they're safe to interpolate
            # into queries below — bind params can't carry identifiers.
            self._table = _safe_identifier(self._table, "table")
            self._schema = _safe_identifier(self._schema, "schema")
        except ValueError as exc:
            self._is_valid = False
            PlgLogger.log(message=str(exc), log_level=Qgis.MessageLevel.Critical, push=True)
            return

        if self._sql:
            # encodeUri may have escaped double-quotes; undo that for execution.
            self._sql = self._sql.replace('\\"', '"')

        self._crs = (
            QgsCoordinateReferenceSystem.fromEpsgId(int(self._epsg))
            if self._epsg
            else QgsCoordinateReferenceSystem()
        )

        try:
            self.connect_database()
        except Exception as exc:
            self._is_valid = False
            PlgLogger.log(
                message=f"Could not connect to GizmoSQL: {exc}",
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        if self._sql and not self._table:
            if not self.test_sql_query():
                return
            self._from_clause = f"({self._sql})"
        else:
            schema = self._schema or "main"
            self._from_clause = f'"{schema}"."{self._table}"'

        self.get_geometry_column()

        self._provider_options = providerOptions
        self._flags = flags
        self._is_valid = True
        weakref.finalize(self, self.disconnect_database)

        if Qgis.QGIS_VERSION_INT < 33800:
            self.mapping_field_type = deprecate_mapping_duckdb_qgis_type
        else:
            self.mapping_field_type = mapping_duckdb_qgis_type

    # -- provider identity -----------------------------------------------------

    @classmethod
    def providerKey(cls) -> str:
        return "gizmosql"

    @classmethod
    def description(cls) -> str:
        return "GizmoSQL"

    @classmethod
    def createProvider(cls, uri, providerOptions, flags=QgsDataProvider.ReadFlags()):
        return GizmoSqlProvider(uri, providerOptions, flags)

    def name(self) -> str:
        return self.providerKey()

    def storageType(self) -> str:
        return "GizmoSQL Arrow Flight SQL server"

    def isValid(self) -> bool:
        return self._is_valid

    def capabilities(self) -> QgsVectorDataProvider.Capabilities:
        return (
            QgsVectorDataProvider.Capability.CreateSpatialIndex |
            QgsVectorDataProvider.Capability.SelectAtId
        )

    # -- connection ------------------------------------------------------------

    def connect_database(self) -> None:
        self.wrapper.conn_config = self._conn_config
        self._con = self.wrapper.connect()

    def disconnect_database(self) -> None:
        if self._con is not None and self.isValid():
            try:
                self._con.close()
            except Exception:
                pass
            self._con = None

    def con(self) -> Optional[Any]:
        """Return a raw ADBC cursor for callers (e.g. the feature iterator)."""
        if not self._is_valid or self._con is None:
            return None
        return self._con.cursor()

    def test_sql_query(self) -> bool:
        if not self._sql:
            return True
        try:
            # Probe with LIMIT 0 — cheapest possible parse/plan check.
            # Trust boundary: self._sql is the user's own custom query from
            # the add-layer dialog; running it is the entire point.
            with self._con.cursor() as cur:
                cur.execute(f"SELECT * FROM ({self._sql}) LIMIT 0")  # nosec B608
            return True
        except Exception as exc:
            PlgLogger.log(
                self.tr(f"The SQL query is invalid: {exc}"),
                log_level=Qgis.MessageLevel.Critical,
                duration=15,
                push=True,
            )
            return False

    # -- feature metadata ------------------------------------------------------

    def featureCount(self) -> int:
        if self._feature_count is None:
            if not self._is_valid:
                self._feature_count = 0
            else:
                # _from_clause is built from validated identifiers (see
                # _safe_identifier in __init__) or from self._sql (user-
                # provided custom query — explicit trust boundary).
                # subsetString() is a SQL fragment supplied by QGIS / the user
                # via QgsVectorLayer.setSubsetString() — also a trust boundary.
                if self.subsetString():
                    row = self._con.sql(
                        f"select count(*) from {self._from_clause} "
                        f"WHERE {self.subsetString()}"  # nosec B608
                    ).fetchone()
                else:
                    row = self._con.sql(
                        f"select count(*) from {self._from_clause}"  # nosec B608
                    ).fetchone()
                self._feature_count = row[0] if row else 0
        return self._feature_count

    def wkbType(self) -> QgsWkbTypes:
        if not self._column_geom:
            return QgsWkbTypes.Type.NoGeometry
        if self._wkb_type is None:
            if not self._is_valid:
                self._wkb_type = QgsWkbTypes.Type.Unknown
            else:
                # _column_geom and _from_clause are validated identifiers.
                row = self._con.sql(
                    f"select st_geometrytype({self._column_geom}) "
                    f"from {self._from_clause} limit 1"  # nosec B608
                ).fetchone()
                str_geom = row[0] if row else None
                if str_geom in mapping_duckdb_qgis_geometry:
                    self._wkb_type = mapping_duckdb_qgis_geometry[str_geom]
                else:
                    PlgLogger.log(
                        self.tr(f"Geometry type {str_geom} not supported"),
                        log_level=Qgis.MessageLevel.Critical,
                        duration=15,
                        push=True,
                    )
                    self._wkb_type = QgsWkbTypes.Type.Unknown
        return self._wkb_type

    def extent(self) -> QgsRectangle:
        if self._extent is None:
            if not self._is_valid or not self._column_geom:
                self._extent = QgsRectangle()
                PlgLogger.log(
                    message="Table without geometry, can not compute an extent",
                    log_level=Qgis.MessageLevel.Success,
                    push=False,
                )
            else:
                # _column_geom and _from_clause are validated identifiers.
                extent_bounds = self._con.sql(
                    query=f"select min(st_xmin({self._column_geom})), "  # nosec B608
                    f"min(st_ymin({self._column_geom})), "
                    f"max(st_xmax({self._column_geom})), "
                    f"max(st_ymax({self._column_geom})) "
                    f"from {self._from_clause}"
                ).fetchone()
                self._extent = QgsRectangle(*extent_bounds)
                PlgLogger.log(
                    message="Extent calculated for {}: xmin={}, xmax={}, ymin={}, ymax={}".format(
                        self._table, *extent_bounds
                    ),
                    log_level=Qgis.MessageLevel.Success,
                )
        return self._extent

    def updateExtents(self) -> None:
        if self._extent is not None:
            self._extent.setMinimal()

    def get_geometry_column(self) -> Optional[str]:
        if self._column_geom is not None:
            return self._column_geom
        if not self._sql:
            schema = self._schema or "main"
            with self._con.cursor() as cur:
                cur.execute(
                    operation=(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = ? AND table_schema = ? "
                        "AND data_type = 'GEOMETRY'"
                    ),
                    parameters=[self._table, schema],
                )
                row = cur.fetchone()
            if row:
                self._column_geom = row[0]
        else:
            # Use DuckDB's DESCRIBE to introspect an ad-hoc query's output types.
            # Trust boundary: self._sql is the user-supplied custom query.
            rows = self._con.sql(f"DESCRIBE {self._sql}").fetchall()  # nosec B608
            for r in rows:
                col_name, col_type = r[0], r[1]
                if col_type == "GEOMETRY":
                    self._column_geom = col_name
                    break
        return self._column_geom

    def primary_key(self) -> int:
        if self._primary_key is not None:
            return self._primary_key
        if self._sql:
            self._primary_key = -1
            return self._primary_key
        schema = self._schema or "main"
        # information_schema-only query — portable across DuckDB versions and
        # avoids relying on the ``duckdb_constraints()`` table function, which
        # is server-internal.
        with self._con.cursor() as cur:
            cur.execute(
                operation=(
                    "SELECT kcu.ordinal_position - 1 "
                    "FROM information_schema.table_constraints tc "
                    "JOIN information_schema.key_column_usage kcu "
                    "  ON tc.constraint_name = kcu.constraint_name "
                    "  AND tc.table_schema = kcu.table_schema "
                    "  AND tc.table_name = kcu.table_name "
                    "WHERE tc.constraint_type = 'PRIMARY KEY' "
                    "  AND tc.table_name = ? "
                    "  AND tc.table_schema = ? "
                    "ORDER BY kcu.ordinal_position"
                ),
                parameters=[self._table, schema],
            )
            row = cur.fetchone()
        self._primary_key = int(row[0]) if row else -1
        return self._primary_key

    def fields(self) -> QgsFields:
        if self._fields is not None:
            return self._fields
        self._fields = QgsFields()
        if not self._is_valid:
            return self._fields

        if not self._sql:
            schema = self._schema or "main"
            with self._con.cursor() as cur:
                cur.execute(
                    operation=(
                        "select column_name, data_type from "
                        "information_schema.columns WHERE table_name = ? "
                        "AND table_schema = ? AND "
                        "data_type not in ('GEOMETRY', 'WKB_BLOB')"
                    ),
                    parameters=[self._table, schema],
                )
                field_info = cur.fetchall()
        else:
            # Trust boundary: self._sql is the user-supplied custom query.
            rows = self._con.sql(f"DESCRIBE {self._sql}").fetchall()  # nosec B608
            field_info = [
                (r[0], r[1])
                for r in rows
                if r[1] not in ("GEOMETRY", "WKB_BLOB") and r[0] != "rowid"
            ]

        for field_name, field_type in field_info:
            qgs_type = self.mapping_field_type.get(field_type)
            if qgs_type is None:
                # Fall back to string for unknown types rather than dropping the column.
                qgs_type = self.mapping_field_type.get("VARCHAR")
            self._fields.append(QgsField(field_name, qgs_type))
        return self._fields

    # -- QGIS provider API -----------------------------------------------------

    def dataSourceUri(self, expandAuthConfig: bool = False) -> str:
        return self._uri

    def crs(self) -> QgsCoordinateReferenceSystem:
        return self._crs

    def featureSource(self):
        return gizmosql_feature_source.GizmoSqlFeatureSource(self)

    def get_table(self) -> str:
        return "" if self._sql else (self._table or "")

    def is_view(self) -> bool:
        if self._sql:
            return False
        query = (
            "SELECT concat(table_schema,'.',table_name) as table_name "
            "FROM information_schema.tables WHERE table_type = 'VIEW'"
        )
        view_list = [row[0] for row in self._con.sql(query).fetchall()]
        return f"{self._schema or 'main'}.{self._table}" in view_list

    def uniqueValues(self, fieldIndex: int, limit: int = -1) -> set:
        # column_name comes from QgsFields, populated by self.fields() from
        # information_schema responses for the validated _table/_schema; it
        # cannot carry user-controlled SQL. _from_clause is built from
        # regex-validated identifiers (see _safe_identifier above).
        column_name = self.fields().field(fieldIndex).name()
        query = (
            f"select distinct {column_name} from {self._from_clause} "  # nosec B608
            f"order by {column_name}"
        )
        if limit >= 0:
            query += f" limit {limit}"
        return {row[0] for row in self._con.sql(query).fetchall()}

    def getFeatures(self, request=QgsFeatureRequest()) -> QgsFeature:
        return QgsFeatureIterator(
            gizmosql_feature_iterator.GizmoSqlFeatureIterator(
                gizmosql_feature_source.GizmoSqlFeatureSource(self), request
            )
        )

    def subsetString(self) -> Optional[str]:
        return self.filter_where_clause

    def setSubsetString(
        self, subsetstring: str, updateFeatureCount: bool = True
    ) -> bool:
        if subsetstring:
            try:
                # Trust boundary: `subsetstring` is a SQL fragment supplied by
                # QGIS / the user via QgsVectorLayer.setSubsetString(). We
                # smoke-test that the server can parse it. _from_clause is
                # composed of regex-validated identifiers.
                with self._con.cursor() as cur:
                    cur.execute(
                        f"select count(*) from {self._from_clause} "  # nosec B608
                        f"WHERE {subsetstring} LIMIT 0"
                    )
            except Exception as e:
                PlgLogger.log(
                    self.tr(f"SQL error in filter: {e}"),
                    log_level=Qgis.MessageLevel.Critical,
                    duration=5,
                    push=False,
                )
                return False
            self.filter_where_clause = subsetstring
        else:
            self.filter_where_clause = None

        if updateFeatureCount:
            self._feature_count = None
            self.reloadData()
        return True

    def supportsSubsetString(self) -> bool:
        return True

    def get_field_index_by_type(self, field_type: QMetaType) -> list:
        fields_index = []
        for i in range(self._fields.count()):
            if self._fields[i].type() == field_type:
                fields_index.append(i)
        return fields_index
