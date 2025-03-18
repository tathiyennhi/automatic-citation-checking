#!/bin/bash

echo "Starting setup process for reservation_spacy..."

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

# Tải model spaCy
python -m spacy download en_core_web_sm

# Chạy file Python chính
echo "Running main.py..."
python main.py

echo "Setup and execution completed!" 