@echo off
REM Creates .\venv with Python 3.12 and installs dependencies from pyproject.toml.
REM Run from the repo root: double-click, or `setup_venv.bat` in a terminal.

cd /d "%~dp0"

REM Prompt user to browse to python.exe (starts in the per-user Python folder if it exists)
for /f "usebackq delims=" %%I in (`
  powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $p = Join-Path $env:LOCALAPPDATA 'Programs\Python'; $dlg = New-Object System.Windows.Forms.OpenFileDialog; $dlg.Title = 'Select python.exe (3.12)'; $dlg.Filter = 'Python executable|python.exe'; if (Test-Path $p) { $dlg.InitialDirectory = $p }; if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::WriteLine($dlg.FileName) }"
`) do set "PYTHON_PATH=%%I"

REM Abort if dialog was closed or path is invalid
if not defined PYTHON_PATH (
    echo No file selected. Exiting.
    pause
    exit /b 1
)
if not exist "%PYTHON_PATH%" (
    echo Selected file does not exist: "%PYTHON_PATH%"
    pause
    exit /b 1
)

set ENV_FOLDER=venv

REM Validate Python 3.12
"%PYTHON_PATH%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"
if errorlevel 1 (
    echo Selected Python is not 3.12.x. Please choose a Python 3.12 interpreter.
    pause
    exit /b 1
)

if not exist pyproject.toml (
    echo pyproject.toml not found. Run this from the repo root.
    pause
    exit /b 1
)

REM Remove any existing virtual environment and create a fresh one
if exist "%ENV_FOLDER%" (
    echo Removing existing virtual environment at "%ENV_FOLDER%"...
    rmdir /s /q "%ENV_FOLDER%"
)

echo Creating virtual environment...
"%PYTHON_PATH%" -m venv "%ENV_FOLDER%"
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%ENV_FOLDER%\Scripts\activate"

echo Installing dependencies from pyproject.toml...
python -m pip install --upgrade pip
pip install -e .
if errorlevel 1 (
    echo Installation failed.
    pause
    exit /b 1
)

python -c "import cv2, streamlit, streamlit_image_coordinates; print('OK  opencv', cv2.__version__, '| aruco:', hasattr(cv2, 'aruco'), '| streamlit', streamlit.__version__)"

echo.
echo Setup complete. Activate later with:  venv\Scripts\activate
echo Run the app with:                     streamlit run app.py
pause
