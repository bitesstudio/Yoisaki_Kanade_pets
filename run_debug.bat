@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== 宵崎奏 桌宠 · 诊断启动 =====
echo 如果窗口没有出现，请把下面的信息截图反馈。
echo.

if exist "%~dp0runtime\python.exe" (
    "%~dp0runtime\python.exe" "%~dp0pet.py"
) else (
    python "%~dp0pet.py"
)

echo.
echo ===== 已退出 =====
pause
