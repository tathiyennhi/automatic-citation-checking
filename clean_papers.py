#!/usr/bin/env python3
"""
Xóa các PDFs không có trong manifest.jsonl
"""
import json
import re
from pathlib import Path

PAPERS_DIR = Path("papers")
MANIFEST = PAPERS_DIR / "manifest.jsonl"

def sanitize_filename(title: str, fallback: str = "unknown") -> str:
    """Same logic as crawl_papers.py"""
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name or fallback

def load_manifest():
    """Load manifest and get expected PDF filenames"""
    expected_pdfs = set()

    if not MANIFEST.exists():
        print(f"❌ Manifest not found: {MANIFEST}")
        return expected_pdfs

    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            title = rec.get("title", "")
            h = rec.get("hash", "")[:16]

            # Generate expected filename
            fname = sanitize_filename(title, h) + ".pdf"
            expected_pdfs.add(fname)
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Invalid JSON line: {e}")
            continue

    print(f"✅ Loaded {len(expected_pdfs)} expected PDFs from manifest")
    return expected_pdfs

def find_extra_pdfs():
    """Find PDFs not in manifest"""
    expected = load_manifest()

    if not PAPERS_DIR.exists():
        print(f"❌ Papers directory not found: {PAPERS_DIR}")
        return []

    all_pdfs = list(PAPERS_DIR.glob("*.pdf"))
    print(f"📁 Found {len(all_pdfs)} total PDFs in {PAPERS_DIR}")

    extra_pdfs = []
    for pdf in all_pdfs:
        if pdf.name not in expected:
            extra_pdfs.append(pdf)

    return extra_pdfs

def main():
    print("="*60)
    print("🧹 CLEAN PAPERS - Remove PDFs not in manifest")
    print("="*60)

    extra_pdfs = find_extra_pdfs()

    if not extra_pdfs:
        print("\n✅ No extra PDFs found. All PDFs are in manifest!")
        return

    print(f"\n⚠️  Found {len(extra_pdfs)} PDFs NOT in manifest:")
    print("="*60)
    for i, pdf in enumerate(extra_pdfs[:20], 1):  # Show first 20
        print(f"{i:4d}. {pdf.name}")

    if len(extra_pdfs) > 20:
        print(f"... and {len(extra_pdfs) - 20} more")

    print("="*60)
    print(f"\n⚠️  Total to delete: {len(extra_pdfs)} PDFs")

    # Ask for confirmation
    response = input("\n❓ Delete these PDFs? (yes/no): ").strip().lower()

    if response == "yes":
        deleted = 0
        for pdf in extra_pdfs:
            try:
                pdf.unlink()
                deleted += 1
            except Exception as e:
                print(f"❌ Error deleting {pdf.name}: {e}")

        print(f"\n✅ Deleted {deleted}/{len(extra_pdfs)} PDFs")
        print(f"📊 Remaining PDFs: {len(list(PAPERS_DIR.glob('*.pdf')))}")
    else:
        print("\n❌ Cancelled. No files deleted.")

if __name__ == "__main__":
    main()
