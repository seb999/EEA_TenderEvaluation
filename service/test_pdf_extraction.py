import fitz
import re
from pathlib import Path
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Open the PDF
pdf_path = Path("uploads/Candidate123.pdf")
doc = fitz.open(str(pdf_path))

print("=" * 80)
print("PDF TEXT EXTRACTION DIAGNOSTIC")
print("=" * 80)

print(f"\nPDF Info:")
print(f"  - Number of pages: {len(doc)}")
print(f"  - File size: {pdf_path.stat().st_size:,} bytes")

# Extract text from first page
page = doc[0]
text = page.get_text("text")

print(f"\n1. TOTAL TEXT LENGTH: {len(text)} characters")
print(f"\n2. FIRST 1000 CHARACTERS:")
print("-" * 80)
print(text[:1000])
print("-" * 80)

# Search for the header
search_term = "Team Management and Delivery Governance"
print(f"\n3. SEARCHING FOR: '{search_term}'")
print("-" * 80)

# Case-sensitive search
if search_term in text:
    print(f"OK FOUND (exact case match)")
    idx = text.find(search_term)
    print(f"  Position: {idx}")
    print(f"  Context: ...{text[max(0, idx-50):idx+len(search_term)+50]}...")
else:
    print(f"X NOT FOUND (exact case)")

# Case-insensitive search
if search_term.lower() in text.lower():
    print(f"OK FOUND (case-insensitive)")
    idx_lower = text.lower().find(search_term.lower())
    print(f"  Position: {idx_lower}")
    actual_text = text[idx_lower:idx_lower+len(search_term)]
    print(f"  Actual text: '{actual_text}'")
    print(f"  Context: ...{text[max(0, idx_lower-50):idx_lower+len(search_term)+50]}...")
else:
    print(f"X NOT FOUND (case-insensitive)")

# Test regex patterns (from the code)
print(f"\n4. TESTING REGEX PATTERNS (from _extract_criterion_paragraph)")
print("-" * 80)

search_label = "Team Management and Delivery Governance"
auto_increment = False

if not auto_increment:
    # Pattern from the code for non-auto-increment
    pattern = re.compile(rf"{re.escape(search_label)}", re.IGNORECASE)
    matches = pattern.findall(text)
    print(f"Pattern: {pattern.pattern}")
    print(f"Found {len(matches)} matches")
    if matches:
        print(f"Matches: {matches}")
        for match in pattern.finditer(text):
            print(f"  - Position {match.start()}: '{match.group()}'")
    else:
        print("X NO MATCHES")

# Check for special characters
print(f"\n5. CHECKING FOR SPECIAL CHARACTERS")
print("-" * 80)
# Look for "Team Management" specifically
team_mgmt_variants = [
    "Team Management",
    "Team\u00a0Management",  # non-breaking space
    "Team  Management",  # double space
    "Team\tManagement",  # tab
]

for variant in team_mgmt_variants:
    if variant in text:
        print(f"OK Found variant: {repr(variant)}")

# Show lines containing "Team"
print(f"\n6. ALL LINES CONTAINING 'Team':")
print("-" * 80)
lines = text.splitlines()
for idx, line in enumerate(lines):
    if "team" in line.lower():
        print(f"Line {idx}: {repr(line.strip())}")

# Check for images
print(f"\n7. IMAGE ANALYSIS")
print("-" * 80)
image_list = page.get_images()
print(f"Number of images on page 1: {len(image_list)}")
if image_list:
    print("This PDF contains images. If text extraction returned 0 characters,")
    print("this is likely a SCANNED DOCUMENT, not a PDF with real text.")
    print("\nImage details:")
    for img_idx, img in enumerate(image_list[:5]):  # Show first 5 images
        xref = img[0]
        try:
            base_image = doc.extract_image(xref)
            print(f"  Image {img_idx + 1}:")
            print(f"    - Format: {base_image['ext']}")
            print(f"    - Size: {base_image['width']}x{base_image['height']}")
            print(f"    - Colorspace: {base_image.get('colorspace', 'N/A')}")
        except:
            print(f"  Image {img_idx + 1}: Could not extract details")

# Try different text extraction methods
print(f"\n8. TRYING ALTERNATIVE EXTRACTION METHODS")
print("-" * 80)
text_dict = page.get_text("dict")
blocks = text_dict.get("blocks", [])
print(f"Number of blocks: {len(blocks)}")
text_blocks = [b for b in blocks if b.get("type") == 0]  # type 0 = text
image_blocks = [b for b in blocks if b.get("type") == 1]  # type 1 = image
print(f"  - Text blocks: {len(text_blocks)}")
print(f"  - Image blocks: {len(image_blocks)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
if len(text) == 0 and len(image_blocks) > 0:
    print("X This PDF is a SCANNED DOCUMENT (images only, no extractable text)")
    print("  You need to use OCR (Optical Character Recognition) to extract text.")
elif len(text) > 0:
    print("OK This PDF contains extractable text")
else:
    print("? Unknown: No text and no images detected")
print("=" * 80)
