#!/bin/bash

echo "Starting setup process for reservation_old_data..."

# Thoát môi trường ảo nếu đang kích hoạt
deactivate 2>/dev/null || true

# Xóa môi trường ảo cũ
rm -rf venv

# Tạo môi trường ảo mới
python3 -m venv venv

# Kích hoạt môi trường ảo
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy các file Python theo thứ tự
echo "Running BERT fine-tuning..."
python reservation_old_data/main_bert_finetune_citation_classification.py

echo "Running DPR..."
python reservation_old_data/main_dpr.py

echo "Running RAG..."
python reservation_old_data/main_rag.py

echo "Setup and execution completed!" 