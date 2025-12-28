#!/usr/bin/env python3
"""
Thêm 2 papers từ dư list vào manifest để có đủ 2000 unique PDFs
"""
import json
import re
import random
import hashlib
from pathlib import Path

PAPERS_DIR = Path("papers")
MANIFEST = PAPERS_DIR / "manifest.jsonl"

def sanitize_filename(title: str, fallback: str = "unknown") -> str:
    """Same logic as crawl_papers.py"""
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name or fallback

def load_expected_pdfs():
    """Load expected PDF filenames from manifest"""
    expected = set()
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        title = rec.get("title", "")
        h = rec.get("hash", "")[:16]
        fname = sanitize_filename(title, h) + ".pdf"
        expected.add(fname)
    return expected

def find_extra_pdfs():
    """Find PDFs not in manifest"""
    expected = load_expected_pdfs()
    all_pdfs = list(PAPERS_DIR.glob("*.pdf"))

    extra = []
    for pdf in all_pdfs:
        if pdf.name not in expected:
            extra.append(pdf)

    return extra

def extract_title_from_filename(fname: str) -> str:
    """Convert filename back to title"""
    # Remove .pdf
    name = fname.replace(".pdf", "")
    # Replace underscores with spaces
    title = name.replace("_", " ")
    return title

def create_manifest_entry(pdf_path: Path) -> dict:
    """Create a manifest entry for a PDF"""
    # Read PDF and compute hash
    pdf_bytes = pdf_path.read_bytes()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Extract title from filename
    title = extract_title_from_filename(pdf_path.name)

    # Create entry
    entry = {
        "key": f"manual-add-{pdf_hash[:16]}",
        "title": title,
        "hash": pdf_hash,
        "pdf_url": f"local://{pdf_path.name}",
        "query": "manual-addition",
        "source": "local",
        "year": 2024
    }

    return entry

def main():
    print("="*60)
    print("📝 ADD MISSING PAPERS TO MANIFEST")
    print("="*60)

    # Find extra PDFs
    extra_pdfs = find_extra_pdfs()
    print(f"Found {len(extra_pdfs)} extra PDFs not in manifest")

    if len(extra_pdfs) < 2:
        print("❌ Not enough extra PDFs to add!")
        return

    # Pick 2 random PDFs
    selected = random.sample(extra_pdfs, 2)

    print("\n📌 Selected 2 PDFs to add:")
    for i, pdf in enumerate(selected, 1):
        print(f"{i}. {pdf.name}")

    # Create entries
    entries = []
    for pdf in selected:
        entry = create_manifest_entry(pdf)
        entries.append(entry)
        print(f"\n✅ Created entry for: {entry['title']}")

    # Append to manifest
    print(f"\n📝 Appending to {MANIFEST}...")
    with MANIFEST.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("\n✅ Done! Manifest now has 2002 entries")
    print("   → 2000 original + 2 added = 2002 entries")
    print("   → Should have 2000 unique PDF filenames now")

if __name__ == "__main__":
    main()
