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


class DuckdbFeatureIterator(QgsAbstractFeatureIterator):
    def __init__(
        self,
        source: duckdb_feature_source.DuckdbFeatureSource,
        request: QgsFeatureRequest,
    ):
        """Constructor"""
        # FIXME: Handle QgsFeatureRequest.FilterExpression
        super().__init__(request)
        self._provider: duckdb_provider.DuckdbProvider = source.get_provider()

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

        table = self._provider.get_table()
        geom_column = self._provider.get_geometry_column()

        list_field_names = []
        for field in self._provider.fields():
            list_field_names.append(field.name())

        fields_name_for_query = ", ".join(list_field_names)
        self.index_geom_column = len(list_field_names)

        # Create fid/fids list
        feature_id_list = None
        if (
            self._request.filterType() == self._request.FilterFid
            or self._request.filterType() == self._request.FilterFids
        ):
            feature_id_list = (
                [self._request.filterFid()]
                if self._request.filterType() == self._request.FilterFid
                else self._request.filterFids()
            )

        where_clause = ""

        if feature_id_list and not filter_rect.isNull():
            if self._provider.primary_key() == -1:
                where_clause = (
                    f"where st_intersects({geom_column}, "
                    f"st_geomfromtext('{filter_rect.asWktPolygon()}'))"
                    f"and index in {tuple(feature_id_list)}"
                )

            else:
                primary_key_name = list_field_names[self._provider.primary_key()]
                where_clause = (
                    f"where st_intersects({geom_column}, "
                    f"st_geomfromtext('{filter_rect.asWktPolygon()}'))"
                    f"and {primary_key_name} in {tuple(feature_id_list)}"
                )

        if feature_id_list and filter_rect.isNull():
            if self._provider.primary_key() == -1:
                where_clause = f"where index in {tuple(feature_id_list)}"

            else:
                primary_key_name = list_field_names[self._provider.primary_key()]
                where_clause = f"where {primary_key_name} in {tuple(feature_id_list)}"

        if not filter_rect.isNull() and not feature_id_list:
            where_clause = (
                f"where st_intersects({geom_column}, "
                f"st_geomfromtext('{filter_rect.asWktPolygon()}'))"
            )

        self._result = self._provider.con().execute(
            f"select * from (select {fields_name_for_query}, "
            f"st_astext({geom_column}), {geom_column}, row_number() over() as index from {self._provider._from_clause}) "
            f"{where_clause} order by index"
        )
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
        f.setValid(self._provider.isValid())
        geometry = QgsGeometry.fromWkt(next_result[self.index_geom_column])
        f.setGeometry(geometry)
        self.geometryToDestinationCrs(f, self._transform)

        if self._provider.primary_key() == -1:
            # the table does not have a primary key, use the row number as fallback
            f.setId(next_result[-1])
        else:
            f.setId(next_result[self._provider.primary_key()])

        for enum in range(self.index_geom_column):
            f.setAttribute(enum, next_result[enum])

        self._index += 1
        return True

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
