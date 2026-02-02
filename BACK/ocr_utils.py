"""
OCR utilities for handling scanned PDFs using LLM-based text extraction.
Provides hybrid approach: try native text extraction first, fall back to LLM OCR if needed.
"""
import fitz
import base64
import io
from pathlib import Path
from PIL import Image
import openai
import os
from typing import Optional, Tuple
import hashlib


def is_scanned_pdf(pdf_path: Path, page_num: int = 0) -> bool:
    """
    Detect if a PDF page is scanned (image-based) or contains real text.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to check (0-indexed)

    Returns:
        True if the page is scanned (no extractable text), False otherwise
    """
    try:
        with fitz.open(str(pdf_path)) as doc:
            if page_num >= len(doc):
                return False

            page = doc[page_num]
            text = page.get_text("text").strip()

            # If there's substantial text, it's not a scanned document
            if len(text) > 50:  # More than 50 chars suggests real text
                return False

            # Check if there are image blocks
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            image_blocks = [b for b in blocks if b.get("type") == 1]

            # Scanned if no text and has images
            return len(text) < 50 and len(image_blocks) > 0
    except Exception:
        return False


def pdf_page_to_image(pdf_path: Path, page_num: int = 0, dpi: int = 200) -> Optional[Image.Image]:
    """
    Convert a PDF page to a PIL Image.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to convert (0-indexed)
        dpi: Resolution for rendering (default 200 DPI for good OCR quality)

    Returns:
        PIL Image object or None if conversion fails
    """
    try:
        with fitz.open(str(pdf_path)) as doc:
            if page_num >= len(doc):
                return None

            page = doc[page_num]

            # Render page to pixmap at specified DPI
            # zoom factor: dpi/72 (72 is the default DPI)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert pixmap to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            return img
    except Exception as e:
        print(f"Error converting PDF page to image: {e}")
        return None


def get_page_hash(pdf_path: Path, page_num: int) -> str:
    """
    Generate a hash for a PDF page to use as cache key.
    Uses the actual page content to ensure different PDFs with same filename
    get different cache entries.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number

    Returns:
        SHA256 hash of the PDF page content
    """
    try:
        with fitz.open(str(pdf_path)) as doc:
            if page_num >= len(doc):
                # Fallback for invalid page number
                return hashlib.sha256(f"{pdf_path.absolute()}:{page_num}:invalid".encode()).hexdigest()

            page = doc[page_num]

            # Get the raw page content (text + image data)
            # This creates a unique fingerprint based on actual content
            page_text = page.get_text("text")

            # Get image blocks to include in hash
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            image_hashes = []

            for block in blocks:
                if block.get("type") == 1:  # Image block
                    # Include image dimensions and position as part of hash
                    img_info = f"{block.get('bbox')}:{block.get('width')}:{block.get('height')}"
                    image_hashes.append(img_info)

            # Combine text content and image structure for unique hash
            content_string = f"{page_text}:{'|'.join(image_hashes)}:{page_num}"
            return hashlib.sha256(content_string.encode()).hexdigest()

    except Exception as e:
        print(f"Error generating page hash: {e}")
        # Fallback to path-based hash with error marker
        return hashlib.sha256(f"{pdf_path.absolute()}:{page_num}:error".encode()).hexdigest()


def llm_ocr_page(
    image: Image.Image,
    client: openai.OpenAI,
    model: str = "gpt-4o"
) -> Optional[str]:
    """
    Use LLM vision capabilities to extract text from an image.

    Args:
        image: PIL Image to extract text from
        client: OpenAI client instance
        model: Model to use (must support vision)

    Returns:
        Extracted text or None if extraction fails
    """
    try:
        # Convert image to base64
        buffer = io.BytesIO()

        # Convert to RGB if necessary (remove alpha channel)
        if image.mode == "RGBA":
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Save as JPEG (more efficient than PNG for photos/scans)
        image.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()
        encoded = base64.b64encode(img_bytes).decode("ascii")

        # Prompt for text extraction
        prompt = """Extract ALL text from this document image.
Preserve the exact formatting, structure, headers, and layout as much as possible.
Return ONLY the extracted text, with no additional commentary or explanation.
Preserve line breaks and spacing."""

        # Call LLM with vision
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}
                    }
                ]
            }],
            temperature=0,
            max_completion_tokens=4096
        )

        extracted_text = response.choices[0].message.content
        return extracted_text.strip() if extracted_text else None

    except Exception as e:
        print(f"Error during LLM OCR: {e}")
        return None


def extract_text_hybrid(
    pdf_path: Path,
    page_num: int = 0,
    openai_client: Optional[openai.OpenAI] = None,
    model: str = "gpt-4o"
) -> Tuple[str, bool]:
    """
    Hybrid text extraction: try native extraction first, fall back to LLM OCR if needed.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to extract (0-indexed)
        openai_client: OpenAI client for OCR fallback (required for scanned PDFs)
        model: Model to use for OCR

    Returns:
        Tuple of (extracted_text, used_ocr)
        - extracted_text: The extracted text (empty string if failed)
        - used_ocr: True if OCR was used, False if native extraction worked
    """
    try:
        # Step 1: Try native text extraction
        with fitz.open(str(pdf_path)) as doc:
            if page_num >= len(doc):
                return "", False

            page = doc[page_num]
            text = page.get_text("text")

            # If we got substantial text, return it
            if len(text.strip()) > 50:
                return text, False

        # Step 2: Detected scanned PDF - need OCR
        if not openai_client:
            print("Warning: Scanned PDF detected but no OpenAI client provided for OCR")
            return "", False

        print(f"Scanned PDF detected on page {page_num}. Using LLM OCR...")

        # Convert page to image
        image = pdf_page_to_image(pdf_path, page_num)
        if not image:
            print("Failed to convert PDF page to image")
            return "", False

        # Use LLM for OCR
        ocr_text = llm_ocr_page(image, openai_client, model)
        if ocr_text:
            print(f"LLM OCR successful: extracted {len(ocr_text)} characters")
            return ocr_text, True
        else:
            print("LLM OCR failed")
            return "", True

    except Exception as e:
        print(f"Error in hybrid text extraction: {e}")
        return "", False


def extract_full_pdf_text_hybrid(
    pdf_path: Path,
    openai_client: Optional[openai.OpenAI] = None,
    model: str = "gpt-4o"
) -> Tuple[dict, bool]:
    """
    Extract text from all pages of a PDF using hybrid approach.

    Args:
        pdf_path: Path to the PDF file
        openai_client: OpenAI client for OCR fallback
        model: Model to use for OCR

    Returns:
        Tuple of (page_texts, any_ocr_used)
        - page_texts: Dict mapping page_num -> text
        - any_ocr_used: True if OCR was used for any page
    """
    page_texts = {}
    any_ocr_used = False

    try:
        with fitz.open(str(pdf_path)) as doc:
            num_pages = len(doc)

        for page_num in range(num_pages):
            text, used_ocr = extract_text_hybrid(
                pdf_path,
                page_num,
                openai_client,
                model
            )
            page_texts[page_num] = text
            if used_ocr:
                any_ocr_used = True

        return page_texts, any_ocr_used
    except Exception as e:
        print(f"Error extracting full PDF text: {e}")
        return {}, False
