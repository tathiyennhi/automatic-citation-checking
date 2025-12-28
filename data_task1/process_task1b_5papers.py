#!/usr/bin/env python3
"""
Process task 1b for the 5 papers only
"""
import json
import os
from pathlib import Path
import sys

# Import task 1b pipeline
sys.path.insert(0, str(Path(__file__).parent))
from main_1b import CitationExtractionPipeline

def main():
    print("="*70)
    print("PROCESSING TASK 1B - CITATION EXTRACTION (5 PAPERS ONLY)")
    print("="*70)

    processor = CitationExtractionPipeline()

    # Process each paper folder separately
    task1a_dir = Path("../data_outputs/task1a")
    output_dir = Path("../data_outputs/task1b")
    output_dir.mkdir(parents=True, exist_ok=True)

    total_citation_sentences = 0
    total_individual_citations = 0
    global_index = 0

    papers_summary = []

    for paper_dir in sorted(task1a_dir.glob("*/")):
        if not paper_dir.is_dir():
            continue

        paper_name = paper_dir.name
        print(f"\n{'='*70}")
        print(f"Processing: {paper_name[:60]}...")
        print(f"{'='*70}")

        paper_sentences = 0
        paper_citations = 0

        # Process all .label files in this paper folder
        for label_file in sorted(paper_dir.glob("*.label")):
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Get citation sentences
                sentences = data.get("correct_citations", [])
                style = data.get("style", "")

                if not style or not sentences:
                    continue

                # Process each citation sentence
                for sentence in sentences:
                    citations_data = processor.extract_citations_with_mask(sentence)

                    # Only create file if citations found
                    if citations_data["citation_references"]:
                        # Create .in file
                        processor.create_in_file(sentence, global_index, str(output_dir))

                        # Create .label file
                        processor.create_label_file(citations_data, global_index, str(output_dir))

                        paper_sentences += 1
                        paper_citations += len(citations_data["citation_references"])
                        global_index += 1

            except Exception as e:
                print(f"Error processing {label_file}: {e}")
                continue

        print(f"✅ Paper processed:")
        print(f"   Citation sentences: {paper_sentences}")
        print(f"   Individual citations extracted: {paper_citations}")

        papers_summary.append({
            'name': paper_name,
            'sentences': paper_sentences,
            'citations': paper_citations
        })

        total_citation_sentences += paper_sentences
        total_individual_citations += paper_citations

    # Print summary
    print(f"\n{'='*70}")
    print("TASK 1B PROCESSING SUMMARY")
    print(f"{'='*70}")

    for i, paper in enumerate(papers_summary, 1):
        print(f"\nPaper {i}: {paper['name'][:50]}...")
        print(f"  Citation sentences: {paper['sentences']}")
        print(f"  Individual citations: {paper['citations']}")

    print(f"\n{'='*70}")
    print(f"TỔNG KẾT:")
    print(f"{'='*70}")
    print(f"✅ Citation sentences processed: {total_citation_sentences}")
    print(f"✅ Individual citations extracted: {total_individual_citations}")
    print(f"✅ Files created: {global_index} cặp (.in và .label)")
    print(f"📂 Output directory: {output_dir}")
    print(f"{'='*70}\n")

    # Show example
    if global_index > 0:
        print("\n" + "="*70)
        print("EXAMPLE OUTPUT")
        print("="*70)
        example_file = output_dir / "citation_000.label"
        if example_file.exists():
            with open(example_file, 'r', encoding='utf-8') as f:
                example = json.load(f)
            print(f"File: citation_000.label")
            print(f"Text: {example.get('text','')[:100]}...")
            print(f"Mask: {example.get('mask','')}")
            refs = example.get('citation_references', [])
            print(f"Citations found: {len(refs)}")
            if refs:
                print("Citations mapping:")
                for item in refs:
                    print(f"  {item['citation_marker']}: {item['reference_text']}")
        print("="*70)

if __name__ == "__main__":
    main()
