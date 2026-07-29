from app.database import SessionLocal
from app.models.auth_models import User, Role

def run_checks():
    db = SessionLocal()
    try:
        email = "abhishek.jadon@technovion.com"
        user = db.query(User).filter(User.email == email).first()
        admin_role = db.query(Role).filter(Role.name == 'admin').first()
        
        if not user:
            user = User(
                email=email,
                first_name="Abhishek",
                last_name="Jadon",
                status="Active",
                role_id=admin_role.id if admin_role else None
            )
            db.add(user)
        else:
            user.status = "Active"
            user.role_id = admin_role.id if admin_role else None
            
        db.commit()
        print(f"Updated user {email}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_checks()
