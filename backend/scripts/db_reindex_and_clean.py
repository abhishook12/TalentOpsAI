import sys, os, io, time, psycopg
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join('C:/TalentOpsAI/backend', '.env'))

def reindex_and_vacuum():
    print("=== DATABASE DE-BLOAT & REINDEX ENGINE ===")
    raw_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL') or ''
    db_url = raw_url.replace('postgresql+psycopg://', 'postgresql://')

    conn = psycopg.connect(db_url, autocommit=True, prepare_threshold=None)
    cursor = conn.cursor()

    cursor.execute("SELECT pg_database_size(current_database()) / 1048576.0")
    print(f"Size Before De-bloat: {float(cursor.fetchone()[0]):.2f} MB")

    print("\n[1/3] Reindexing companies table...")
    cursor.execute("REINDEX TABLE companies")
    cursor.execute("VACUUM VERBOSE companies")
    print(" -> companies reindexed & vacuumed.")

    print("\n[2/3] Reindexing enrichment_results table...")
    cursor.execute("REINDEX TABLE enrichment_results")
    cursor.execute("VACUUM VERBOSE enrichment_results")
    print(" -> enrichment_results reindexed & vacuumed.")

    print("\n[3/3] Reindexing recruiters table (rebuilding 18 B-Tree indexes without bloat)...")
    start_r = time.time()
    cursor.execute("REINDEX TABLE recruiters")
    cursor.execute("VACUUM VERBOSE recruiters")
    print(f" -> recruiters reindexed & vacuumed in {round(time.time() - start_r, 2)}s.")

    cursor.execute("SELECT pg_database_size(current_database()) / 1048576.0")
    final_mb = float(cursor.fetchone()[0])
    print(f"\n📊 Exact Database Size After Reindex & De-bloat: {final_mb:.2f} MB")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    reindex_and_vacuum()
