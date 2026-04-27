# standard
from __future__ import (
    annotations,  # used to manage type annotation for method that return Self in Python < 3.11
)

from typing import Any, Callable

# PyQGIS
from qgis.core import (
    Qgis,
    QgsAbstractFeatureIterator,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QDate, QDateTime, QMetaType, QTime

# plugin
from qgizmosql.toolbelt.log_handler import PlgLogger
from qgizmosql.toolbelt.preferences import PlgOptionsManager


class GizmoSqlFeatureIterator(QgsAbstractFeatureIterator):
    def __init__(
        self,
        source,
        request: QgsFeatureRequest,
    ):
        """Constructor"""
        super().__init__(request)
        self._provider = source.get_provider()
        self._settings = PlgOptionsManager.get_plg_settings()
        self.log = PlgLogger().log

        self._request = request if request is not None else QgsFeatureRequest()
        self._transform = QgsCoordinateTransform()

        dest_crs = self._request.destinationCrs()
        if dest_crs.isValid() and dest_crs != source._provider.crs():
            self._transform = QgsCoordinateTransform(
                source._provider.crs(),
                dest_crs,
                self._request.transformContext(),
            )

        try:
            filter_rect = self.filterRectToSourceCrs(self._transform)
        except QgsCsException:
            self.close()
            return

        if not self._provider.isValid():
            return

        geom_column = self._provider.get_geometry_column()

        # Check if some attributes which contain date or time
        # In that case, they need to be converted to a Qt type
        # to be correctly handled by QGIS.
        attributes_conversion_functions: dict[QMetaType.Type, Callable[[Any], Any]] = {
            QMetaType.Type.QDate: QDate,
            QMetaType.Type.QTime: QTime,
            QMetaType.Type.QDateTime: QDateTime,
        }
        # By default, do not convert
        self._attributes_converters = {}
        for idx in range(len(self._provider.fields())):
            self._attributes_converters[idx] = lambda x: x

        # Check if some fields need to be converted
        # If that's the case, enable the _attributes_need_conversion flag
        # and assign the converter with the attributes index.
        self._attributes_need_conversion = False
        for field_type, converter in attributes_conversion_functions.items():
            for index in self._provider.get_field_index_by_type(field_type):
                self._attributes_need_conversion = True
                self._attributes_converters[index] = converter

        # Create the list of fields that need to be retrieved
        self._request_sub_attributes = (
            self._request.flags() & QgsFeatureRequest.Flag.SubsetOfAttributes
        )
        if self._request_sub_attributes and not self._provider.subsetString():
            idx_required = [idx for idx in self._request.subsetOfAttributes()]

            # The primary key column must be added if it is not present in the field list.
            pk = self._provider.primary_key()
            if pk != -1 and pk not in idx_required:
                idx_required.append(pk)

            list_field_names = [
                self._provider.fields()[idx].name() for idx in idx_required
            ]
        else:
            list_field_names = [field.name() for field in self._provider.fields()]

        if len(list_field_names) > 0:
            fields_name_for_query = '"' + '", "'.join(list_field_names) + '"'
        else:
            fields_name_for_query = ""

        if fields_name_for_query:
            fields_name_for_query += ","
        self.index_geom_column = len(list_field_names)

        # Create fid/fids list
        feature_id_list = None
        ft = self._request.filterType()
        ft_type = QgsFeatureRequest.FilterType
        if ft in (ft_type.FilterFid, ft_type.FilterFids):
            if ft == ft_type.FilterFid:
                feature_id_list = [self._request.filterFid()]
            else:
                feature_id_list = self._request.filterFids()

        where_clause_list = []
        if feature_id_list:
            if self._provider.primary_key() == -1:
                feature_clause = f"index in {tuple(feature_id_list)}"
            else:
                primary_key_name = list_field_names[self._provider.primary_key()]
                feature_clause = f"{primary_key_name} in {tuple(feature_id_list)}"

            where_clause_list.append(feature_clause)

        # Apply the filter expression
        if self._request.filterType() == QgsFeatureRequest.FilterType.FilterExpression:
            # A provider is supposed to implement a QgsSqlExpressionCompiler
            # in order to handle expression. However, this class is not
            # available in the Python bindings.
            # Try to use the expression as is. It should work in most
            # cases for simple expression.
            expression = self._request.filterExpression().expression()
            if expression:
                try:
                    cur = self._provider.con()
                    # Trust boundary: `expression` is a SQL fragment produced
                    # by QGIS from QgsFeatureRequest.filterExpression(). It is
                    # already structured SQL the QGIS core has built; we only
                    # smoke-test that the server can parse it. _from_clause is
                    # composed of regex-validated identifiers (see
                    # _safe_identifier in gizmosql_provider.py).
                    cur.execute(
                        f"SELECT count(*)"  # nosec B608
                        f" FROM {self._provider._from_clause}"
                        f" WHERE {expression}"
                        " LIMIT 0"
                    )
                    cur.close()
                    self._expression = expression
                    where_clause_list.append(expression)
                except Exception:
                    PlgLogger.log(
                        f"GizmoSQL provider does not handle expression: {expression}",
                        log_level=Qgis.MessageLevel.Critical,
                        duration=5,
                        push=False,
                    )
                    self._expression = ""
            else:
                self._expression = ""

        # Apply the subset string filter
        if self._provider.subsetString():
            subset_clause = self._provider.subsetString().replace('"', "")
            where_clause_list.append(subset_clause)

        # Apply the geometry filter
        if not filter_rect.isNull():
            filter_geom_clause = (
                f"st_intersects({geom_column}, "
                f"st_geomfromtext('{filter_rect.asWktPolygon()}'))"
            )
            where_clause_list.append(filter_geom_clause)

        # build the complete where clause
        where_clause = ""
        if where_clause_list:
            where_clause = f"where {where_clause_list[0]}"
            if len(where_clause_list) > 1:
                for clause in where_clause_list[1:]:
                    where_clause += f" and {clause}"

        geom_query = f"st_aswkb({geom_column}), {geom_column}, "
        self._request_no_geometry = (
            self._request.flags() & QgsFeatureRequest.Flag.NoGeometry
        )
        if self._request_no_geometry:
            geom_query = ""

        if self._provider.primary_key() == -1:
            index = "ROW_NUMBER() OVER () as index"
            order_by = "index"
        else:
            index = self._provider._fields[self._provider.primary_key()].name()
            order_by = index

        # All identifiers (column names, _from_clause) are validated; QGIS-
        # generated `where_clause` and the user's optional custom SQL are the
        # explicit trust boundaries documented above.
        final_query = (
            "select * from ("  # nosec B608
            f"select {fields_name_for_query} "
            f"{geom_query} {index} "
            f"from {self._provider._from_clause}) "
            f"{where_clause} "
            f"order by {order_by}"
        )

        if self._settings.debug_mode:
            self.log(
                message="feature iterator execute query: {}".format(final_query),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )

        # Stream the result as Arrow record batches instead of pulling row
        # tuples one at a time. ADBC has already received the data as Arrow
        # over Flight; converting batch-at-a-time to Python lists is markedly
        # cheaper than per-row dbapi.fetchone() bookkeeping. See issue #2 for
        # the related max-message-size fix.
        self._cursor = self._provider.con().cursor()
        self._cursor.execute(final_query)
        self._reader = self._cursor.fetch_record_batch_reader()
        # Cached row-oriented snapshot of the current Arrow record batch.
        # We materialise the batch's columns to Python lists once per batch
        # so per-row access is a plain list lookup.
        self._batch_cols: list[list[Any]] | None = None
        self._batch_row_idx: int = 0
        self._batch_num_rows: int = 0
        self._index = 0

    def _load_next_batch(self) -> bool:
        """Pull the next Arrow record batch from the reader and materialise
        its columns to Python lists for fast row-indexed access. Returns
        False once the stream is exhausted.
        """
        if self._reader is None:
            return False
        try:
            batch = self._reader.read_next_batch()
        except StopIteration:
            return False
        if batch is None or batch.num_rows == 0:
            return False
        self._batch_cols = [
            batch.column(i).to_pylist() for i in range(batch.num_columns)
        ]
        self._batch_num_rows = batch.num_rows
        self._batch_row_idx = 0
        return True

    def fetchFeature(self, f: QgsFeature) -> bool:
        """fetch next feature, return true on success

        :param f: Next feature
        :type f: QgsFeature
        :return: True if success
        :rtype: bool
        """
        if not self._provider.isValid() or self._reader is None:
            f.setValid(False)
            return False

        if self._batch_row_idx >= self._batch_num_rows:
            if not self._load_next_batch():
                f.setValid(False)
                return False

        cols = self._batch_cols
        row = self._batch_row_idx

        f.setFields(self._provider.fields())
        f.setValid(True)

        if not self._request_no_geometry:
            wkb = cols[self.index_geom_column][row]
            if wkb is not None:
                geometry = QgsGeometry()
                geometry.fromWkb(wkb)
                f.setGeometry(geometry)
                self.geometryToDestinationCrs(f, self._transform)

        f.setId(cols[-1][row])

        # set attributes
        if self._attributes_need_conversion:
            if self._request_sub_attributes:
                for idx, attr_idx in enumerate(self._request.subsetOfAttributes()):
                    attribute = self._attributes_converters[idx](cols[idx][row])
                    f.setAttribute(attr_idx, attribute)
            else:
                for idx in range(self.index_geom_column):
                    converted = self._attributes_converters[idx](cols[idx][row])
                    f.setAttribute(idx, converted)
        else:
            if self._request_sub_attributes:
                for idx, attr_idx in enumerate(self._request.subsetOfAttributes()):
                    f.setAttribute(attr_idx, cols[idx][row])
            else:
                f.setAttributes([cols[idx][row] for idx in range(self.index_geom_column)])

        self._batch_row_idx += 1
        self._index += 1
        return True

    def nextFeatureFilterExpression(self, f: QgsFeature) -> bool:
        if not self._expression:
            return super().nextFeatureFilterExpression(f)
        else:
            return self.fetchFeature(f)

    def __iter__(self) -> "GizmoSqlFeatureIterator":
        """Returns self as an iterator object"""
        self._index = 0
        return self

    def __next__(self) -> QgsFeature:
        """Returns the next value till current is lower than high"""
        f = QgsFeature()
        if not self.nextFeature(f):
            raise StopIteration
        else:
            return f

    def rewind(self) -> bool:
        """reset the iterator to the starting position"""
        # virtual bool rewind() = 0;
        if self._index < 0:
            return False
        self._index = 0
        return True

    def close(self) -> bool:
        """end of iterating: free the resources / lock"""
        self._index = -1
        for attr in ("_reader", "_cursor"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
                setattr(self, attr, None)
        self._batch_cols = None
        self._batch_num_rows = 0
        self._batch_row_idx = 0
        return True
