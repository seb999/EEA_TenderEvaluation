# Tender Evaluation API Service

Python FastAPI service for the Tender Evaluation application.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**Git Bash/Unix/macOS:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Make sure the `.env` file exists in the service folder with the following configuration:

```
EEA_API_KEY=your-api-key
EEA_MODEL=Inhouse-LLM/gpt-oss-120b
EEA_BASE_URL=https://llmgw.eea.europa.eu/v1
```

## Running the Service

### Start the API Server

**Option 1: After activating the virtual environment**
```bash
uvicorn main:app --reload
```

**Option 2: Without activating (from service folder)**
```bash
venv\Scripts\python -m uvicorn main:app --reload
```

**Option 3: From project root**
```bash
cd service && venv\Scripts\python -m uvicorn main:app --reload
```

The API will be available at: `http://localhost:8000`

### Run on a Different Port

```bash
venv\Scripts\python -m uvicorn main:app --reload --port 8080
```

### Run in Production Mode (without auto-reload)

```bash
venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Database

The service uses SQLite database to store applicant information.

### Database Location

The database file is automatically created at: `data/tender_evaluation.db`

### Migrating Existing Files

If you have existing PDF files in the uploads directory, run the migration script to import them into the database:

```bash
venv\Scripts\python migrate_existing_files.py
```

## API Endpoints

### GET `/`
Root endpoint to verify the API is running.

**Response:**
```json
{
  "message": "Tender Evaluation API is running"
}
```

### GET `/model`
Get the configured EEA LLM model.

**Response:**
```json
{
  "model": "Inhouse-LLM/gpt-oss-120b",
  "provider": "EEA In-house LLM"
}
```

### GET `/uploads`
List all uploaded applicants from the database.

**Response:**
```json
{
  "uploads": [
    {
      "id": 1,
      "filename": "Vendor A.pdf",
      "vendor_name": "Vendor A",
      "file_size": 1024000,
      "uploaded_at": 1769083833.60234,
      "status": "uploaded",
      "evaluation_score": null
    }
  ]
}
```

### POST `/upload`
Upload a PDF file with vendor name. Saves both the file and database record.

**Parameters:**
- `file`: PDF file (multipart/form-data)
- `vendor_name`: Name of the vendor/applicant (form field)

**Response:**
```json
{
  "message": "File uploaded successfully",
  "id": 1,
  "vendor_name": "Vendor A",
  "filename": "Vendor A.pdf",
  "file_path": "uploads\\Vendor A.pdf",
  "file_size": 1024000
}
```

## API Documentation

- **Swagger UI:** `http://localhost:8000/swagger`
- **ReDoc:** `http://localhost:8000/redoc`

## Deactivating Virtual Environment

When you're done working, deactivate the virtual environment:

```bash
deactivate
```
