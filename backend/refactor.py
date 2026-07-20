import re
import os

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add import for User and get_current_user_from_request
    if "get_current_user_from_request" not in content:
        content = content.replace("from ..database import get_db", "from ..database import get_db\nfrom ..services.auth_service import get_current_user_from_request\nfrom ..models.auth_models import User")

    # 2. Add current_user to route definitions
    # Find all def ... (..., db: Session = Depends(get_db)):
    # and replace with def ... (..., db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    content = re.sub(r'(def [a-zA-Z0-9_]+\(.*?)db: Session = Depends\(get_db\)(.*?)\):',
                     r'\1db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)\2):',
                     content)

    # 3. Add user_id filter to db.query(Campaign)
    content = content.replace("db.query(Campaign).filter(", "db.query(Campaign).filter(Campaign.user_id == current_user.id, ")
    content = content.replace("db.query(Campaign).order_by(", "db.query(Campaign).filter(Campaign.user_id == current_user.id).order_by(")
    content = content.replace("db.query(Campaign).all()", "db.query(Campaign).filter(Campaign.user_id == current_user.id).all()")
    content = content.replace("s_db.query(Campaign.status).filter(", "s_db.query(Campaign.status).filter(Campaign.user_id == current_user.id, ")

    # Do the same for EmailSignature
    content = content.replace("db.query(EmailSignature).filter(", "db.query(EmailSignature).filter(EmailSignature.user_id == current_user.id, ")
    content = content.replace("db.query(EmailSignature).order_by(", "db.query(EmailSignature).filter(EmailSignature.user_id == current_user.id).order_by(")
    content = content.replace("EmailSignature.user_email == user_email", "EmailSignature.user_id == current_user.id")
    content = content.replace("EmailSignature.user_email == sig.user_email", "EmailSignature.user_id == current_user.id")

    # Do the same for EmailTemplate
    content = content.replace("db.query(EmailTemplate).filter(", "db.query(EmailTemplate).filter(EmailTemplate.user_id == current_user.id, ")

    # Handle creation logic to inject user_id
    content = content.replace("Campaign(**payload.model_dump())", "Campaign(**payload.model_dump(), user_id=current_user.id)")
    content = content.replace("EmailTemplate(campaign_id=campaign_id, **payload.model_dump())", "EmailTemplate(campaign_id=campaign_id, user_id=current_user.id, **payload.model_dump())")
    
    # Save it back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Refactored {filepath}")

refactor_file("app/routes/campaigns.py")
