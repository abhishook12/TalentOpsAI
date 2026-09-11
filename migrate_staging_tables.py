"""
Creates/migrates all missing staging and knowledge tables in PostgreSQL.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import engine, Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.extension_models import (
    ExtensionDevice,
    ExtensionActivationCode,
    ExtensionHeartbeat,
    ExtensionSubmissionLog,
    ExtensionDiscoveryEvent
)
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.knowledge_models import (
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeSignal,
    SemanticObservation
)


def run_migrations():
    print("Connecting to live database and ensuring all tables exist...")
    Base.metadata.create_all(bind=engine)
    print("All tables successfully created/verified in PostgreSQL!")


if __name__ == "__main__":
    run_migrations()
