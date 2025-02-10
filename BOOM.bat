@echo off
REM Change to the directory where the batch file is located
cd /d %~dp0

REM Set the Python version
set PYTHON_VERSION=3.11.0

REM Check if Python is in the PATH
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not found in PATH. Attempting to add it...
    set "PYTHON_PATH=C:\Python%PYTHON_VERSION%"
    setx PATH "%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"
    echo Added Python to PATH. Please restart your command prompt.
    pause
    exit /b
) else (
    echo Python found in PATH.
)

REM Set up the virtual environment
if not exist vJAM (
    python -m venv vJAM
)
call vJAM\Scripts\activate

REM Install dependencies
echo Installing dependencies...
python.exe -m pip install --upgrade setuptools
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

echo Monitoring settops on network
REM start /B cmd /C "python scripts\stb_search.py"

echo Checking Active JAMboree Version
REM python versionControl.py

REM Run the script
echo Running JAMboree.py...
python JAMboree.py

REM Deactivate the virtual environment
call vJAM\Scripts\deactivate
echo Done.
REM Pause the script to see any output before it closes
pause
endlocal
