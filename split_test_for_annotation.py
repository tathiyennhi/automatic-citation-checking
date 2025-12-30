#!/usr/bin/env python3
"""
Split Task 3 test set for annotation:
- Clone test → test_v4_original (backup)
- Sample 500 random files → test_gold_500 (for human annotation)
- Remaining 2,500 files → test_silver_2500 (V4 labels)
"""

import json
import random
import shutil
from pathlib import Path

def split_test_for_annotation():
    print("="*60)
    print("SPLIT TEST SET FOR ANNOTATION")
    print("="*60)

    # Paths
    test_dir = Path("data_outputs/task3/test")
    backup_dir = Path("data_outputs/task3/test_v4_original")
    gold_dir = Path("data_outputs/task3/test_gold_500")
    silver_dir = Path("data_outputs/task3/test_silver_2500")

    # Check test directory exists
    if not test_dir.exists():
        print(f"❌ Error: {test_dir} does not exist!")
        return

    # Get all test files
    test_files = sorted([f.stem for f in test_dir.glob("*.label")])
    total_files = len(test_files)

    print(f"\n📊 Found {total_files:,} test files")

    if total_files < 500:
        print(f"❌ Error: Need at least 500 files, found {total_files}")
        return

    # Step 1: Clone test → test_v4_original (backup)
    print(f"\n1️⃣  Creating V4 backup...")
    if backup_dir.exists():
        print(f"   ⚠️  {backup_dir} already exists, skipping clone")
    else:
        shutil.copytree(test_dir, backup_dir)
        print(f"   ✅ Cloned {total_files:,} files to {backup_dir}/")

    # Step 2: Sample 500 random files
    print(f"\n2️⃣  Sampling 500 files for human annotation...")
    random.seed(42)  # Reproducible
    gold_files = random.sample(test_files, 500)
    silver_files = [f for f in test_files if f not in gold_files]

    print(f"   ✅ Selected 500 files for annotation")
    print(f"   ✅ {len(silver_files):,} files remain as V4 silver test")

    # Save selection
    selection = {
        "gold_500": gold_files,
        "silver_2500": silver_files,
        "seed": 42,
        "total": total_files
    }

    selection_file = Path("data_outputs/task3/test_split_selection.json")
    with open(selection_file, 'w') as f:
        json.dump(selection, f, indent=2)
    print(f"   ✅ Saved selection to {selection_file}")

    # Step 3: Create gold and silver directories
    print(f"\n3️⃣  Splitting files into gold and silver folders...")
    gold_dir.mkdir(exist_ok=True)
    silver_dir.mkdir(exist_ok=True)

    # Move 500 files to gold folder
    print(f"   Moving 500 files to {gold_dir}/...")
    for i, file_id in enumerate(gold_files):
        src = test_dir / f"{file_id}.label"
        dst = gold_dir / f"{file_id}.label"
        shutil.move(str(src), str(dst))

        if (i + 1) % 100 == 0:
            print(f"     Moved {i+1}/500 files...")

    print(f"   ✅ Gold folder complete: {len(list(gold_dir.glob('*.label')))} files")

    # Move 2,500 files to silver folder
    print(f"   Moving {len(silver_files):,} files to {silver_dir}/...")
    for i, file_id in enumerate(silver_files):
        src = test_dir / f"{file_id}.label"
        dst = silver_dir / f"{file_id}.label"
        shutil.move(str(src), str(dst))

        if (i + 1) % 500 == 0:
            print(f"     Moved {i+1}/{len(silver_files)} files...")

    print(f"   ✅ Silver folder complete: {len(list(silver_dir.glob('*.label')))} files")

    # Remove empty test folder
    if test_dir.exists() and not list(test_dir.glob("*.label")):
        test_dir.rmdir()
        print(f"   ✅ Removed empty {test_dir}/")

    # Summary
    print("\n" + "="*60)
    print("✅ SPLIT COMPLETE!")
    print("="*60)
    print(f"\nFolder structure:")
    print(f"  data_outputs/task3/")
    print(f"    ├── train/              (55,556 files - V4 training)")
    print(f"    ├── val/                (3,000 files - V4 validation)")
    print(f"    ├── test_v4_original/   ({total_files:,} files - V4 backup)")
    print(f"    ├── test_gold_500/      (500 files - FOR ANNOTATION ⭐)")
    print(f"    └── test_silver_2500/   ({len(silver_files):,} files - V4 optional test)")

    print(f"\n📋 Selection saved: {selection_file}")

    print(f"\n🎯 Next steps:")
    print(f"  1. Annotate 500 files in test_gold_500/")
    print(f"  2. Use test_v4_original/ as V4 baseline reference")
    print(f"  3. Optionally test on test_silver_2500/ for large-scale eval")

    print("\n" + "="*60)

if __name__ == "__main__":
    split_test_for_annotation()
