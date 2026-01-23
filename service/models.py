from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

class Applicant(SQLModel, table=True):
    """Applicant/Vendor model for storing uploaded tender applications"""
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_name: str = Field(index=True)
    filename: str
    file_path: str
    file_size: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="uploaded")  # uploaded, processing, completed, error

    # Additional fields for tender evaluation
    evaluation_score: Optional[float] = None
    evaluation_result: Optional[str] = None  # JSON string with detailed results
    processed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "vendor_name": "Acme Corp",
                "filename": "Acme Corp.pdf",
                "file_path": "uploads/Acme Corp.pdf",
                "file_size": 1024000,
                "status": "uploaded"
            }
        }


class Question(SQLModel, table=True):
    """Evaluation question model for LLM prompts"""
    id: Optional[int] = Field(default=None, primary_key=True)
    q_id: str = Field(index=True, unique=True)  # e.g., "Q2"
    prompt_json: str = Field(sa_column=Column(JSON))  # Full prompt structure as JSON
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)  # To enable/disable questions

    # PDF search configuration
    search_label: str = Field(default="Criterion")  # Label to search in PDF (e.g., "Criterion", "Section")
    auto_increment: bool = Field(default=True)  # If true, appends question number to search_label

    class Config:
        json_schema_extra = {
            "example": {
                "q_id": "Q2",
                "prompt_json": {
                    "question": "Explain how you organise your team...",
                    "scale": "0-5",
                    "required_evidence": ["team structure", "governance"],
                    "evaluation_guidance": ["Score higher for specific answers"],
                    "output_format": {"score": "integer 0-5", "justification": "text"}
                },
                "search_label": "Criterion",
                "auto_increment": True
            }
        }


class ApplicantAnswer(SQLModel, table=True):
    """Stores applicant answers to specific questions"""
    id: Optional[int] = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    q_id: str = Field(index=True)  # Question ID (e.g., "Q2")
    answer_text: str  # The actual answer content
    source: str = Field(default="extracted")  # "extracted" or "manual"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "applicant_id": 1,
                "q_id": "Q2",
                "answer_text": "Our team is organized with...",
                "source": "extracted"
            }
        }


class AssessmentResult(SQLModel, table=True):
    """Stores LLM assessment results for applicant answers"""
    id: Optional[int] = Field(default=None, primary_key=True)
    applicant_id: int = Field(foreign_key="applicant.id", index=True)
    q_id: str = Field(index=True)  # Question ID (e.g., "Q2")
    question_text: str  # The actual question text
    answer_text: str  # The answer that was evaluated
    score: Optional[float] = None  # Numeric score extracted from LLM response
    justification: Optional[str] = None  # Justification text from LLM
    llm_response: str  # Full raw LLM response
    parsed_result: Optional[str] = None  # JSON string of parsed LLM response
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "applicant_id": 1,
                "q_id": "Q2",
                "question_text": "Explain how you organise your team...",
                "answer_text": "Our team is organized with...",
                "score": 4.5,
                "justification": "The response demonstrates...",
                "llm_response": "{\"score\": 4.5, \"justification\": \"...\"}",
                "parsed_result": "{\"score\": 4.5, \"justification\": \"...\"}"
            }
        }


class SearchKeyword(SQLModel, table=True):
    """Stores configurable search keywords for PDF extraction"""
    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str = Field(index=True)  # e.g., "Criterion", "Award Criterion", "Section"
    is_active: bool = Field(default=True)  # Enable/disable keywords
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "Criterion",
                "is_active": True
            }
        }
