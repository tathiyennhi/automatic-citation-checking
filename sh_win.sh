#!/bin/bash

D:\project\venv\Scripts\activate

# Cài đặt PyTorch cho Windows (CPU)
echo "Cài đặt PyTorch cho Windows (CPU)..."
pip install torch torchvision torchaudio -f https://download.pytorch.org/whl/cpu/torch_stable.html

echo "Cài đặt các gói khác từ requirements.txt..."
pip install -r requirements.txt

echo "Hoàn tất cài đặt trên Windows!"
