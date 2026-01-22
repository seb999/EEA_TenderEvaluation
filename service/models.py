from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

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
