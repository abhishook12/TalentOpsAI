from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    res = conn.execute(text("UPDATE companies SET logo_url = 'https://logo.clearbit.com/' || primary_domain, verification_status = 'verified' WHERE logo_url IS NULL AND primary_domain IS NOT NULL"))
    print('Updated logos:', res.rowcount)
