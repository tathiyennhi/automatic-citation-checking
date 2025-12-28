#!/bin/bash

# DEPLOY V2 to full dataset (60k+ files)
# Only run this if V2 test results are better than V1!

set -e

echo "================================================================================"
echo "⚠️  DEPLOY V2 LOGIC TO FULL DATASET"
echo "================================================================================"
echo ""
echo "This will:"
echo "1. Backup current data (task3_manual_review → task3_v1_backup)"
echo "2. Generate ALL 60k+ files with V2 logic → task3_v2"
echo "3. You can rollback if needed"
echo ""

read -p "Are you sure you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled."
    exit 0
fi

BASE_DIR="/Users/tathiyennhi/Documents/automatic-citation-checking"
cd "$BASE_DIR"

# Step 1: Backup V1 data
echo ""
echo "STEP 1: Backup existing data"
echo "--------------------------------------------------------------------------------"

if [ -d "data_outputs/task3_v1_backup" ]; then
    echo "⚠️  Backup already exists: data_outputs/task3_v1_backup"
    read -p "Overwrite backup? (yes/no): " overwrite
    if [ "$overwrite" != "yes" ]; then
        echo "Using existing backup."
    else
        echo "Removing old backup..."
        rm -rf data_outputs/task3_v1_backup
        echo "Creating new backup..."
        cp -r data_outputs/task3_manual_review data_outputs/task3_v1_backup
        echo "✅ Backup created: data_outputs/task3_v1_backup"
    fi
else
    echo "Creating backup..."
    cp -r data_outputs/task3_manual_review data_outputs/task3_v1_backup
    echo "✅ Backup created: data_outputs/task3_v1_backup"
fi

# Step 2: Generate full V2 dataset
echo ""
echo "STEP 2: Generate FULL dataset with V2 logic"
echo "--------------------------------------------------------------------------------"
echo "⏳ This will take ~2-4 hours depending on API speed..."
echo ""

python3 data_task3/main_v2.py \
  --task2-dir data_outputs/task2 \
  --output-dir data_outputs/task3_v2 \
  --force-reprocess

echo ""
echo "✅ V2 generation complete!"
echo ""

# Step 3: Compare full datasets
echo "STEP 3: Compare V1 vs V2 (full dataset)"
echo "--------------------------------------------------------------------------------"

python3 data_task3/compare_versions_detailed.py \
  --v1-dir data_outputs/task3_v1_backup \
  --v2-dir data_outputs/task3_v2 \
  --report-file data_task3/FULL_V1_VS_V2_COMPARISON.txt

echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "📁 V1 backup:     data_outputs/task3_v1_backup"
echo "📁 V2 new data:   data_outputs/task3_v2"
echo "📄 Comparison:    data_task3/FULL_V1_VS_V2_COMPARISON.txt"
echo ""
echo "NEXT STEPS:"
echo "1. Review comparison report"
echo "2. If satisfied, use V2 for training"
echo "3. To rollback: bash data_task3/ROLLBACK_TO_V1.sh"
echo ""
echo "================================================================================"
