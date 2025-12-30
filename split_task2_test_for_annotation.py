#!/usr/bin/env python3
"""
Split Task 2 test set for annotation (same 500 IDs as Task 3)
- Clone test → test_v4_original (backup)
- Use SAME 500 file IDs from Task 3 → test_gold_500
- Remaining 2,500 files → test_silver_2500
"""

import json
import shutil
from pathlib import Path

def split_task2_test_for_annotation():
    print("="*60)
    print("SPLIT TASK 2 TEST SET FOR ANNOTATION")
    print("="*60)

    # Paths
    test_dir = Path("data_outputs/task2/test")
    backup_dir = Path("data_outputs/task2/test_v4_original")
    gold_dir = Path("data_outputs/task2/test_gold_500")
    silver_dir = Path("data_outputs/task2/test_silver_2500")

    # Load Task 3 selection (to use SAME 500 IDs)
    selection_file = Path("data_outputs/task3/test_split_selection.json")

    if not selection_file.exists():
        print(f"❌ Error: {selection_file} not found!")
        print("   Run split_test_for_annotation.py for Task 3 first!")
        return

    with open(selection_file, 'r') as f:
        task3_selection = json.load(f)

    gold_files = task3_selection['gold_500']
    silver_files = task3_selection['silver_2500']

    print(f"\n✅ Loaded Task 3 selection:")
    print(f"   Gold:   {len(gold_files)} files")
    print(f"   Silver: {len(silver_files)} files")
    print(f"   Using SAME IDs for Task 2")

    # Check test directory exists
    if not test_dir.exists():
        print(f"\n❌ Error: {test_dir} does not exist!")
        return

    # Get all test files
    test_files = sorted([f.stem for f in test_dir.glob("*.label")])
    total_files = len(test_files)

    print(f"\n📊 Found {total_files:,} test files in Task 2")

    # Step 1: Clone test → test_v4_original (backup)
    print(f"\n1️⃣  Creating V4 backup...")
    if backup_dir.exists():
        print(f"   ⚠️  {backup_dir} already exists, skipping clone")
    else:
        shutil.copytree(test_dir, backup_dir)
        print(f"   ✅ Cloned {total_files:,} files to {backup_dir}/")

    # Step 2: Create gold and silver directories
    print(f"\n2️⃣  Splitting files into gold and silver folders...")
    gold_dir.mkdir(exist_ok=True)
    silver_dir.mkdir(exist_ok=True)

    # Move 500 files to gold folder
    print(f"   Moving gold files to {gold_dir}/...")
    moved_gold = 0
    for i, file_id in enumerate(gold_files):
        # Move .in and .label files
        for ext in ['.in', '.label']:
            src = test_dir / f"{file_id}{ext}"
            dst = gold_dir / f"{file_id}{ext}"
            if src.exists():
                shutil.move(str(src), str(dst))

        moved_gold += 1

        if (i + 1) % 100 == 0:
            print(f"     Moved {i+1}/500 files...")

    print(f"   ✅ Gold folder complete: {moved_gold} files")

    # Move 2,500 files to silver folder
    print(f"   Moving silver files to {silver_dir}/...")
    moved_silver = 0
    for i, file_id in enumerate(silver_files):
        for ext in ['.in', '.label']:
            src = test_dir / f"{file_id}{ext}"
            dst = silver_dir / f"{file_id}{ext}"
            if src.exists():
                shutil.move(str(src), str(dst))

        moved_silver += 1

        if (i + 1) % 500 == 0:
            print(f"     Moved {i+1}/{len(silver_files)} files...")

    print(f"   ✅ Silver folder complete: {moved_silver} files")

    # Remove empty test folder
    remaining = list(test_dir.glob("*.label"))
    if test_dir.exists() and len(remaining) == 0:
        test_dir.rmdir()
        print(f"   ✅ Removed empty {test_dir}/")

    # Summary
    print("\n" + "="*60)
    print("✅ TASK 2 TEST SPLIT COMPLETE!")
    print("="*60)
    print(f"\nFolder structure:")
    print(f"  data_outputs/task2/")
    print(f"    ├── train/              (55,556 files)")
    print(f"    ├── val/                (3,000 files)")
    print(f"    ├── test_v4_original/   ({total_files:,} files - V4 backup)")
    print(f"    ├── test_gold_500/      ({moved_gold} files - SAME as Task 3 ⭐)")
    print(f"    └── test_silver_2500/   ({moved_silver} files - V4 optional)")

    # Verify
    gold_in = len(list(gold_dir.glob("*.in")))
    gold_label = len(list(gold_dir.glob("*.label")))
    silver_in = len(list(silver_dir.glob("*.in")))
    silver_label = len(list(silver_dir.glob("*.label")))

    print(f"\n📊 Verification:")
    print(f"  test_gold_500/:    {gold_in} .in, {gold_label} .label")
    print(f"  test_silver_2500/: {silver_in} .in, {silver_label} .label")

    if gold_label == 500:
        print(f"  ✅ Gold count matches Task 3!")
    else:
        print(f"  ⚠️  Gold count: expected 500, got {gold_label}")

    print(f"\n🎯 Ready for annotation!")
    print(f"  - Task 2 and Task 3 now have SAME 500 test files")
    print(f"  - Can annotate both tasks together")

    print("\n" + "="*60)

if __name__ == "__main__":
    split_task2_test_for_annotation()
