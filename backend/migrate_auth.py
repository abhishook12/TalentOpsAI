from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'"))
            print("Added auth_provider")
        except Exception as e:
            print("auth_provider exists or error:", e)

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN provider_id VARCHAR(255)"))
            print("Added provider_id")
        except Exception as e:
            print("provider_id exists or error:", e)

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
            print("Added avatar_url")
        except Exception as e:
            print("avatar_url exists or error:", e)
            
        try:
            # Need to drop NOT NULL constraint on password_hash. In sqlite we can't easily, but postgres we can.
            if engine.url.drivername.startswith("postgres"):
                conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
                print("Altered password_hash drop not null")
        except Exception as e:
            print("alter password_hash error:", e)

if __name__ == "__main__":
    migrate()
