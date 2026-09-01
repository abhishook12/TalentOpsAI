import sys
from app.database import engine, Base
from app.models.models import *
from app.models.auth_models import *
from app.models.extension_models import *

print("Creating extension database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: Extension database tables created successfully.")
except Exception as e:
    print(f"Error creating tables: {e}")
    sys.exit(1)
