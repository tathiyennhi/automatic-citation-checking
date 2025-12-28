"""
Clone task3 data into 2 versions:
1. task3_rule_based (original, read-only backup)
2. task3_manual_review (working copy for manual annotation)
"""

import shutil
from pathlib import Path
import json


def main():
    # Paths
    original = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3")
    rule_based = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_rule_based")
    manual_review = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_manual_review")

    print("="*80)
    print("CLONING TASK3 DATA FOR MANUAL REVIEW")
    print("="*80)
    print(f"Original: {original}")
    print(f"→ Clone 1 (rule-based backup): {rule_based}")
    print(f"→ Clone 2 (manual review): {manual_review}")
    print()

    # Check if original exists
    if not original.exists():
        print(f"❌ Error: Original directory not found: {original}")
        return

    # Count files
    label_files = list(original.glob("*.label"))
    print(f"Found {len(label_files)} .label files")
    print()

    # Check if clones already exist
    if rule_based.exists() or manual_review.exists():
        response = input("⚠️  Clone directories already exist. Overwrite? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return

        if rule_based.exists():
            shutil.rmtree(rule_based)
        if manual_review.exists():
            shutil.rmtree(manual_review)

    # Clone 1: Rule-based (backup)
    print("Copying to task3_rule_based...")
    shutil.copytree(original, rule_based)
    print(f"✅ Copied {len(list(rule_based.glob('*.label')))} files to {rule_based.name}")

    # Clone 2: Manual review (working copy)
    print("\nCopying to task3_manual_review...")
    shutil.copytree(original, manual_review)
    print(f"✅ Copied {len(list(manual_review.glob('*.label')))} files to {manual_review.name}")

    # Create metadata file
    metadata = {
        "original_path": str(original),
        "rule_based_path": str(rule_based),
        "manual_review_path": str(manual_review),
        "total_files": len(label_files),
        "created_date": "2025-01-14",
        "purpose": "Manual quality control for span extraction training data",
        "notes": [
            "task3_rule_based: Read-only backup of rule-based extraction results",
            "task3_manual_review: Working copy for manual annotation and corrections"
        ]
    }

    metadata_file = Path("/Users/tathiyennhi/Documents/automatic-citation-checking/data_outputs/task3_metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print()
    print("="*80)
    print("✅ CLONING COMPLETE")
    print("="*80)
    print(f"📁 Rule-based backup: {rule_based}")
    print(f"📁 Manual review (work here): {manual_review}")
    print(f"📄 Metadata: {metadata_file}")
    print()
    print("Next steps:")
    print("1. Use the manual annotation tool to review short spans")
    print("2. Changes will be saved to task3_manual_review only")
    print("3. Original and rule-based versions remain untouched")


if __name__ == "__main__":
    main()
