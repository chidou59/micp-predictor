@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

"%PYTHON_EXE%" -c "import customtkinter, sklearn, joblib, pandas, numpy, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Missing dependencies. Please run install_deps.bat first.
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" app.py
if errorlevel 1 pause
