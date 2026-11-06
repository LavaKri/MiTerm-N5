@echo off
rem Launch MiTerm-N5 in develop mode (--develop) from the project folder. Extra arguments are passed on.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Virtual environment not found. Create it with:
    echo   python -m venv .venv --system-site-packages
    echo   .venv\Scripts\python.exe -m pip install -e .[dev]
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m n5terminal --develop %*
