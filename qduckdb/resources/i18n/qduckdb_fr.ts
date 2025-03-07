<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fr" sourcelanguage="en">
<context>
    <name></name>
    <message>
        <location filename="../../toolbelt/network.py" line="35"/>
        <source>Unable to determine the name of the remote file, a default name will be applied. Trace: {}</source>
        <translation>Impossible de déterminer le nom du fichier distant, un nom par défaut sera appliqué. Trace : {}</translation>
    </message>
</context>
<context>
    <name>Dialog</name>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="32"/>
        <source>DuckDB</source>
        <translation>DuckDB</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="66"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Database&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Base de données&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="45"/>
        <source>Add Layer</source>
        <translation>Ajouter une couche</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="59"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Projection&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Projection&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="144"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Table&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Table&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="38"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Custom SQL query&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Requête SQL personnalisée&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="52"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Extension&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;Extension&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="112"/>
        <source>Entire table</source>
        <translation>Table entière</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.ui" line="122"/>
        <source>Custom SQL query</source>
        <translation>Requête SQL personnalisée</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.ui" line="26"/>
        <source>Open Parquet with DuckDB</source>
        <translation>Ouvrir Parquet avec DuckDB</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.ui" line="32"/>
        <source>Open (Geo)Parquet files with DuckDB</source>
        <translation>Ouvrir des fichiers (Geo)Parquet avec DuckDB</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.ui" line="86"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;You can open one or more parquet files and choose whether or not to group the results. To do this, the plugin doesn&apos;t use QGIS&apos;s native parquet provider; a DuckDB memory base will be created to read the parquet file(s), then the plugin&apos;s QDuckDB provider will be used to create the layer in QGIS.&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-style:italic;&quot;&gt;Vous pouvez ouvrir un ou plusieurs fichiers parquet et choisir de grouper ou non les résultats. Pour ce faire, le plugin n&apos;utilise pas le fournisseur de parquet natif de QGIS ; une base de mémoire DuckDB sera créée pour lire le(s) fichier(s) parquet, puis le fournisseur QDuckDB du plugin sera utilisé pour créer la couche dans QGIS.&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.ui" line="99"/>
        <source>Open</source>
        <translation>Ouvrir</translation>
    </message>
</context>
<context>
    <name>DuckdbProvider</name>
    <message>
        <location filename="../../provider/duckdb_provider.py" line="165"/>
        <source>{} unknown extension, open an issue if it exists to add its support.</source>
        <translation>{} extension inconnue, ouvrez une question si elle existe pour ajouter son support.</translation>
    </message>
    <message>
        <location filename="../../provider/duckdb_provider.py" line="194"/>
        <source>The sql query is invalid: {}</source>
        <translation>La requête SQL n&apos;est pas valide : {}</translation>
    </message>
    <message>
        <location filename="../../provider/duckdb_provider.py" line="268"/>
        <source>Geometry type {} not supported</source>
        <translation>Le type de géométrie {} n&apos;est pas pris en charge</translation>
    </message>
    <message>
        <location filename="../../provider/duckdb_provider.py" line="489"/>
        <source>SQL error in filter : {}</source>
        <translation>Erreur SQL dans le filtre : {}</translation>
    </message>
</context>
<context>
    <name>LoadDuckDBLayerDialog</name>
    <message>
        <location filename="../../gui/dlg_add_duckdb_layer.py" line="146"/>
        <source>The database {} does not exist.</source>
        <translation>La base de données {} n&apos;existe pas.</translation>
    </message>
</context>
<context>
    <name>OpenParquetDialog</name>
    <message>
        <location filename="../../gui/dlg_open_parquet.py" line="129"/>
        <source>The parquet file {} does not exist.</source>
        <translation type="obsolete">Le fichier parquet {} n&apos;existe pas.</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.py" line="148"/>
        <source>{} is not a valid URL</source>
        <translation type="obsolete">{} n&apos;est pas une URL valide</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_open_parquet.py" line="74"/>
        <source>Unable to determine the name of the remote file, a default name will be applied. Trace: {}</source>
        <translation type="obsolete">Impossible de déterminer le nom du fichier distant, un nom par défaut sera appliqué. Trace : {}</translation>
    </message>
</context>
<context>
    <name>QduckdbPlugin</name>
    <message>
        <location filename="../../plugin_main.py" line="127"/>
        <source>Help</source>
        <translation>Aide</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="136"/>
        <source>Settings</source>
        <translation>Paramètres</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="147"/>
        <source>DuckDB</source>
        <translation>DuckDB</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="155"/>
        <source>Open (geo)Parquet with DuckDB</source>
        <translation>Ouvrir un fichier (geo)Parquer avec DuckDB</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="257"/>
        <source>Error importing dependencies. Plugin disabled.</source>
        <translation>Erreur dans l&apos;importation des dépendances. Plugin désactivé.</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="274"/>
        <source>Plugin disabled. Please install all dependencies and then restart QGIS. Refer to the documentation for more information.</source>
        <translation>Plugin désactivé. Veuillez installer toutes les dépendances et redémarrer QGIS. Reportez-vous à la documentation pour plus d&apos;informations.</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="281"/>
        <source>Dependencies satisfied</source>
        <translation>Dépendances satisfaites</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="257"/>
        <source>How to fix it...</source>
        <translation>Comment y remédier...</translation>
    </message>
</context>
<context>
    <name>QduckdbServerPlugin</name>
    <message>
        <location filename="../../plugin_main.py" line="297"/>
        <source>Error importing dependencies. Plugin disabled.</source>
        <translation>Erreur dans l&apos;importation des dépendances. Plugin désactivé.</translation>
    </message>
    <message>
        <location filename="../../plugin_main.py" line="305"/>
        <source>Dependencies satisfied</source>
        <translation>Dépendances satisfaites</translation>
    </message>
</context>
<context>
    <name>wdg_qduckdb_settings</name>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="14"/>
        <source>QDuckDB - Settings</source>
        <translation>QDuckDB - Paramètres</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="44"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p align=&quot;center&quot;&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;PluginTitle - Version X.X.X&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p align=&quot;center&quot;&gt;&lt;span style=&quot; font-weight:600;&quot;&gt;PluginTitle - Version X.X.X&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="75"/>
        <source>Miscellaneous</source>
        <translation>Divers</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="124"/>
        <source>Report an issue</source>
        <translation>Créer un ticket</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="146"/>
        <source>Version used to save settings:</source>
        <translation>Version utilisée pour sauvegarder les paramètres:</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="168"/>
        <source>Help</source>
        <translation>Aide</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="190"/>
        <source>Reset setttings to factory defaults</source>
        <translation>Réinitialiser les paramètres par défaut</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="209"/>
        <source>Enable debug mode.</source>
        <translation>Activer le mode debug.</translation>
    </message>
    <message>
        <location filename="../../gui/dlg_settings.ui" line="218"/>
        <source>Debug mode (degraded performances)</source>
        <translation>Mode debug (performances dégradées)</translation>
    </message>
</context>
</TS>
