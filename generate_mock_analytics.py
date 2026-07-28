import sqlite3
import random
from datetime import datetime, timedelta

def generate_mock_data():
    conn = sqlite3.connect(r'C:\TalentOpsAI\backend\dev.db')
    c = conn.cursor()
    
    # 1. Update Recruiters with random states
    states = [
        'CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI',
        'WA', 'VA', 'CO', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI'
    ]
    
    # Update recruiters to have states
    c.execute("UPDATE recruiters SET state = ? WHERE recruiter_id % 20 = ?", ('CA', 0))
    for i, state in enumerate(states):
        c.execute("UPDATE recruiters SET state = ? WHERE recruiter_id % 20 = ?", (state, i))
    
    # 2. Generate Page Visits for admin@talentops.com
    now = datetime.utcnow()
    pages = ['/dashboard', '/recruiters', '/campaigns', '/analytics', '/directory']
    
    # Generate 500 visits over the last 30 days
    visits = []
    for _ in range(500):
        days_ago = random.randint(0, 30)
        visit_time = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        page = random.choice(pages)
        visits.append((
            'admin@talentops.com',
            'session_mock_123',
            page,
            visit_time.isoformat(),
            'Mock IP',
            'Windows',
            'Chrome'
        ))
        
    c.executemany("""
        INSERT INTO page_visits (user_email, session_id, page, path, visited_at, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(v[0], v[1], v[2], v[2], v[3], v[4], 'Mock User Agent') for v in visits])
    
    # 3. Add to Action Logs for Searches
    searches = []
    for _ in range(50):
        days_ago = random.randint(0, 5)
        search_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        searches.append((
            'admin@talentops.com',
            'SEARCH_RECRUITERS',
            '{"query": "software"}',
            search_time.isoformat()
        ))
        
    c.executemany("""
        INSERT INTO action_logs (user_email, action_type, details, created_at)
        VALUES (?, ?, ?, ?)
    """, searches)
    
    conn.commit()
    conn.close()
    print("Mock analytics data generated successfully.")

if __name__ == "__main__":
    generate_mock_data()
