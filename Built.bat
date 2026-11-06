@echo off
rem Build the distribution: Dist\MiTerm-N5\MiTerm-N5.exe with its libraries (PyInstaller, one
rem folder), then Dist\MiTerm-N5-<version>.zip. Run from anywhere; needs the virtual environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Create it with:
    echo   python -m venv .venv --system-site-packages
    echo   .venv\Scripts\python.exe -m pip install -e .[dev]
    pause
    exit /b 1
)

rem The version has a single source: __version__ in src\n5terminal\__init__.py.
set VERSION=
for /f "delims=" %%v in ('.venv\Scripts\python.exe -c "import n5terminal; print(n5terminal.__version__)"') do set VERSION=%%v
if "%VERSION%"=="" (
    echo The version of MiTerm-N5 could not be read.
    pause
    exit /b 1
)
echo Building MiTerm-N5 %VERSION%

if exist "Dist" rmdir /s /q "Dist"
if exist "build" rmdir /s /q "build"

.venv\Scripts\python.exe -m PyInstaller packaging\n5terminal.spec --noconfirm --clean --distpath Dist --workpath build
if errorlevel 1 (
    echo PyInstaller failed.
    pause
    exit /b 1
)

rem The askpass program lives in _internal, with the libraries it shares with the application.
move /y "Dist\MiTerm-N5\MiTerm-N5-askpass.exe" "Dist\MiTerm-N5\_internal\" >nul
if errorlevel 1 (
    echo MiTerm-N5-askpass.exe could not be moved into _internal.
    pause
    exit /b 1
)

rem What the application looks for next to the executable (see specs\packaging.md); the starter
rem profiles are in _internal\StartProfil, put there by the spec.
xcopy "Help" "Dist\MiTerm-N5\Help\" /e /i /y /q >nul
if errorlevel 1 goto copy_failed
xcopy "licenses" "Dist\MiTerm-N5\licenses\" /e /i /y /q >nul
if errorlevel 1 goto copy_failed
copy /y "THIRD-PARTY-NOTICES.md" "Dist\MiTerm-N5\" >nul
if errorlevel 1 goto copy_failed

powershell -NoProfile -Command "Compress-Archive -Path 'Dist\MiTerm-N5' -DestinationPath 'Dist\MiTerm-N5-%VERSION%.zip' -Force"
if errorlevel 1 (
    echo The zip file could not be made.
    pause
    exit /b 1
)

echo.
echo Folder: Dist\MiTerm-N5
echo Zip:    Dist\MiTerm-N5-%VERSION%.zip
exit /b 0

:copy_failed
echo The Help folder, the licenses or the notices could not be copied.
pause
exit /b 1
