# OCR Implementation for Scanned PDFs

## Problem Identified

The uploaded PDF `Candidate123.pdf` is a **scanned document** containing only images, not extractable text. This is why:
- Text extraction returned 0 characters
- The header "Team Management and Delivery Governance" could not be found
- Copy/paste doesn't work in the PDF

## Solution Implemented

A hybrid approach that automatically handles both regular PDFs and scanned PDFs:

### 1. **Hybrid Text Extraction** ([ocr_utils.py](service/ocr_utils.py))
- First attempts native text extraction (fast, free)
- If text extraction fails (< 50 characters), detects it as a scanned PDF
- Automatically falls back to LLM-based OCR using GPT-4 Vision
- Caches OCR results to avoid repeated API calls

### 2. **OCR Caching** ([models.py](service/models.py) - `PDFOCRCache`)
- Stores OCR-extracted text in database
- Uses SHA256 hash of file path + page number as cache key
- Prevents expensive re-processing of the same pages
- Tracks which model was used for OCR

### 3. **Integrated with Existing Flow** ([main.py](service/main.py))
- Updated `_extract_criterion_paragraph()` to use hybrid approach
- Transparent to the API - works automatically
- Only uses OCR when OpenAI provider is configured

## New Files Created

1. **`service/ocr_utils.py`** - OCR utility functions:
   - `is_scanned_pdf()` - Detects if a PDF page is scanned
   - `pdf_page_to_image()` - Converts PDF page to image
   - `llm_ocr_page()` - Uses GPT-4 Vision for OCR
   - `extract_text_hybrid()` - Main hybrid extraction function
   - `get_page_hash()` - Generates cache key for pages

2. **`service/test_ocr.py`** - Test script for OCR functionality

3. **`service/test_pdf_extraction.py`** - Diagnostic script (already used)

## Database Changes

Added new table `PDFOCRCache`:
```python
class PDFOCRCache(SQLModel, table=True):
    id: Optional[int]
    page_hash: str  # Unique cache key
    pdf_path: str
    page_num: int
    extracted_text: str  # OCR result
    model_used: str  # e.g., "gpt-4o"
    created_at: datetime
```

## Dependencies Added

- **Pillow** - For image processing (added to `requirements.txt`)

## How It Works

### Flow Diagram
```
User uploads PDF
    ↓
Extract answer endpoint called
    ↓
_extract_criterion_paragraph() called
    ↓
For each page:
    ├─→ Try native text extraction
    │   ├─→ Success (>50 chars)? → Use extracted text
    │   └─→ Failure (<50 chars)? → Scanned PDF detected
    │       ├─→ Check OCR cache
    │       │   ├─→ Found in cache? → Use cached text
    │       │   └─→ Not in cache? → Perform OCR
    │       │       ├─→ Convert page to image
    │       │       ├─→ Send to GPT-4 Vision
    │       │       ├─→ Extract text
    │       │       └─→ Cache result
    │       └─→ Use OCR text
    └─→ Search for headers in text
```

### Cost Optimization
- OCR only runs when needed (scanned PDFs)
- Results are cached permanently
- Each page is only OCR'd once per document
- Cache survives application restarts

## Configuration Requirements

### For OCR to Work:
**Important**: OCR is **independent** of your evaluation provider choice!

- **For Evaluations**: You can use EEA (local LLM) OR OpenAI
- **For OCR**: Always uses OpenAI (when available)

This means:
1. You can use **EEA LLM** for evaluations (selected in settings)
2. AND still have **OCR** work for scanned PDFs (if OpenAI key configured)
3. OCR will work regardless of which provider is selected for evaluations

### Environment Variables:
```bash
# Required for OCR to work on scanned PDFs
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o  # or gpt-4-vision-preview
OPENAI_BASE_URL=https://api.openai.com/v1  # optional

# Your local LLM (for evaluations)
EEA_API_KEY=...
EEA_BASE_URL=...
EEA_MODEL=...
```

### How it Works:
- **Settings page**: Select "EEA" or "OpenAI" for evaluations
- **OCR**: Automatically uses OpenAI if `OPENAI_API_KEY` is set
- **If no OpenAI key**: Scanned PDFs will fail with helpful error message

## Testing

### 1. Test OCR Functionality
```bash
cd service
python test_ocr.py
```

This will:
- Detect if the PDF is scanned
- Extract text from page 1 using LLM OCR
- Search for "Team Management and Delivery Governance"
- Show extracted text and search results

### 2. Test Full Integration
```bash
# Start the application
docker compose up

# Use the UI to:
# 1. Configure OpenAI provider in settings
# 2. Upload the scanned PDF
# 3. Extract answer for question ID "2"
# 4. Verify the header is found
```

### 3. Verify Caching
After first OCR:
```bash
# Check the database
sqlite3 service/data/tender_evaluation.db "SELECT * FROM pdfoorcrcache;"
```

Second extraction should use cached text (faster, no API call).

## API Cost Estimation

### GPT-4 Vision Pricing (as of 2024):
- **gpt-4o**: ~$5.00 per 1M input tokens
- Image processing: Variable based on resolution

### Per Page Estimate:
- 1 page at 200 DPI ≈ $0.01 - $0.03
- Cached pages: $0.00 (no additional cost)

### For a 10-page scanned document:
- First extraction: ~$0.10 - $0.30
- Subsequent extractions: $0.00 (cached)

## Limitations & Considerations

1. **Requires OpenAI Access**: OCR only works when OpenAI provider is configured
2. **API Costs**: OCR incurs API costs (but caching minimizes this)
3. **Processing Time**: OCR takes 2-5 seconds per page (first time only)
4. **Quality**: LLM OCR is very good but not perfect - may have minor formatting differences
5. **Image Size**: Large images may exceed API limits (200 DPI is a good balance)

## Alternative Approaches

If you want to avoid API costs, you could:
1. **Use Tesseract OCR** (free, local, but requires installation)
2. **Pre-process PDFs** (convert scanned PDFs to text PDFs before upload)
3. **Require text PDFs only** (reject scanned documents)

The current LLM-based approach was chosen for:
- Best accuracy and context understanding
- No additional software dependencies
- Handles complex layouts well
- Already integrated with OpenAI

## Future Enhancements

Possible improvements:
1. **Batch OCR**: Process all pages at once during upload
2. **Progress indicator**: Show OCR progress in UI
3. **Quality detection**: Warn users about low-quality scans
4. **OCR on demand**: Add a button to trigger OCR manually
5. **Alternative models**: Support other vision models (Claude, Gemini)
