@echo off
echo ============================================
echo   MTS to MP4 Converter - Build Script
echo ============================================
echo.

set PYTHON_EXE=C:\Users\jjone\AppData\Local\Programs\Python\Python312\python.exe

if exist "venv\Scripts\activate.bat" (
    echo [1/3] Activating venv...
    call venv\Scripts\activate.bat
    set PYTHON_EXE=python
) else (
    echo [!] No venv found. Using Python312.
)

echo [2/3] Installing dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo [3/3] Building EXE...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name "MTS_to_MP4_Converter" --add-data "converter.py;." --hidden-import ttkbootstrap main.py

echo.
if exist "dist\MTS_to_MP4_Converter.exe" (
    echo ============================================
    echo   Build OK!
    echo   Output: dist\MTS_to_MP4_Converter.exe
    echo ============================================
) else (
    echo ============================================
    echo   Build FAILED! Check errors above.
    echo ============================================
)

echo.
pause
