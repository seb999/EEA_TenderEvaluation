# Changes Summary - OCR Implementation + Database Updates

## 1. Added `applicant_id` to PDFOCRCache

### Updated Files:
- **[models.py](service/models.py:143)**: Added `applicant_id` field to `PDFOCRCache` table
- **[main.py](service/main.py:9)**: Added `Optional` import and updated `_extract_criterion_paragraph`
- **[main.py](service/main.py:214)**: Pass `applicant_id` when creating cache entries

### Benefits:
- ✓ Better tracking of which candidate's PDF was OCR'd
- ✓ Easier cleanup when deleting candidates
- ✓ Audit trail for OCR usage
- ✓ Consistent with rest of database design

### Database Migration Needed:
Since we added a new field to `PDFOCRCache`, you need to either:
- **Option A**: Delete existing database and let it recreate (loses data)
  ```bash
  rm service/data/tender_evaluation.db
  ```
- **Option B**: Keep existing cache and new entries will have applicant_id

## 2. Existing Scripts

### Question Management: [seed_questions.py](service/data/seed_questions.py)
This script can import/export questions to/from the database.

**Usage:**
```bash
# Import questions from seed file
cd service/data
python seed_questions.py --import questions_seed.json

# Export questions to file
python seed_questions.py --export questions_export.json
```

### Current Questions in Seed File:
- Question 2: Team Management and Delivery Governance
- Question 3: External Integration and Dataflows

## 3. Next Steps

### To Add Question 4:
1. Add question to [questions_seed.json](service/data/questions_seed.json)
2. Run import script to load it into database

**Question 4 Template:**
```json
{
  "q_id": "4",
  "prompt_json": {
    "question": "Your question text here...",
    "scale": "0-5",
    "required_evidence": [
      "evidence item 1",
      "evidence item 2"
    ],
    "evaluation_guidance": [
      "guidance 1",
      "guidance 2"
    ],
    "output_format": {
      "score": "integer 0-5",
      "justification": "brief explanation",
      "missing_evidence": "list of missing elements"
    }
  },
  "is_active": true,
  "search_label": "Header text from PDF",
  "auto_increment": false
}
```

## What I Need from You:

**For Question 4, please provide:**
1. **Question text**: What question should be asked?
2. **Search label**: What is the header in the PDF? (e.g., "Security and Compliance")
3. **Required evidence**: What elements should the answer contain?
4. **Evaluation guidance**: How should answers be scored?
5. **Scale**: 0-5 or different?
6. **Auto-increment**: Should it look for numbered sections?
