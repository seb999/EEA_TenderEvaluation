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

## API Documentation

- **Swagger UI:** `http://localhost:8000/swagger`
- **ReDoc:** `http://localhost:8000/redoc`

## Deactivating Virtual Environment

When you're done working, deactivate the virtual environment:

```bash
deactivate
```
