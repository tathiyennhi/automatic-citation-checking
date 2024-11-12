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
D:\myenv\Scripts\activate

# Tạo môi trường ảo trong thư mục người dùng (Mac)
python -m venv /Users/tathiyennhi/myenv
source /Users/tathiyennhi/myenv/bin/activate

# run mac bash file 
chmod +x sh_mac.sh
./sh_mac.sh
brew install swig # nếu chưa có 

# run windows bash file 
chmod +x sh_windows.sh
./sh_windows.sh