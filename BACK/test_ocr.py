"""
Test script for OCR functionality on scanned PDF
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import openai
from ocr_utils import extract_text_hybrid, is_scanned_pdf
import re

# Load environment variables
load_dotenv()

# Setup
pdf_path = Path("uploads/Candidate123.pdf")
search_term = "Team Management and Delivery Governance"

print("=" * 80)
print("OCR FUNCTIONALITY TEST")
print("=" * 80)

# Check if PDF is scanned
print(f"\n1. CHECKING IF PDF IS SCANNED")
print("-" * 80)
is_scanned = is_scanned_pdf(pdf_path, page_num=0)
print(f"Is scanned PDF: {is_scanned}")

if not is_scanned:
    print("This PDF contains extractable text, OCR not needed.")
    exit(0)

# Setup OpenAI client
print(f"\n2. SETTING UP OPENAI CLIENT FOR OCR")
print("-" * 80)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env file")
    print("OCR requires OpenAI API access for GPT-4 Vision")
    exit(1)

model = os.getenv("OPENAI_MODEL") or "gpt-4o"
print(f"Using model: {model}")

client = openai.OpenAI(
    api_key=api_key,
    base_url=os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
)

# Test OCR extraction
print(f"\n3. EXTRACTING TEXT FROM PAGE 1 USING LLM OCR")
print("-" * 80)
print("This will use OpenAI API and incur costs...")

extracted_text, used_ocr = extract_text_hybrid(
    pdf_path,
    page_num=0,
    openai_client=client,
    model=model
)

if not extracted_text:
    print("ERROR: OCR extraction failed")
    exit(1)

print(f"OCR used: {used_ocr}")
print(f"Extracted text length: {len(extracted_text)} characters")
print(f"\nFirst 500 characters:")
print("-" * 80)
print(extracted_text[:500])
print("-" * 80)

# Search for the header
print(f"\n4. SEARCHING FOR HEADER: '{search_term}'")
print("-" * 80)

# Case-sensitive search
if search_term in extracted_text:
    print(f"✓ FOUND (exact case match)")
    idx = extracted_text.find(search_term)
    print(f"  Position: {idx}")
    context_start = max(0, idx - 50)
    context_end = idx + len(search_term) + 100
    print(f"  Context: ...{extracted_text[context_start:context_end]}...")
else:
    print(f"✗ NOT FOUND (exact case)")

# Case-insensitive search
if search_term.lower() in extracted_text.lower():
    print(f"✓ FOUND (case-insensitive)")
    idx_lower = extracted_text.lower().find(search_term.lower())
    print(f"  Position: {idx_lower}")
    actual_text = extracted_text[idx_lower:idx_lower+len(search_term)]
    print(f"  Actual text: '{actual_text}'")
else:
    print(f"✗ NOT FOUND (case-insensitive)")

# Test regex pattern matching (from the actual code)
print(f"\n5. TESTING REGEX PATTERN (from _extract_criterion_paragraph)")
print("-" * 80)
pattern = re.compile(rf"{re.escape(search_term)}", re.IGNORECASE)
matches = pattern.findall(extracted_text)
print(f"Pattern: {pattern.pattern}")
print(f"Found {len(matches)} matches")
if matches:
    print(f"Matches: {matches}")
    for match in pattern.finditer(extracted_text):
        print(f"  - Position {match.start()}: '{match.group()}'")
else:
    print("✗ NO MATCHES")

# Show all lines containing "Team"
print(f"\n6. ALL LINES CONTAINING 'team' (case-insensitive)")
print("-" * 80)
lines = extracted_text.splitlines()
team_lines = [line for line in lines if "team" in line.lower()]
print(f"Found {len(team_lines)} lines containing 'team'")
for idx, line in enumerate(team_lines[:10]):  # Show first 10
    print(f"  {idx + 1}. {line.strip()}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

if search_term.lower() in extracted_text.lower():
    print("✓ SUCCESS: OCR successfully extracted the text and found the header!")
else:
    print("✗ FAILED: Header not found in OCR-extracted text")
