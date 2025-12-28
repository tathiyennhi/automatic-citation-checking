#!/usr/bin/env python3
"""
Test script để xử lý 5 papers đầu tiên từ manifest.jsonl
"""

import json
import os
import sys
from pathlib import Path
import re

# Import processor từ main_flow
sys.path.insert(0, str(Path(__file__).parent / "main_flow"))
from main import PDFToPipelineProcessor


def sanitize_filename(title: str) -> str:
    """Tạo tên file từ title giống như trong crawl_papers.py"""
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", title)[:120]
    return name


def find_pdf_file(papers_dir: Path, title: str, hash_value: str) -> Path:
    """Tìm file PDF dựa trên title hoặc hash"""
    # Thử tìm theo title
    sanitized = sanitize_filename(title)
    pdf_path = papers_dir / f"{sanitized}.pdf"
    if pdf_path.exists():
        return pdf_path

    # Thử tìm theo hash
    hash_path = papers_dir / f"{hash_value[:16]}.pdf"
    if hash_path.exists():
        return hash_path

    # Tìm file chứa một phần của title
    for pdf_file in papers_dir.glob("*.pdf"):
        if sanitized[:50] in pdf_file.stem or title[:30].lower() in pdf_file.stem.lower():
            return pdf_file

    return None


def main():
    # Đường dẫn
    base_dir = Path(__file__).parent
    manifest_path = base_dir / "papers" / "manifest.jsonl"
    papers_dir = base_dir / "papers"
    output_base = base_dir / "main_flow" / "out"

    # Đọc 5 papers đầu từ manifest
    print("=" * 70)
    print("Testing first 5 papers from manifest")
    print("=" * 70)

    papers = []
    with open(manifest_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            papers.append(json.loads(line))

    # Khởi tạo processor
    processor = PDFToPipelineProcessor(
        sentences_per_file=5,
        remove_headings=True,
        remove_references=True
    )

    # Xử lý từng paper
    results = []
    for idx, paper in enumerate(papers, 1):
        print(f"\n{'='*70}")
        print(f"Paper {idx}/5: {paper['title'][:60]}...")
        print(f"DOI: {paper.get('doi', 'N/A')}")
        print(f"{'='*70}")

        # Tìm PDF file
        pdf_path = find_pdf_file(papers_dir, paper['title'], paper['hash'])

        if not pdf_path:
            print(f"⚠️  PDF not found for: {paper['title']}")
            results.append({
                'paper': paper['title'],
                'status': 'PDF not found',
                'pdf_path': None
            })
            continue

        print(f"✓ Found PDF: {pdf_path.name}")

        # Tạo thư mục output riêng cho paper này
        output_dir = output_base / f"test_{idx:02d}_{paper['hash'][:8]}"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Xử lý PDF
            processor.process_pdf(str(pdf_path), str(output_dir))

            # Đếm số files được tạo
            in_files = list(output_dir.glob("*.in"))
            label_files = list(output_dir.glob("*.label"))

            results.append({
                'paper': paper['title'],
                'status': 'success',
                'pdf_path': str(pdf_path),
                'output_dir': str(output_dir),
                'files_created': len(in_files)
            })

            print(f"✓ Success: Created {len(in_files)} file pairs in {output_dir.name}")

        except Exception as e:
            print(f"✗ Error processing: {e}")
            results.append({
                'paper': paper['title'],
                'status': f'error: {str(e)}',
                'pdf_path': str(pdf_path)
            })

    # In summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    successful = sum(1 for r in results if r['status'] == 'success')
    print(f"Total papers: {len(papers)}")
    print(f"Successfully processed: {successful}")
    print(f"Failed/Not found: {len(papers) - successful}")

    print(f"\nDetailed results:")
    for idx, result in enumerate(results, 1):
        status_symbol = "✓" if result['status'] == 'success' else "✗"
        print(f"{idx}. {status_symbol} {result['paper'][:50]}...")
        print(f"   Status: {result['status']}")
        if result.get('output_dir'):
            print(f"   Output: {result['output_dir']}")

    print(f"\n{'='*70}")


if __name__ == "__main__":
    main()
