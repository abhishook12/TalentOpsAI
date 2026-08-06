import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import engine, Base
from app.models.models import DomainIntelligence
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    # Create the DomainIntelligence table
    logger.info("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")

    # Alter recruiters table
    logger.info("Altering recruiters table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN company_confidence INTEGER DEFAULT 0;"))
            logger.info("Added company_confidence.")
        except ProgrammingError as e:
            if 'already exists' in str(e):
                logger.info("company_confidence already exists.")
            else:
                logger.error(f"Error adding company_confidence: {e}")
                
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN company_reasoning TEXT;"))
            logger.info("Added company_reasoning.")
        except ProgrammingError as e:
            if 'already exists' in str(e):
                logger.info("company_reasoning already exists.")
            else:
                logger.error(f"Error adding company_reasoning: {e}")
                
        conn.commit()

    logger.info("Migration complete.")

if __name__ == "__main__":
    run_migration()
