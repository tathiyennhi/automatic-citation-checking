#windows
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python <your_main_file.py>

#macos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python <your_main_file.py>

# Tạo môi trường ảo trên ổ D: (Windows)
python -m venv D:/myenv

# Tạo môi trường ảo trong thư mục người dùng (Mac)
python -m venv /Users/tathiyennhi/myenv