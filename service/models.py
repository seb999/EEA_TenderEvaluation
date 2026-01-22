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
                }
            }
        }
