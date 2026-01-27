from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import base64
from datetime import datetime
from pathlib import Path
import shutil
from typing import Optional
from sqlmodel import Session, select
from data.createBlankDatabase import create_db_and_tables, get_session
from models import Applicant, Question, ApplicantAnswer, AssessmentResult, SearchKeyword, LLMConfig, PDFOCRCache
import json
import openai
import re
import fitz
from ocr_utils import extract_text_hybrid, get_page_hash

# Load environment variables from .env file
load_dotenv()

# LLM clients
eea_client = openai.OpenAI(
    api_key=os.getenv("EEA_API_KEY"),
    base_url=os.getenv("EEA_BASE_URL")
)

# Optional OpenAI client (created lazily)
openai_client = None

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

def _get_llm_provider(session: Session) -> str:
    config = session.exec(select(LLMConfig)).first()
    provider = (config.provider if config else "eea").strip().lower()
    if provider not in {"eea", "openai"}:
        return "eea"
    return provider

def _get_model_for_provider(provider: str) -> tuple[str | None, str]:
    if provider == "openai":
        return os.getenv("OPENAI_MODEL"), "OpenAI"
    return os.getenv("EEA_MODEL"), "EEA In-house LLM"

def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return openai.OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    )

def _extract_criterion_paragraph(pdf_path: Path, question, session: Session, applicant_id: Optional[int] = None) -> tuple[str, str] | None:
    if not pdf_path.exists():
        return None

    # Build search pattern from question configuration
    search_label = question.search_label
    auto_increment = question.auto_increment

    # Extract number from q_id if auto_increment is enabled (e.g., "Q2" -> 2)
    question_number = None
    if auto_increment:
        match = re.search(r'\d+', question.q_id)
        if match:
            question_number = int(match.group())

    # Build regex patterns
    header_patterns = []
    next_header_patterns = []

    if auto_increment and question_number is not None:
        # Pattern for current number - supports both "Label Number" and "Number Label" formats
        # Examples: "Criterion 2", "Award Criterion 2", "2. Team Management", "2 Criterion"
        header_patterns.append(
            # Label followed by Number: "Criterion 2"
            re.compile(rf"\b(?:Award\s+)?{re.escape(search_label)}\s*{question_number}\b", re.IGNORECASE)
        )
        header_patterns.append(
            # Number followed by Label: "2. Team Management" or "2 Team Management"
            re.compile(rf"\b{question_number}\.?\s*{re.escape(search_label)}", re.IGNORECASE)
        )

        # Pattern for next number (to detect end of section)
        next_number = question_number + 1
        next_header_patterns.append(
            # Label followed by Number: "Criterion 3"
            re.compile(rf"\b(?:Award\s+)?{re.escape(search_label)}\s*{next_number}\b", re.IGNORECASE)
        )
        next_header_patterns.append(
            # Number followed by Label: "3. Next Section" or "3 Next Section"
            re.compile(rf"\b{next_number}\.?\s*{re.escape(search_label)}", re.IGNORECASE)
        )
    else:
        # Use exact search label without numbering
        header_patterns.append(
            re.compile(rf"{re.escape(search_label)}", re.IGNORECASE)
        )
        # For non-auto-increment, we need a way to detect the next section
        # Use a generic pattern that matches common section headers (both formats)
        next_header_patterns.append(
            # Label followed by Number: "Criterion 3", "Section 4"
            re.compile(r"^(Criterion|Section|Question|Award Criterion)\s*\d+", re.IGNORECASE)
        )
        next_header_patterns.append(
            # Number followed by Label: "3. ", "4. "
            re.compile(r"^\d+\.\s+\w", re.IGNORECASE)
        )

    extracted_lines = []
    header_line = None
    collecting = False

    # Get OpenAI client for potential OCR fallback
    # NOTE: OCR is independent of the evaluation provider setting
    # We use OpenAI for OCR (if available) even if EEA is selected for evaluations
    ocr_client = _get_openai_client()
    ocr_model = os.getenv("OPENAI_MODEL") or "gpt-4o"

    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc):
            # First try standard text extraction
            text = page.get_text("text")

            # If no text found (scanned PDF), use hybrid OCR approach
            if not text or len(text.strip()) < 50:
                # Check cache first
                page_hash = get_page_hash(pdf_path, page_num)
                cached = session.exec(select(PDFOCRCache).where(PDFOCRCache.page_hash == page_hash)).first()

                if cached:
                    print(f"Using cached OCR text for page {page_num}")
                    text = cached.extracted_text
                elif ocr_client:
                    print(f"Scanned PDF detected on page {page_num}, using LLM OCR...")
                    ocr_text, used_ocr = extract_text_hybrid(pdf_path, page_num, ocr_client, ocr_model)
                    if used_ocr and ocr_text:
                        text = ocr_text
                        # Cache the OCR result
                        cache_entry = PDFOCRCache(
                            page_hash=page_hash,
                            pdf_path=str(pdf_path),
                            page_num=page_num,
                            extracted_text=ocr_text,
                            model_used=ocr_model,
                            applicant_id=applicant_id
                        )
                        session.add(cache_entry)
                        session.commit()
                        print(f"OCR text cached for future use")
                else:
                    print(f"Warning: Scanned PDF detected but OCR not available (OpenAI provider not configured)")

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
                    # Check if any next header pattern matches
                    if any(pattern.search(trimmed) for pattern in next_header_patterns) and not re.search(r"\.{4,}", trimmed):
                        collecting = False
                        break
                    extracted_lines.append(line)
                    continue

                # Check if any header pattern matches
                if any(pattern.search(trimmed) for pattern in header_patterns):
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
                        if any(pattern.search(next_trimmed) for pattern in next_header_patterns) and not re.search(r"\.{4,}", next_trimmed):
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
async def get_model(session: Session = Depends(get_session)):
    """Get the configured LLM model"""
    provider = _get_llm_provider(session)
    model_name, provider_label = _get_model_for_provider(provider)

    if not model_name:
        return {"error": f"{provider_label} model not configured"}, 404

    # Check if OCR is available (independent of evaluation provider)
    ocr_available = _get_openai_client() is not None

    return {
        "model": model_name,
        "provider": provider_label,
        "supports_images": provider == "openai",
        "ocr_available": ocr_available
    }

@app.get("/llm-config")
async def get_llm_config(session: Session = Depends(get_session)):
    """Get current LLM provider configuration"""
    provider = _get_llm_provider(session)
    model_name, provider_label = _get_model_for_provider(provider)

    # Check if OCR is available (OpenAI credentials configured)
    ocr_available = _get_openai_client() is not None

    return {
        "provider": provider,
        "provider_label": provider_label,
        "model": model_name,
        "supports_images": provider == "openai",
        "ocr_available": ocr_available,
        "ocr_note": "OCR for scanned PDFs requires OpenAI API key" if not ocr_available else "OCR enabled for scanned PDFs"
    }

@app.put("/llm-config")
async def update_llm_config(
    provider: str = Form(...),
    session: Session = Depends(get_session)
):
    """Update LLM provider configuration"""
    normalized = provider.strip().lower()
    if normalized not in {"eea", "openai"}:
        raise HTTPException(status_code=400, detail="Invalid provider")

    existing = session.exec(select(LLMConfig)).first()
    if existing:
        existing.provider = normalized
        session.add(existing)
    else:
        session.add(LLMConfig(provider=normalized))

    session.commit()
    return {"provider": normalized}

@app.post("/evaluate")
async def evaluate_answer(
    applicant_id: int = Form(...),
    q_id: str = Form(...),
    answer_text: str = Form(...),
    image: UploadFile | None = File(None),
    session: Session = Depends(get_session)
):
    """Evaluate a candidate answer using the question prompt stored in the database."""
    provider = _get_llm_provider(session)
    model_name, provider_label = _get_model_for_provider(provider)
    if not model_name:
        raise HTTPException(status_code=500, detail=f"{provider_label} model not configured")

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
        if provider == "openai":
            client = _get_openai_client()
            if not client:
                raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

            message_content = [{"type": "text", "text": prompt}]
            if image:
                allowed_types = {"image/png", "image/jpeg", "image/webp"}
                if image.content_type not in allowed_types:
                    raise HTTPException(status_code=400, detail="Only PNG, JPEG, or WEBP images are supported")
                image_bytes = await image.read()
                if not image_bytes:
                    raise HTTPException(status_code=400, detail="Empty image upload")
                encoded = base64.b64encode(image_bytes).decode("ascii")
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.content_type};base64,{encoded}"}
                })

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": message_content}],
                temperature=0
            )
        else:
            if image:
                raise HTTPException(status_code=400, detail="Image input is only supported with OpenAI")
            response = eea_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {str(e)}")

    content = response.choices[0].message.content
    parsed = _extract_json_payload(content)

    # Extract score and justification from parsed result
    score = None
    justification = None
    if isinstance(parsed, dict):
        score_value = parsed.get("score")
        if isinstance(score_value, (int, float)):
            score = float(score_value)
        elif isinstance(score_value, str):
            try:
                score = float(score_value)
            except ValueError:
                pass

        justification_value = parsed.get("justification")
        if isinstance(justification_value, str):
            justification = justification_value

    # Save or update assessment result in AssessmentResult table
    statement = select(AssessmentResult).where(
        AssessmentResult.applicant_id == applicant_id,
        AssessmentResult.q_id == q_id
    )
    existing_assessment = session.exec(statement).first()

    if existing_assessment:
        # Update existing assessment
        existing_assessment.question_text = question_text
        existing_assessment.answer_text = answer_text
        existing_assessment.score = score
        existing_assessment.justification = justification
        existing_assessment.llm_response = content
        existing_assessment.parsed_result = json.dumps(parsed, ensure_ascii=True) if parsed else None
        existing_assessment.created_at = datetime.utcnow()
        session.add(existing_assessment)
    else:
        # Create new assessment result
        new_assessment = AssessmentResult(
            applicant_id=applicant_id,
            q_id=q_id,
            question_text=question_text,
            answer_text=answer_text,
            score=score,
            justification=justification,
            llm_response=content,
            parsed_result=json.dumps(parsed, ensure_ascii=True) if parsed else None
        )
        session.add(new_assessment)

    # Keep existing logic for backward compatibility with Applicant.evaluation_result
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

    # Calculate average score from all assessments
    all_assessments = session.exec(
        select(AssessmentResult).where(AssessmentResult.applicant_id == applicant_id)
    ).all()

    scores = []
    for assessment in all_assessments:
        if assessment.score is not None:
            scores.append(assessment.score)
        # If this is the current assessment being created and hasn't been committed yet
        elif assessment.q_id == q_id and score is not None:
            scores.append(score)

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
    q_id: str = Form(...),
    session: Session = Depends(get_session)
):
    """Extract the paragraph for a specific question from the applicant PDF."""
    applicant = session.get(Applicant, applicant_id)
    if not applicant:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")

    # Get question to retrieve search configuration
    statement = select(Question).where(Question.q_id == q_id)
    question = session.exec(statement).first()
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {q_id} not found")

    file_path = Path(applicant.file_path)
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent / file_path

    extracted = _extract_criterion_paragraph(file_path, question, session, applicant_id)
    if not extracted:
        search_pattern = question.search_label
        if question.auto_increment:
            # Extract number from q_id (e.g., "Q2" -> "2")
            match = re.search(r'\d+', q_id)
            if match:
                search_pattern += f" {match.group()}"

        raise HTTPException(
            status_code=404,
            detail=f"Section '{search_pattern}' not found in PDF"
        )

    header, paragraph = extracted

    return {
        "applicant_id": applicant_id,
        "q_id": q_id,
        "header": header,
        "paragraph": paragraph
    }

@app.get("/applicant-answer/{applicant_id}/{q_id}")
async def get_applicant_answer(
    applicant_id: int,
    q_id: str,
    session: Session = Depends(get_session)
):
    """Get the stored answer for an applicant and question"""
    statement = select(ApplicantAnswer).where(
        ApplicantAnswer.applicant_id == applicant_id,
        ApplicantAnswer.q_id == q_id
    )
    answer = session.exec(statement).first()

    if not answer:
        return {"answer": None}

    return {
        "answer": {
            "id": answer.id,
            "applicant_id": answer.applicant_id,
            "q_id": answer.q_id,
            "answer_text": answer.answer_text,
            "source": answer.source,
            "created_at": answer.created_at.isoformat(),
            "updated_at": answer.updated_at.isoformat()
        }
    }

@app.post("/applicant-answer")
async def save_applicant_answer(
    applicant_id: int = Form(...),
    q_id: str = Form(...),
    answer_text: str = Form(...),
    source: str = Form("manual"),
    session: Session = Depends(get_session)
):
    """Save or update an applicant's answer to a question"""
    # Check if answer already exists
    statement = select(ApplicantAnswer).where(
        ApplicantAnswer.applicant_id == applicant_id,
        ApplicantAnswer.q_id == q_id
    )
    existing_answer = session.exec(statement).first()

    if existing_answer:
        # Update existing answer
        existing_answer.answer_text = answer_text
        existing_answer.source = source
        existing_answer.updated_at = datetime.utcnow()
        session.add(existing_answer)
        session.commit()
        session.refresh(existing_answer)

        return {
            "message": "Answer updated successfully",
            "answer": {
                "id": existing_answer.id,
                "applicant_id": existing_answer.applicant_id,
                "q_id": existing_answer.q_id,
                "answer_text": existing_answer.answer_text,
                "source": existing_answer.source,
                "created_at": existing_answer.created_at.isoformat(),
                "updated_at": existing_answer.updated_at.isoformat()
            }
        }
    else:
        # Create new answer
        new_answer = ApplicantAnswer(
            applicant_id=applicant_id,
            q_id=q_id,
            answer_text=answer_text,
            source=source
        )
        session.add(new_answer)
        session.commit()
        session.refresh(new_answer)

        return {
            "message": "Answer saved successfully",
            "answer": {
                "id": new_answer.id,
                "applicant_id": new_answer.applicant_id,
                "q_id": new_answer.q_id,
                "answer_text": new_answer.answer_text,
                "source": new_answer.source,
                "created_at": new_answer.created_at.isoformat(),
                "updated_at": new_answer.updated_at.isoformat()
            }
        }

@app.get("/assessment-results/{applicant_id}")
async def get_assessment_results(
    applicant_id: int,
    session: Session = Depends(get_session)
):
    """Get all assessment results for an applicant"""
    statement = select(AssessmentResult).where(
        AssessmentResult.applicant_id == applicant_id
    ).order_by(AssessmentResult.q_id)

    results = session.exec(statement).all()

    assessment_list = []
    for result in results:
        parsed_obj = None
        if result.parsed_result:
            try:
                parsed_obj = json.loads(result.parsed_result)
            except json.JSONDecodeError:
                parsed_obj = None

        assessment_list.append({
            "id": result.id,
            "applicant_id": result.applicant_id,
            "q_id": result.q_id,
            "question_text": result.question_text,
            "answer_text": result.answer_text,
            "score": result.score,
            "justification": result.justification,
            "llm_response": result.llm_response,
            "parsed_result": parsed_obj,
            "created_at": result.created_at.isoformat()
        })

    return {"results": assessment_list}

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
                "is_active": q.is_active,
                "search_label": q.search_label,
                "auto_increment": q.auto_increment
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
            "is_active": question.is_active,
            "search_label": question.search_label,
            "auto_increment": question.auto_increment
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
    search_label: str = Form("Criterion"),
    auto_increment: bool = Form(True),
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
            is_active=is_active,
            search_label=search_label,
            auto_increment=auto_increment
        )
        session.add(question)
        session.commit()
        session.refresh(question)

        return {
            "message": "Question created successfully",
            "id": question.id,
            "q_id": question.q_id,
            "prompt_json": json.loads(question.prompt_json),
            "is_active": question.is_active,
            "search_label": question.search_label,
            "auto_increment": question.auto_increment
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
    search_label: str = Form("Criterion"),
    auto_increment: bool = Form(True),
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
        question.search_label = search_label
        question.auto_increment = auto_increment
        session.add(question)
        session.commit()
        session.refresh(question)

        return {
            "message": "Question updated successfully",
            "id": question.id,
            "q_id": question.q_id,
            "prompt_json": json.loads(question.prompt_json),
            "is_active": question.is_active,
            "search_label": question.search_label,
            "auto_increment": question.auto_increment
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

@app.get("/search-keywords")
async def list_search_keywords(session: Session = Depends(get_session)):
    """List all search keywords for PDF extraction"""
    try:
        statement = select(SearchKeyword).order_by(SearchKeyword.keyword)
        keywords = session.exec(statement).all()

        result = []
        for keyword in keywords:
            result.append({
                "id": keyword.id,
                "keyword": keyword.keyword,
                "is_active": keyword.is_active,
                "created_at": keyword.created_at.isoformat()
            })

        return {"keywords": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list search keywords: {str(e)}")

@app.post("/search-keywords")
async def create_search_keyword(
    keyword: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Create a new search keyword"""
    try:
        # Check if keyword already exists
        statement = select(SearchKeyword).where(SearchKeyword.keyword == keyword)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Keyword '{keyword}' already exists")

        # Create new keyword
        new_keyword = SearchKeyword(
            keyword=keyword,
            is_active=is_active
        )
        session.add(new_keyword)
        session.commit()
        session.refresh(new_keyword)

        return {
            "message": "Search keyword created successfully",
            "id": new_keyword.id,
            "keyword": new_keyword.keyword,
            "is_active": new_keyword.is_active,
            "created_at": new_keyword.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create search keyword: {str(e)}")

@app.put("/search-keywords/{keyword_id}")
async def update_search_keyword(
    keyword_id: int,
    keyword: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_session)
):
    """Update an existing search keyword"""
    try:
        # Find existing keyword
        existing_keyword = session.get(SearchKeyword, keyword_id)
        if not existing_keyword:
            raise HTTPException(status_code=404, detail=f"Search keyword with id {keyword_id} not found")

        # Update keyword
        existing_keyword.keyword = keyword
        existing_keyword.is_active = is_active
        session.add(existing_keyword)
        session.commit()
        session.refresh(existing_keyword)

        return {
            "message": "Search keyword updated successfully",
            "id": existing_keyword.id,
            "keyword": existing_keyword.keyword,
            "is_active": existing_keyword.is_active,
            "created_at": existing_keyword.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update search keyword: {str(e)}")

@app.delete("/search-keywords/{keyword_id}")
async def delete_search_keyword(keyword_id: int, session: Session = Depends(get_session)):
    """Delete a search keyword"""
    try:
        # Find existing keyword
        keyword = session.get(SearchKeyword, keyword_id)
        if not keyword:
            raise HTTPException(status_code=404, detail=f"Search keyword with id {keyword_id} not found")

        # Delete keyword
        session.delete(keyword)
        session.commit()

        return {
            "message": f"Search keyword '{keyword.keyword}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete search keyword: {str(e)}")
