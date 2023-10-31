from pathlib import Path

import duckdb

csv_path = Path(__file__).parent.parent.joinpath("fixtures/capitals.csv")
output_db = csv_path.with_suffix(".db")

# connect (= create if not exists) to a database related to the input CSV file
con = duckdb.connect(database=f"{output_db}", read_only=False)

# make sure that spatial stuff is here
con.sql(
    query="""
        INSTALL spatial;
        LOAD spatial;
        """
)


# load data from CSV into a temporary table
con.execute(
    query=f"CREATE TEMP TABLE temp_table AS SELECT * FROM read_csv_auto('{csv_path}');"
)


# drop and recreate a table importing geometry from temporary table
con.execute(query="DROP TABLE IF EXISTS capitals;")
con.execute(
    query="CREATE TABLE capitals AS SELECT *, "
    "ST_Point(longitude, latitude) AS geom "
    "FROM temp_table;"
)

# check if data has been loaded
result = con.execute(query="SELECT * FROM capitals LIMIT 5;").fetchall()
print(result)

# properly close
con.close()

# output_db.unlink()
