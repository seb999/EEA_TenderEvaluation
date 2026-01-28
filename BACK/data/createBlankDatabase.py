from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

from models import Applicant, Question, ApplicantAnswer, AssessmentResult, SearchKeyword, LLMConfig, PDFOCRCache

DATABASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'tender_evaluation.db'}"

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session
