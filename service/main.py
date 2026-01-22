from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from datetime import datetime
from pathlib import Path
import shutil
from sqlmodel import Session, select
from data.createBlankDatabase import create_db_and_tables, get_session
from models import Applicant, Question
import json
import openai
import re
import fitz

# Load environment variables from .env file
load_dotenv()

# LLM client (shared)
llm_client = openai.OpenAI(
    api_key=os.getenv("EEA_API_KEY"),
    base_url=os.getenv("EEA_BASE_URL")
)

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

@app.on_event("startup")
def on_startup():
    """Initialize database on application startup"""
    create_db_and_tables()

def _extract_json_payload(content: str):
    content = content.strip()
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = content[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None

def _build_prompt(prompt_data: dict, answer_text: str) -> str:
    template = prompt_data.get("prompt_template")
    question_text = prompt_data.get("question_text") or prompt_data.get("question") or ""

    if isinstance(template, str) and template.strip():
        values = dict(prompt_data)
        values.update({
            "answer": answer_text,
            "answer_text": answer_text,
            "question_text": question_text
        })

        class _SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        return template.format_map(_SafeDict(values))

    prompt_json = json.dumps(prompt_data, ensure_ascii=True)
    return (
        "You are evaluating a tender proposal answer using the following prompt JSON.\n"
        "Return only the evaluation result in JSON.\n\n"
        f"Prompt JSON:\n{prompt_json}\n\n"
        f"Candidate answer:\n{answer_text}\n"
    )

def _extract_criterion_paragraph(pdf_path: Path, criterion_number: int) -> tuple[str, str] | None:
    if not pdf_path.exists():
        return None

    header_pattern = re.compile(
        rf"\b(?:Award\s+)?Criterion\s*{criterion_number}\b",
        re.IGNORECASE
    )
    next_header_number = criterion_number + 1
    next_header_pattern = re.compile(
        rf"\b(?:Award\s+)?Criterion\s*{next_header_number}\b",
        re.IGNORECASE
    )

    extracted_lines = []
    header_line = None
    collecting = False

    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            text = page.get_text("text")
            if not text:
                continue

            text = text.replace("\u00a0", " ")
            lines = text.splitlines()

            for idx, line in enumerate(lines):
                trimmed = line.strip()
                if not trimmed:
                    if collecting:
                        extracted_lines.append(line)
                    continue

                if collecting:
                    if next_header_pattern.search(trimmed) and not re.search(r"\.{4,}", trimmed):
                        collecting = False
                        break
                    extracted_lines.append(line)
                    continue

                if header_pattern.search(trimmed):
                    if re.search(r"\.{4,}", trimmed):
                        continue
                    header_line = line
                    collecting = True
                    for j in range(idx + 1, len(lines)):
                        next_line = lines[j]
                        next_trimmed = next_line.strip()
                        if not next_trimmed:
                            extracted_lines.append(next_line)
                            continue
                        if next_header_pattern.search(next_trimmed) and not re.search(r"\.{4,}", next_trimmed):
                            collecting = False
                            break
                        extracted_lines.append(next_line)
                    break

    if not extracted_lines or not header_line:
        return None

    combined = "\n".join(extracted_lines).strip()
    if not combined:
        return None

    header_text = header_line.strip()
    combined_with_header = f"{header_text}\n{combined}".strip()
    return header_text, combined_with_header

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

@app.post("/evaluate")
async def evaluate_answer(
    applicant_id: int = Form(...),
    q_id: str = Form(...),
    answer_text: str = Form(...),
    session: Session = Depends(get_session)
):
    """Evaluate a candidate answer using the question prompt stored in the database."""
    model_name = os.getenv("EEA_MODEL")
    if not model_name:
        raise HTTPException(status_code=500, detail="EEA_MODEL not configured")

    applicant = session.get(Applicant, applicant_id)
    if not applicant:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")

    statement = select(Question).where(Question.q_id == q_id)
    question = session.exec(statement).first()
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {q_id} not found")

    try:
        prompt_data = json.loads(question.prompt_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Question {q_id} has invalid prompt_json")

    prompt = _build_prompt(prompt_data, answer_text)
    question_text = (
        prompt_data.get("question_text")
        or prompt_data.get("question")
        or ""
    )

    try:
        response = llm_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {str(e)}")

    content = response.choices[0].message.content
    parsed = _extract_json_payload(content)

    existing_result = {}
    if applicant.evaluation_result:
        try:
            existing_result = json.loads(applicant.evaluation_result)
        except json.JSONDecodeError:
            existing_result = {}

    evaluations = existing_result.get("evaluations")
    if not isinstance(evaluations, dict):
        evaluations = {}

    evaluations[q_id] = {
        "question_text": question_text,
        "answer_text": answer_text,
        "parsed_result": parsed,
        "llm_response": content
    }

    existing_result["evaluations"] = evaluations
    existing_result["last_updated"] = datetime.utcnow().isoformat()

    scores = []
    for entry in evaluations.values():
        parsed_result = entry.get("parsed_result")
        if isinstance(parsed_result, dict):
            score_value = parsed_result.get("score")
            if isinstance(score_value, (int, float)):
                scores.append(float(score_value))
            elif isinstance(score_value, str):
                try:
                    scores.append(float(score_value))
                except ValueError:
                    pass

    applicant.evaluation_score = (sum(scores) / len(scores)) if scores else None
    applicant.evaluation_result = json.dumps(existing_result, ensure_ascii=True)
    applicant.status = "completed"
    applicant.processed_at = datetime.utcnow()
    session.add(applicant)
    session.commit()
    session.refresh(applicant)

    return {
        "applicant_id": applicant_id,
        "q_id": q_id,
        "prompt": prompt_data,
        "answer_text": answer_text,
        "llm_response": content,
        "parsed_result": parsed,
        "evaluation_result": existing_result,
        "evaluation_score": applicant.evaluation_score
    }

@app.post("/extract-answer")
async def extract_answer_paragraph(
    applicant_id: int = Form(...),
    criterion_number: int = Form(...),
    session: Session = Depends(get_session)
):
    """Extract the paragraph following a Criterion header from the applicant PDF."""
    applicant = session.get(Applicant, applicant_id)
    if not applicant:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")

    file_path = Path(applicant.file_path)
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent / file_path

    extracted = _extract_criterion_paragraph(file_path, criterion_number)
    if not extracted:
        raise HTTPException(
            status_code=404,
            detail=f"Criterion {criterion_number} not found in PDF"
        )

    header, paragraph = extracted

    return {
        "applicant_id": applicant_id,
        "criterion_number": criterion_number,
        "header": header,
        "paragraph": paragraph
    }

@app.get("/uploads")
async def list_uploads(session: Session = Depends(get_session)):
    """List all uploaded PDF files from database"""
    try:
        statement = select(Applicant).order_by(Applicant.uploaded_at.desc())
        applicants = session.exec(statement).all()

        uploads = []
        for applicant in applicants:
            evaluation_payload = None
            if applicant.evaluation_result:
                try:
                    evaluation_payload = json.loads(applicant.evaluation_result)
                except json.JSONDecodeError:
                    evaluation_payload = None

            uploads.append({
                "id": applicant.id,
                "filename": applicant.filename,
                "vendor_name": applicant.vendor_name,
                "file_size": applicant.file_size,
                "uploaded_at": applicant.uploaded_at.timestamp(),
                "status": applicant.status,
                "evaluation_score": applicant.evaluation_score,
                "evaluation_result": evaluation_payload
            })

        return {"uploads": uploads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list uploads: {str(e)}")

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    vendor_name: str = Form(...),
    session: Session = Depends(get_session)
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

    # Save to database
    try:
        applicant = Applicant(
            vendor_name=vendor_name,
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            status="uploaded"
        )
        session.add(applicant)
        session.commit()
        session.refresh(applicant)
    except Exception as e:
        # If database save fails, delete the uploaded file
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

    return {
        "message": "File uploaded successfully",
        "id": applicant.id,
        "vendor_name": applicant.vendor_name,
        "filename": applicant.filename,
        "file_path": applicant.file_path,
        "file_size": applicant.file_size
    }

@app.delete("/uploads/{applicant_id}")
async def delete_applicant(applicant_id: int, session: Session = Depends(get_session)):
    """Delete an applicant and their uploaded file"""
    try:
        # Find the applicant
        statement = select(Applicant).where(Applicant.id == applicant_id)
        applicant = session.exec(statement).first()

        if not applicant:
            raise HTTPException(status_code=404, detail=f"Applicant with id {applicant_id} not found")

        # Delete the PDF file if it exists
        file_path = Path(applicant.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete file {file_path}: {str(e)}")

        # Delete from database
        session.delete(applicant)
        session.commit()

        return {
            "message": f"Applicant {applicant.vendor_name} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete applicant: {str(e)}")

@app.get("/questions")
async def list_questions(session: Session = Depends(get_session)):
    """List all evaluation questions"""
    try:
        statement = select(Question).where(Question.is_active == True).order_by(Question.q_id)
        questions = session.exec(statement).all()

        result = []
        for q in questions:
            result.append({
                "id": q.id,
                "q_id": q.q_id,
                "prompt_json": json.loads(q.prompt_json),
                "is_active": q.is_active
            })

        return {"questions": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list questions: {str(e)}")

@app.get("/questions/{q_id}")
async def get_question(q_id: str, session: Session = Depends(get_session)):
    """Get a specific question by q_id"""
    try:
        statement = select(Question).where(Question.q_id == q_id)
        question = session.exec(statement).first()

        if not question:
            raise HTTPException(status_code=404, detail=f"Question {q_id} not found")

        return {
            "id": question.id,
            "q_id": question.q_id,
            "prompt_json": json.loads(question.prompt_json),
            "is_active": question.is_active
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get question: {str(e)}")

@app.post("/questions")
async def create_question(
    q_id: str = Form(...),
    prompt_json: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Create a new evaluation question"""
    try:
        # Validate JSON
        try:
            json.loads(prompt_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in prompt_json")

        # Check if question with this q_id already exists
        statement = select(Question).where(Question.q_id == q_id)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Question with q_id {q_id} already exists")

        # Create new question
        question = Question(
            q_id=q_id,
            prompt_json=prompt_json,
            is_active=is_active
        )
        session.add(question)
        session.commit()
        session.refresh(question)

        return {
            "message": "Question created successfully",
            "id": question.id,
            "q_id": question.q_id,
            "prompt_json": json.loads(question.prompt_json),
            "is_active": question.is_active
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create question: {str(e)}")

@app.put("/questions/{q_id}")
async def update_question(
    q_id: str,
    prompt_json: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Update an existing evaluation question"""
    try:
        # Validate JSON
        try:
            json.loads(prompt_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in prompt_json")

        # Find existing question
        statement = select(Question).where(Question.q_id == q_id)
        question = session.exec(statement).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {q_id} not found")

        # Update question
        question.prompt_json = prompt_json
        question.is_active = is_active
        session.add(question)
        session.commit()
        session.refresh(question)

        return {
            "message": "Question updated successfully",
            "id": question.id,
            "q_id": question.q_id,
            "prompt_json": json.loads(question.prompt_json),
            "is_active": question.is_active
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update question: {str(e)}")

@app.delete("/questions/{q_id}")
async def delete_question(q_id: str, session: Session = Depends(get_session)):
    """Delete an evaluation question"""
    try:
        # Find existing question
        statement = select(Question).where(Question.q_id == q_id)
        question = session.exec(statement).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {q_id} not found")

        # Delete question
        session.delete(question)
        session.commit()

        return {
            "message": f"Question {q_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {str(e)}")
