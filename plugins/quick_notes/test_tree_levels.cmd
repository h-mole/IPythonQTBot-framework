@echo off
chcp 65001 >nul
echo ============================================================
echo 笔记树无限层级功能测试
echo ============================================================
echo.
echo 正在启动测试...
echo.

python plugins/quick_notes/test_tree_levels.py

pause
