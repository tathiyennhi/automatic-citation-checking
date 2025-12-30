#!/usr/bin/env python3
"""
Split Task 3 data only (Task 2 already done)
"""

import json
import random
from pathlib import Path
import shutil

def create_splits(task_name, data_dir, val_size=3000, test_size=3000, seed=42):
    """Create train/val/test splits for a task"""

    print(f"\n{'='*60}")
    print(f"Creating splits for {task_name}")
    print(f"{'='*60}")

    # Get all .label files
    data_path = Path(data_dir)
    all_files = sorted([f.stem for f in data_path.glob('*.label')])

    total = len(all_files)
    print(f"Total files: {total:,}")

    if total == 0:
        print(f"❌ No .label files found in {data_dir}")
        return None

    # Shuffle with seed
    random.seed(seed)
    random.shuffle(all_files)

    # Split
    test_files = all_files[:test_size]
    val_files = all_files[test_size:test_size + val_size]
    train_files = all_files[test_size + val_size:]

    print(f"Train: {len(train_files):,} files ({len(train_files)/total*100:.1f}%)")
    print(f"Val:   {len(val_files):,} files ({len(val_files)/total*100:.1f}%)")
    print(f"Test:  {len(test_files):,} files ({len(test_files)/total*100:.1f}%)")

    # Verify no overlap
    assert len(set(train_files) & set(val_files)) == 0, "Train-Val overlap!"
    assert len(set(train_files) & set(test_files)) == 0, "Train-Test overlap!"
    assert len(set(val_files) & set(test_files)) == 0, "Val-Test overlap!"
    print("✅ No data leakage verified!")

    # Save splits to JSON
    splits = {
        'train': train_files,
        'val': val_files,
        'test': test_files,
        'metadata': {
            'total': total,
            'train_size': len(train_files),
            'val_size': len(val_files),
            'test_size': len(test_files),
            'seed': seed,
            'task': task_name
        }
    }

    split_file = data_path / 'data_splits.json'
    with open(split_file, 'w') as f:
        json.dump(splits, f, indent=2)
    print(f"✅ Saved split mapping to: {split_file}")

    # Create directories
    train_dir = data_path / 'train'
    val_dir = data_path / 'val'
    test_dir = data_path / 'test'

    for dir_path in [train_dir, val_dir, test_dir]:
        dir_path.mkdir(exist_ok=True)

    print("\nMoving files to train/val/test folders...")

    # Move files
    def move_files(file_list, target_dir, split_name):
        print(f"  Moving {len(file_list):,} files to {split_name}/...")
        for i, file_stem in enumerate(file_list):
            # Move .label files
            for ext in ['.label']:
                src = data_path / f"{file_stem}{ext}"
                dst = target_dir / f"{file_stem}{ext}"
                if src.exists():
                    shutil.move(str(src), str(dst))

            # Progress
            if (i + 1) % 1000 == 0:
                print(f"    Moved {i+1:,}/{len(file_list):,} files...")
        print(f"  ✅ {split_name} complete!")

    move_files(test_files, test_dir, 'test')
    move_files(val_files, val_dir, 'val')
    move_files(train_files, train_dir, 'train')

    print(f"\n✅ {task_name} splits complete!")
    print(f"   Train: {train_dir}")
    print(f"   Val:   {val_dir}")
    print(f"   Test:  {test_dir}")

    return splits

# Run Task 3 split
create_splits(
    task_name="Task 3 (Span Extraction)",
    data_dir="data_outputs/task3",
    val_size=3000,
    test_size=3000,
    seed=42
)

print("\n✅ Task 3 split complete!")
print("\nData structure:")
print("  data_outputs/task3/")
print("    ├── train/          (55,556 files)")
print("    ├── val/            (3,000 files)")
print("    ├── test/           (3,000 files)")
print("    └── data_splits.json")
