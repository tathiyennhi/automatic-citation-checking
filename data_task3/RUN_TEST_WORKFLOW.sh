#!/bin/bash

# WORKFLOW: Test V2 logic on 100 files, compare with V1, decide to deploy

set -e  # Exit on error

echo "================================================================================"
echo "TASK3 V2 TESTING WORKFLOW"
echo "================================================================================"
echo ""

BASE_DIR="/Users/tathiyennhi/Documents/automatic-citation-checking"
cd "$BASE_DIR"

# Step 1: Generate 100 files with V2 logic
echo "STEP 1: Generate 100 files with NEW logic (V2)"
echo "--------------------------------------------------------------------------------"
python3 data_task3/main_v2.py \
  --task2-dir data_outputs/task2 \
  --output-dir data_outputs/task3_v2_test \
  --limit 100 \
  --force-reprocess

echo ""
echo "✅ Step 1 complete: 100 files generated in data_outputs/task3_v2_test"
echo ""

# Step 2: Compare with V1
echo "STEP 2: Compare V1 (old) vs V2 (new)"
echo "--------------------------------------------------------------------------------"
python3 data_task3/compare_versions_detailed.py \
  --v1-dir data_outputs/task3_manual_review \
  --v2-dir data_outputs/task3_v2_test \
  --report-file data_task3/TEST_100_FILES_COMPARISON.txt

echo ""
echo "✅ Step 2 complete: Comparison report generated"
echo ""

# Step 3: Show summary
echo "================================================================================"
echo "TEST COMPLETE - REVIEW RESULTS"
echo "================================================================================"
echo ""
echo "📄 Report location: data_task3/TEST_100_FILES_COMPARISON.txt"
echo "📄 JSON details:    data_task3/TEST_100_FILES_COMPARISON.json"
echo ""
echo "NEXT STEPS:"
echo "1. Review the report above"
echo "2. If V2 quality > V1 quality:"
echo "   → Run full deployment: bash data_task3/DEPLOY_V2_FULL.sh"
echo "3. If V2 quality <= V1 quality:"
echo "   → Debug V2 logic, iterate, re-test"
echo ""
echo "================================================================================"
