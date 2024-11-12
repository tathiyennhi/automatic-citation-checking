#!/bin/bash

# Kích hoạt môi trường ảo (nếu chưa được kích hoạt)
source venv/bin/activate

# Cài đặt PyTorch cho macOS
echo "Cài đặt PyTorch cho macOS..."
pip3 install torch --index-url https://download.pytorch.org/whl/cpu

pip install faiss-cpu==1.7.2


# Cài đặt các gói khác từ requirements.txt
echo "Cài đặt các gói khác từ requirements.txt..."
pip3 install -r requirements.txt

echo "Hoàn tất cài đặt trên macOS!"
