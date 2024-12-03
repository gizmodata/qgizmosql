from pathlib import Path

import duckdb

db_path = Path("tests/fixtures/unitests_database.db")

if db_path.exists():
    db_path.unlink()

db = duckdb.connect(db_path)
db.sql("INSTALL SPATIAL ; LOAD SPATIAL")

with open("tests/fixtures/build_unitests_database.sql", "r") as file:
    sql_content = file.read()
    db.sql(sql_content)

db.close()
