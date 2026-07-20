import time
import os
import sys

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.models.models import Recruiter, Company, PageVisit
from app.models.campaigns import Campaign
from app.routes.analytics import get_dashboard_kpis
from app.models.auth_models import User

# Add SQLAlchemy Event Listener to time queries
query_count = 0
total_sql_time = 0.0

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    global query_count, total_sql_time
    total = time.time() - context._query_start_time
    total_sql_time += total
    query_count += 1
    # print(f"Query {query_count}: {total:.4f}s")

def reset_metrics():
    global query_count, total_sql_time
    query_count = 0
    total_sql_time = 0.0

def profile_function(func, name, *args, **kwargs):
    reset_metrics()
    start_time = time.time()
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(f"Error in {name}: {e}")
    total_time = (time.time() - start_time) * 1000
    print(f"--- {name} ---")
    print(f"Total Time: {total_time:.2f} ms")
    print(f"SQL Queries Executed: {query_count}")
    print(f"Total SQL Time: {(total_sql_time * 1000):.2f} ms")
    print("\n")

if __name__ == "__main__":
    db = SessionLocal()
    # Mock user for testing
    user = db.query(User).first()
    if not user:
        print("No user found in DB.")
        exit(1)
        
    print("=== BACKEND SQL PROFILING ===")
    
    profile_function(get_dashboard_kpis, "Dashboard KPIs", db=db, current_user=user)
    
    # Check N+1 in Recruiters
    def fetch_recruiters():
        recruiters = db.query(Recruiter).limit(50).all()
        # Simulate serialization that hits lazy-loaded relationships
        res = []
        for r in recruiters:
            c = r.company.company_name if r.company else None
            res.append({"name": r.recruiter_name, "company": c})
            
    profile_function(fetch_recruiters, "Fetch 50 Recruiters (N+1 check)")
    
    # Check Companies N+1
    def fetch_companies():
        companies = db.query(Company).limit(50).all()
        for c in companies:
            r_count = len(c.recruiters)
            
    profile_function(fetch_companies, "Fetch 50 Companies + Recruiter Count (N+1 check)")
    
    db.close()
