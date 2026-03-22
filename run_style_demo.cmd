@echo off
chcp 65001 >nul
echo ========================================
echo   IPythonQTBot - 样式演示程序
echo ========================================
echo.
echo 正在启动样式演示程序...
echo.
python app_qt\examples\style_demo.py
if errorlevel 1 (
    echo.
    echo ❌ 程序运行失败！
    echo 请确保已安装以下依赖:
    echo   pip install PySide6
    echo.
    pause
) else (
    echo.
    echo ✅ 程序已退出
    echo.
    pause
)
