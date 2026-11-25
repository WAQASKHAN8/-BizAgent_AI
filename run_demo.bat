@echo off
TITLE BizAgent AI - Master 15-Step End-to-End Demo
COLOR 0A
echo ======================================================================
echo    BizAgent AI - Master 15-Step End-to-End Demonstration (Ali Khan)
echo    Team 3 (Dawley Institute of Technology)
echo ======================================================================
echo.

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

%PYTHON_EXE% demo_runner.py ali_khan

echo.
pause
