@echo off
TITLE BizAgent AI - Multi-Agent Intelligent Business System
COLOR 0B
echo ======================================================================
echo    Starting BizAgent AI - Multi-Agent Intelligent Business System
echo    Team 3 (Dawley Institute of Technology)
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    echo [OK] Using project virtual environment (venv)...
    set "STREAMLIT_EXE=venv\Scripts\streamlit.exe"
) else if exist ".venv\Scripts\python.exe" (
    echo [OK] Using project virtual environment (.venv)...
    set "STREAMLIT_EXE=.venv\Scripts\streamlit.exe"
) else (
    echo [INFO] Virtual environment not detected. Using system Python...
    set "STREAMLIT_EXE=streamlit"
)

echo.
echo Launching Interactive Web Dashboard on http://localhost:8501 ...
echo.

%STREAMLIT_EXE% run app.py

pause
