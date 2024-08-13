@echo off
setlocal

REM Set the Python version
set PYTHON_VERSION=3.11.0

REM Check Python installation and set up the virtual environment
python -m venv vJAM
call vJAM\Scripts\activate

REM Install dependencies

echo Installing dependencies...
python.exe -m pip install --upgrade setuptools
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

echo Monitoring settops on network
start /B cmd /C "python scripts\stb_search.py"

REM Run the script
echo Running JAMboree.py...
python JAMboree.py

REM Deactivate the virtual environment
call vJAM\Scripts\deactivate
echo Done.
REM Pause the script to see any output before it closes
pause
endlocal
