import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import engine, Base
from app.models.models import UploadJob

Base.metadata.create_all(bind=engine)
print("Table created.")
