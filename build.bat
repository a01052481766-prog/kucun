@echo off
chcp 65001 >nul
echo ========================================
echo   仓库管理系统  打包脚本
echo ========================================
echo.

echo [1/2] 安装 PyInstaller...
venv\Scripts\pip install pyinstaller -q
if errorlevel 1 (
    echo 错误：pip install 失败
    pause & exit /b 1
)

echo [2/2] 开始打包（约 1-2 分钟）...
venv\Scripts\pyinstaller ^
  --onedir ^
  --name "仓库管理系统" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --hidden-import flask_login ^
  --hidden-import flask_sqlalchemy ^
  --hidden-import sqlalchemy.dialects.sqlite ^
  --hidden-import sqlalchemy.pool ^
  --collect-all flask_login ^
  --noconfirm ^
  main.py

if errorlevel 1 (
    echo.
    echo 打包失败，请查看上方错误信息
    pause & exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo   文件位置: dist\仓库管理系统\
echo   把整个文件夹压缩发给同事即可
echo ========================================
pause
