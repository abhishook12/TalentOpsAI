with open('app/routes/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Add auth
if 'get_current_user_from_request' not in content:
    content = content.replace('from ..database import get_db', 'from ..database import get_db\nfrom ..services.auth_service import get_current_user_from_request\nfrom ..models.auth_models import User')

content = re.sub(r'(def [a-zA-Z0-9_]+\(.*?)db: Session = Depends\(get_db\)(.*?)\):',
                 r'\1db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)\2):',
                 content)

# Fix SQLAlchemy counts
content = content.replace('db.query(Company).count()', 'db.query(Company).filter(Company.user_id == current_user.id).count()')
content = content.replace('db.query(Vendor).count()', 'db.query(Vendor).filter(Vendor.user_id == current_user.id).count()')

# Now fix raw SQL. 
content = content.replace('FROM page_visits', 'FROM page_visits WHERE user_email = :user_email AND')
content = content.replace('WHERE user_email = :user_email AND WHERE', 'WHERE user_email = :user_email AND')
content = content.replace('WHERE user_email = :user_email AND GROUP', 'WHERE user_email = :user_email GROUP')

content = content.replace('FROM action_logs', 'FROM action_logs WHERE user_email = :user_email AND')
content = content.replace('WHERE user_email = :user_email AND WHERE', 'WHERE user_email = :user_email AND')

content = content.replace('FROM recruiters r', 'FROM recruiters r WHERE r.user_id = :user_id AND')
content = content.replace('WHERE r.data_source', 'WHERE r.user_id = :user_id AND r.data_source')
content = content.replace('WHERE location IS NOT NULL', 'WHERE user_id = :user_id AND location IS NOT NULL')
content = content.replace('WHERE created_at >=', 'WHERE user_id = :user_id AND created_at >=')

# Parameters
content = content.replace('{"since": seven_days_ago}', '{"since": seven_days_ago, "user_email": current_user.email}')
content = content.replace('{"since": thirty_days_ago}', '{"since": thirty_days_ago, "user_email": current_user.email}')
content = content.replace('{"s": today_start}', '{"s": today_start, "user_id": current_user.id, "user_email": current_user.email}')
content = content.replace('{"s": yesterday_start, "e": today_start}', '{"s": yesterday_start, "e": today_start, "user_id": current_user.id, "user_email": current_user.email}')
content = content.replace('{}', '{"user_id": current_user.id}')
content = content.replace('")).mappings().all()', '"), {"user_email": current_user.email, "user_id": current_user.id}).mappings().all()')
content = content.replace('")).fetchall()', '"), {"user_email": current_user.email, "user_id": current_user.id}).fetchall()')
content = content.replace('")).scalar()', '"), {"user_email": current_user.email, "user_id": current_user.id}).scalar()')
content = content.replace('")).fetchone()', '"), {"user_email": current_user.email, "user_id": current_user.id}).fetchone()')
content = content.replace('FROM page_visits")).scalar()', 'FROM page_visits"), {"user_email": current_user.email}).scalar()')

with open('app/routes/analytics_new.py', 'w', encoding='utf-8') as f:
    f.write(content)
