@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building FinFlow executable...
pyinstaller --noconfirm --onefile --windowed --name="FinFlow" --add-data "ui/styles.qss;ui" --add-data "assets/icon.png;assets" --icon="assets/icon.ico" main.py

echo Build completed! Output in dist/FinFlow.exe
pause
