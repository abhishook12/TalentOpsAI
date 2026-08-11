import sys
from app.database import SessionLocal
from app.models.auth_models import User, ConnectedEmailAccount

email = sys.argv[1]
with SessionLocal() as db:
    user = db.query(User).filter(User.email == email).first()
    if user:
        acc = ConnectedEmailAccount(
            user_id=user.id,
            provider="microsoft",
            email_address="sender@test.com",
            access_token="mock",
            status="connected"
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        print(acc.account_id)
    else:
        print("0")
