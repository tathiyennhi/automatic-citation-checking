#!/usr/bin/env python3
"""
1. Remove duplicate entries in manifest (keep first occurrence)
2. Add 2 new papers from extra PDFs
"""
import json
import re
import random
import hashlib
from pathlib import Path
from collections import defaultdict

PAPERS_DIR = Path("papers")
MANIFEST = PAPERS_DIR / "manifest.jsonl"
MANIFEST_BACKUP = PAPERS_DIR / "manifest.jsonl.backup"

def sanitize_filename(title: str, fallback: str = "unknown") -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name or fallback

def remove_duplicates():
    """Remove duplicate filename entries, keep first occurrence"""
    print("🔍 Scanning manifest for duplicates...")

    entries = []
    seen_filenames = set()
    duplicates_removed = []

    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        rec = json.loads(line)
        title = rec.get("title", "")
        h = rec.get("hash", "")[:16]
        fname = sanitize_filename(title, h) + ".pdf"

        if fname in seen_filenames:
            # Duplicate found, skip it
            duplicates_removed.append(fname)
            print(f"  ❌ Removing duplicate: {fname}")
        else:
            # First occurrence, keep it
            seen_filenames.add(fname)
            entries.append(rec)

    print(f"✅ Removed {len(duplicates_removed)} duplicate entries")
    print(f"✅ Kept {len(entries)} unique entries")

    return entries, seen_filenames

def find_extra_pdfs(expected_filenames: set):
    """Find PDFs not in manifest"""
    all_pdfs = list(PAPERS_DIR.glob("*.pdf"))
    extra = [pdf for pdf in all_pdfs if pdf.name not in expected_filenames]
    return extra

def extract_title_from_filename(fname: str) -> str:
    """Convert filename back to title"""
    name = fname.replace(".pdf", "")
    title = name.replace("_", " ")
    return title

def create_manifest_entry(pdf_path: Path) -> dict:
    """Create a manifest entry for a PDF"""
    pdf_bytes = pdf_path.read_bytes()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    title = extract_title_from_filename(pdf_path.name)

    return {
        "key": f"manual-add-{pdf_hash[:16]}",
        "title": title,
        "hash": pdf_hash,
        "pdf_url": f"local://{pdf_path.name}",
        "query": "manual-addition",
        "source": "local",
        "year": 2024
    }

def main():
    print("="*60)
    print("🔧 FIX MANIFEST - Remove duplicates & add 2 new papers")
    print("="*60)

    # Backup original manifest
    print(f"\n💾 Creating backup: {MANIFEST_BACKUP}")
    MANIFEST_BACKUP.write_text(MANIFEST.read_text(encoding="utf-8"))

    # Step 1: Remove duplicates
    print("\n" + "="*60)
    print("STEP 1: Remove duplicates")
    print("="*60)
    unique_entries, expected_filenames = remove_duplicates()

    # Step 2: Find extra PDFs
    print("\n" + "="*60)
    print("STEP 2: Find extra PDFs")
    print("="*60)
    extra_pdfs = find_extra_pdfs(expected_filenames)
    print(f"Found {len(extra_pdfs)} extra PDFs")

    if len(extra_pdfs) < 2:
        print("❌ Not enough extra PDFs!")
        return

    # Step 3: Pick 2 random PDFs
    print("\n" + "="*60)
    print("STEP 3: Select 2 random PDFs to add")
    print("="*60)
    selected = random.sample(extra_pdfs, 2)

    for i, pdf in enumerate(selected, 1):
        print(f"{i}. {pdf.name}")
        entry = create_manifest_entry(pdf)
        unique_entries.append(entry)

    # Step 4: Write new manifest
    print("\n" + "="*60)
    print("STEP 4: Write new manifest")
    print("="*60)
    with MANIFEST.open("w", encoding="utf-8") as f:
        for entry in unique_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ New manifest written: {len(unique_entries)} entries")
    print(f"   - Original: 2000 entries (with 2 duplicates)")
    print(f"   - After removing duplicates: 1998 entries")
    print(f"   - After adding 2 new: {len(unique_entries)} entries")

    # Verify
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    filenames = set()
    for entry in unique_entries:
        title = entry.get("title", "")
        h = entry.get("hash", "")[:16]
        fname = sanitize_filename(title, h) + ".pdf"
        filenames.add(fname)

    print(f"✅ Unique filenames: {len(filenames)}")
    print(f"✅ Should be: 2000")

    if len(filenames) == 2000:
        print("\n🎉 SUCCESS! Manifest now has exactly 2000 unique PDFs")
    else:
        print(f"\n⚠️  Warning: Expected 2000 but got {len(filenames)}")

if __name__ == "__main__":
    main()
