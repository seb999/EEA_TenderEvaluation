from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from pathlib import Path
import shutil

# Load environment variables from .env file
load_dotenv()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Tender Evaluation API",
    docs_url="/swagger",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Tender Evaluation API is running"}

@app.get("/model")
async def get_model():
    """Get the configured EEA LLM model"""
    eea_model = os.getenv("EEA_MODEL")

    if not eea_model:
        return {"error": "EEA_MODEL not configured"}, 404

    return {
        "model": eea_model,
        "provider": "EEA In-house LLM"
    }

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    vendor_name: str = Form(...)
):
    """Upload a PDF file and save it with the vendor name"""

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Sanitize vendor name for file system
    safe_vendor_name = "".join(c for c in vendor_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_vendor_name:
        raise HTTPException(status_code=400, detail="Invalid vendor name")

    # Create filename with vendor name
    file_extension = ".pdf"
    filename = f"{safe_vendor_name}{file_extension}"
    file_path = UPLOAD_DIR / filename

    # If file exists, add a number suffix
    counter = 1
    while file_path.exists():
        filename = f"{safe_vendor_name}_{counter}{file_extension}"
        file_path = UPLOAD_DIR / filename
        counter += 1

    # Save the file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return {
        "message": "File uploaded successfully",
        "vendor_name": vendor_name,
        "filename": filename,
        "file_path": str(file_path),
        "file_size": file_path.stat().st_size
    }
