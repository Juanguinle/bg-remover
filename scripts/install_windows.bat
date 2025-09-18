@echo off
echo Installing BG Remover for Windows...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv bg_remover_env
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call bg_remover_env\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install PyTorch with CUDA support (optional)
echo Installing PyTorch with CUDA support...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

REM Install transparent-background with workaround
echo Installing transparent-background...
pip install transparent-background==1.2.5 --no-deps
pip install easydict kornia opencv-python pyvirtualcam

REM Install rembg
echo Installing rembg...
pip install rembg

REM Install bg-remover
echo Installing bg-remover...
pip install bg-remover

REM Test installation
echo Testing installation...
bg-remover info

echo.
echo Installation completed successfully!
echo.
echo To use bg-remover:
echo 1. Activate the environment: bg_remover_env\Scripts\activate.bat
echo 2. Run: bg-remover --help
echo.
pause