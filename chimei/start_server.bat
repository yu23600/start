@echo off
chcp 65001 >nul
echo ============================================================
echo 🚀 智能食堂云端服务器 - 快速启动
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到Python,请先安装Python 3.7+
    pause
    exit /b 1
)

echo ✅ Python已安装
echo.

REM 检查依赖是否安装
echo 📦 检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo ⏳ 正在安装依赖...
    pip install -r requirements_server.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ 依赖安装成功
) else (
    echo ✅ 依赖已安装
)

echo.
echo ============================================================
echo 📡 正在启动服务器...
echo ============================================================
echo.
echo 💡 提示:
echo   - 服务器地址: http://localhost:5000
echo   - API文档: http://localhost:5000/
echo   - 按 Ctrl+C 停止服务器
echo.
echo ============================================================
echo.

REM 启动服务器
python app_server.py

pause
