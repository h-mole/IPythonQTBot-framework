@echo off
chcp 65001 >nul
echo ================================================
echo    Markdown 渲染功能测试
echo ================================================
echo.
echo 正在启动演示程序...
echo.

python plugins\text_helper\demo_markdown.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo    运行失败！
    echo ================================================
    echo.
    echo 可能的原因:
    echo 1. 未安装 PySide6
    echo 2. 未安装 QMarkdownView
    echo.
    echo 请运行以下命令安装依赖:
    echo   pip install qmarkdownview
    echo.
)

pause
