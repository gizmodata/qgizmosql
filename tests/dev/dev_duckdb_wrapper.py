"""Script to rougthly test DuckDB wrapper

Usage:

    python tests/dev/dev_duckdb_wrapper.py 
"""

import sys
from pathlib import Path

sys.path.insert(0, f"{Path('.').resolve()}")  # move into project package

from qduckdb.provider.duckdb_wrapper import DuckDbTools

csv_path = Path(__file__).parent.parent.joinpath("fixtures/capitals.csv")
output_db = csv_path.with_suffix(".db")
sql_request = f"""
                CREATE TEMP TABLE temp_table AS SELECT *
                    FROM read_csv_auto('{csv_path}');
                DROP TABLE IF EXISTS capitals;
                CREATE TABLE capitals AS SELECT *, ST_Point(longitude, latitude) AS geom
                    FROM temp_table;
                """

if output_db.exists():
    output_db.unlink()

ddb_wrapper = DuckDbTools(database_path=output_db.resolve(), auto_setup_spatial=True)


# load data from CSV into a temporary table
ddb_wrapper.run_sql(
    read_only=False, requires_spatial=True, results_fetcher=None, query_sql=sql_request
)


result = ddb_wrapper.run_sql(
    read_only=True, requires_spatial=False, query_sql="SELECT * FROM capitals LIMIT 5;"
)
assert isinstance(result, list)
print(result)
