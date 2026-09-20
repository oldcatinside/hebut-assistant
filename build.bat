@echo off
setlocal
set TALK_DEBUG_CONSOLE=
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -m venv .venv
if errorlevel 1 goto fail
goto install
:usepython
python -m venv .venv
if errorlevel 1 goto fail
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean talk_assistant.spec
if errorlevel 1 goto fail
echo Build complete. The EXE is in the dist folder.
pause
exit /b 0
:fail
echo Build failed. See the error above. Python 3.11+ is required.
pause
exit /b 1
