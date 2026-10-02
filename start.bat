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

rem .env dosyası varsa ortam değişkenlerini yükle
if exist ".env" (
    for /f "usebackq tokens=1* delims==" %%a in (".env") do (
        set "%%a=%%b"
    )
)

rem Hedef Minecraft sunucu adresi (Varsayılan: localhost)
rem Sıralama: 1. Komut satırı argümanı (%*) -> 2. MINECRAFT_HOST / TARGET env -> 3. localhost
set "SERVER_HOST=%*"
if defined SERVER_HOST goto RUN_APP
if defined MINECRAFT_HOST (
    set "SERVER_HOST=%MINECRAFT_HOST%"
    goto RUN_APP
)
if defined TARGET (
    set "SERVER_HOST=%TARGET%"
    goto RUN_APP
)
if defined SERVER_HOST_ENV (
    set "SERVER_HOST=%SERVER_HOST_ENV%"
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
