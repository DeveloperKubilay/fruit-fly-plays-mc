@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" goto VENV_OK
echo [HATA / ERROR] venv bulunamadı! Lütfen önce setup.bat çalıştırın.
echo.
pause
exit /b 1

:VENV_OK
call "venv\Scripts\activate.bat"

rem Hedef Minecraft sunucu IP adresi (Parametre yoksa varsayılan: localhost)
rem Kullanım / Usage:
rem   start.bat                     -> Yerel sunucu (localhost:8765)
rem   start.bat 192.168.1.105       -> Uzak sunucu IP'si
rem   start.bat 192.168.1.105:8766  -> Özel port
set "SERVER_HOST=%*"
if defined SERVER_HOST goto RUN_APP
if defined TARGET (
    set "SERVER_HOST=%TARGET%"
    goto RUN_APP
)
set "SERVER_HOST=localhost"

:RUN_APP
echo ================================================================
echo   Hedef Minecraft Sunucusu: ws://%SERVER_HOST%
echo ================================================================
python run_real.py --sessiz %SERVER_HOST%
if %ERRORLEVEL% equ 0 goto DONE
echo.
pause

:DONE
