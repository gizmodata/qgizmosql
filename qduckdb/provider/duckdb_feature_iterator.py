# standard
from __future__ import (
    annotations,  # used to manage type annotation for method that return Self in Python < 3.11
)

# PyQGIS
from qgis.core import (
    QgsAbstractFeatureIterator,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
)

# plugin
from qduckdb.provider import duckdb_feature_source, duckdb_provider
from qduckdb.toolbelt.log_handler import PlgLogger
from qduckdb.toolbelt.preferences import PlgOptionsManager


class DuckdbFeatureIterator(QgsAbstractFeatureIterator):
    def __init__(
        self,
        source: duckdb_feature_source.DuckdbFeatureSource,
        request: QgsFeatureRequest,
    ):
        """Constructor"""
        super().__init__(request)
        self._provider: duckdb_provider.DuckdbProvider = source.get_provider()
        self._settings = PlgOptionsManager.get_plg_settings()
        self.log = PlgLogger().log

        self._request = request if request is not None else QgsFeatureRequest()
        self._transform = QgsCoordinateTransform()

        if (
            self._request.destinationCrs().isValid()
            and self._request.destinationCrs() != source._provider.crs()
        ):
            self._transform = QgsCoordinateTransform(
                source._provider.crs(),
                self._request.destinationCrs(),
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

        # Create the list of fields that need to be retrieved
        self._request_sub_attributes = (
            self._request.flags() & QgsFeatureRequest.Flag.SubsetOfAttributes
        )
        if self._request_sub_attributes and not self._provider.subsetString():
            list_field_names = [
                self._provider.fields()[idx].name()
                for idx in self._request.subsetOfAttributes()
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
        if (
            self._request.filterType() == QgsFeatureRequest.FilterFid
            or self._request.filterType() == QgsFeatureRequest.FilterFids
        ):
            feature_id_list = (
                [self._request.filterFid()]
                if self._request.filterType() == QgsFeatureRequest.FilterFid
                else self._request.filterFids()
            )

        where_clause_list = []
        if feature_id_list:
            if self._provider.primary_key() == -1:
                feature_clause = f"index in {tuple(feature_id_list)}"
            else:
                primary_key_name = list_field_names[self._provider.primary_key()]
                feature_clause = f"{primary_key_name} in {tuple(feature_id_list)}"

            where_clause_list.append(feature_clause)

        # Apply the filter expression
        if self._request.filterType() == QgsFeatureRequest.FilterExpression:
            # A provider is supposed to implement a QgsSqlExpressionCompiler
            # in order to handle expression. However, this class is not
            # available in the Python bindings.
            # Try to use the expression as is. It should work in most
            # cases for simple expression.
            expression = self._request.filterExpression().expression()
            if expression:
                try:
                    self._provider.con().sql(
                        f"SELECT count(*)"
                        f" FROM {self._provider._from_clause}"
                        f" WHERE {expression}"
                        " LIMIT 0"
                    )
                    self._expression = expression
                    where_clause_list.append(expression)
                except Exception:
                    PlgLogger.log(
                        f"Duckdb provider does not handle expression: {expression}",
                        log_level=2,
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

        final_query = (
            "select * from ("
            f"select {fields_name_for_query} "
            f"{geom_query} "
            f"rowid + 1 as index "
            f"from {self._provider._from_clause}) "
            f"{where_clause} "
            "order by index"
        )

        if self._settings.debug_mode:
            self.log(
                message="feature iterator execute query: {}".format(final_query),
                log_level=4,  # 4 = info
                push=False,
            )

        self._result = self._provider.con().execute(final_query)
        self._index = 0

    def fetchFeature(self, f: QgsFeature) -> bool:
        """fetch next feature, return true on success

        :param f: Next feature
        :type f: QgsFeature
        :return: True if success
        :rtype: bool
        """
        next_result = self._result.fetchone()

        if not next_result or not self._provider.isValid():
            f.setValid(False)
            return False

        f.setFields(self._provider.fields())
        f.setValid(True)

        if not self._request_no_geometry:
            geometry = QgsGeometry()
            geometry.fromWkb(next_result[self.index_geom_column])
            f.setGeometry(geometry)
            self.geometryToDestinationCrs(f, self._transform)

        if self._provider.primary_key() == -1:
            # the table does not have a primary key, use rowid as fallback
            f.setId(next_result[-1])
        else:
            f.setId(next_result[self._provider.primary_key()])

        # set attributes
        if self._request_sub_attributes:
            for idx, attr_idx in enumerate(self._request.subsetOfAttributes()):
                f.setAttribute(attr_idx, next_result[idx])
        else:
            f.setAttributes(list(next_result[: self.index_geom_column]))

        self._index += 1
        return True

    def nextFeatureFilterExpression(self, f: QgsFeature) -> bool:
        if not self._expression:
            return super().nextFeatureFilterExpression(f)
        else:
            return self.fetchFeature(f)

    def __iter__(self) -> DuckdbFeatureIterator:
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
        # virtual bool close() = 0;
        self._index = -1
        return True
