@echo off
chcp 65001 >nul
echo ========================================
echo   MyAgent 一键安装
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 创建虚拟环境
echo [1/3] 创建虚拟环境...
if exist .venv (
    echo 虚拟环境已存在，跳过
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: 安装依赖
echo [2/3] 安装依赖...
.venv\Scripts\pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 完成
echo [3/3] 完成！
echo.
echo ========================================
echo   安装完成！双击 run.bat 开始使用
echo   或者命令行运行:
echo   .venv\Scripts\python.exe v6_agent.py
echo ========================================
pause
