import duckdb
from datetime import datetime, timedelta, timezone

con = duckdb.connect()
cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
res = con.execute("SELECT CAST(? AS TIMESTAMP)", [cutoff]).fetchone()
print("DuckDB explicit cutoff test:", res)

