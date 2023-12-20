from pathlib import Path

from qgis.core import (
    Qgis,
    QgsPathResolver,
    QgsProject,
    QgsProviderRegistry,
    QgsReadWriteContext,
)
from qgis.testing import start_app, unittest

from .utilities import register_provider_if_necessary


class TestQDuckDBProviderMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Run before all tests"""
        super(TestQDuckDBProviderMetadata, cls).setUpClass()

        start_app()

        # Register the provider if it has not been loaded yet
        register_provider_if_necessary()

        cls.provider_metadata = QgsProviderRegistry.instance().providerMetadata(
            "duckdb"
        )

        cls.base_path = "/home/foo/project"
        cls.db_filename = "./database.path"
        cls.full_path = str(Path(cls.base_path) / Path(cls.db_filename))
        cls.project_path = str(Path(cls.base_path) / Path("project.qgs"))

        cls.table = "mytable"
        cls.epsg = 4326

        cls.expected_abs_uri = f"path={cls.full_path} table={cls.table} epsg={cls.epsg}"
        cls.expected_rel_uri = (
            f"path={cls.db_filename} table={cls.table} epsg={cls.epsg}"
        )

    def test_encode_uri(self):
        # encoding does not have any effect on the path

        abs_parts = {"path": self.full_path, "table": self.table, "epsg": self.epsg}
        abs_uri = self.provider_metadata.encodeUri(abs_parts)
        self.assertEqual(abs_uri, self.expected_abs_uri)

        rel_parts = {"path": self.db_filename, "table": self.table, "epsg": self.epsg}
        uri = self.provider_metadata.encodeUri(rel_parts)
        self.assertEqual(uri, self.expected_rel_uri)

    def test_decode_uri(self):
        # it should always return an absolute path

        qgs_project_filenames = ["", self.project_path]
        for project_filename in qgs_project_filenames:
            QgsProject.instance().setFileName(project_filename)

            # path is absolute
            # it returns an absolute path
            abs_parts = self.provider_metadata.decodeUri(self.expected_abs_uri)
            self.assertEqual(abs_parts["path"], self.full_path)
            self.assertEqual(abs_parts["table"], self.table)
            self.assertEqual(int(abs_parts["epsg"]), self.epsg)

            # path is relative
            # - returns a relative path since QGIS 3.30
            # - returns an absolute path prior to QGIS 3.30
            # This change of behavior was necessary to prevent a
            # QGIS limitation with older QGIS versions.
            # See DuckdbProviderMetadata::decodeUri() code for a full
            # explanation
            if Qgis.QGIS_VERSION_INT < 33000:
                expected_path = self.full_path
            else:
                expected_path = self.rel_path

            rel_parts = self.provider_metadata.decodeUri(self.expected_abs_uri)
            self.assertEqual(rel_parts["path"], expected_path)
            self.assertEqual(rel_parts["table"], self.table)
            self.assertEqual(int(rel_parts["epsg"]), self.epsg)

        QgsProject.instance().setFileName("")

    def test_absolute_to_relative_uri(self):
        ctx = QgsReadWriteContext()

        #
        # 1. no context path defined
        #
        ctx.setPathResolver(QgsPathResolver(""))

        # absolute uri is unchanged
        rel_path = self.provider_metadata.absoluteToRelativeUri(
            self.expected_abs_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_abs_uri)

        # relative uri is unchanged
        rel_path = self.provider_metadata.absoluteToRelativeUri(
            self.expected_rel_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_rel_uri)

        #
        # 2. context path defined
        #
        ctx.setPathResolver(QgsPathResolver(self.project_path))

        # absolute uri becomes relative
        rel_path = self.provider_metadata.absoluteToRelativeUri(
            self.expected_abs_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_rel_uri)

        # relative uri is unchanged
        rel_path = self.provider_metadata.absoluteToRelativeUri(
            self.expected_rel_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_rel_uri)

    def test_relative_to_absolute_uri(self):
        ctx = QgsReadWriteContext()

        #
        # 1. no context path defined
        #
        ctx.setPathResolver(QgsPathResolver(""))

        # absolute uri is unchanged
        rel_path = self.provider_metadata.relativeToAbsoluteUri(
            self.expected_abs_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_abs_uri)

        # relative uri is unchanged
        rel_path = self.provider_metadata.relativeToAbsoluteUri(
            self.expected_rel_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_rel_uri)

        #
        # 2. context path defined
        #
        ctx.setPathResolver(QgsPathResolver(self.project_path))

        # absolute uri is unchanged
        rel_path = self.provider_metadata.relativeToAbsoluteUri(
            self.expected_abs_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_abs_uri)

        # relative uri becomes absolute
        rel_path = self.provider_metadata.relativeToAbsoluteUri(
            self.expected_rel_uri, ctx
        )
        self.assertEqual(rel_path, self.expected_abs_uri)
