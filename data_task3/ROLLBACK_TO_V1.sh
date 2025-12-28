#!/bin/bash

# Rollback from V2 to V1 if needed

echo "================================================================================"
echo "⚠️  ROLLBACK TO V1"
echo "================================================================================"
echo ""
echo "This will restore V1 data from backup."
echo ""

read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled."
    exit 0
fi

BASE_DIR="/Users/tathiyennhi/Documents/automatic-citation-checking"
cd "$BASE_DIR"

if [ ! -d "data_outputs/task3_v1_backup" ]; then
    echo "❌ No backup found: data_outputs/task3_v1_backup"
    exit 1
fi

echo "Restoring from backup..."
echo ""

# Archive V2 for reference
if [ -d "data_outputs/task3_v2" ]; then
    echo "Archiving V2 → task3_v2_archived"
    mv data_outputs/task3_v2 data_outputs/task3_v2_archived
fi

# Restore V1
echo "Restoring V1 backup → task3_manual_review"
rm -rf data_outputs/task3_manual_review
cp -r data_outputs/task3_v1_backup data_outputs/task3_manual_review

echo ""
echo "✅ Rollback complete!"
echo ""
echo "📁 Active data: data_outputs/task3_manual_review (restored from V1)"
echo "📁 V2 archived: data_outputs/task3_v2_archived"
echo ""
