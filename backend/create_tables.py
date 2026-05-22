from app.database import engine, Base
from app.models import models

# This will create tables that don't exist yet
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
