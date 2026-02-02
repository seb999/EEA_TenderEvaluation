from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event

from models import Applicant, Question, ApplicantAnswer, AssessmentResult, SearchKeyword, LLMConfig, PDFOCRCache

DATABASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'tender_evaluation.db'}"

# Enable foreign key constraints for SQLite (required for CASCADE DELETE)
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Enable foreign keys for each connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for each new connection"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session
