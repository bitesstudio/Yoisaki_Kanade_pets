@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist "%~dp0runtime\pythonw.exe" (
    start "" "%~dp0runtime\pythonw.exe" "%~dp0pet.py"
    exit /b
)

where pythonw >nul 2>nul
if errorlevel 1 (
    start "" python "%~dp0pet.py"
) else (
    start "" pythonw "%~dp0pet.py"
)
