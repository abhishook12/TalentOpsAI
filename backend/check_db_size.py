from dotenv import load_dotenv
load_dotenv()
from app.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    size_result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database())) as size, pg_database_size(current_database()) as raw_size;")).fetchone()
    print('Database Size:', size_result.size, '(', round(size_result.raw_size / (1024*1024), 2), 'MB)')
    
    tables_query = """
        SELECT relname as table_name, pg_size_pretty(pg_total_relation_size(relid)) as total_size,
        pg_total_relation_size(relid) as raw_size
        FROM pg_catalog.pg_statio_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT 5;
    """
    tables = conn.execute(text(tables_query)).fetchall()
    print('\nTop 5 Largest Tables:')
    for t in tables:
        print(f'- {t.table_name}: {t.total_size}')
