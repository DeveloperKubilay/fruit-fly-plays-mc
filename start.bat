@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" goto VENV_OK
echo [HATA / ERROR] venv bulunamadi! Lutfen once setup.bat calistirin.
echo.
pause
exit /b 1

:VENV_OK
call "venv\Scripts\activate.bat"

rem 1. Varsa config.json dosyasindan ayarlari oku
set "CFG_HOST="
set "CFG_PORT=8765"
set "CFG_PASS="

if exist "config.json" (
    for /f "tokens=1,2 delims=:, " %%a in ('findstr /i "minecraft_host auth_token minecraft_port password" "config.json" 2^>nul') do (
        if /i "%%~a"=="minecraft_host" set "CFG_HOST=%%~b"
        if /i "%%~a"=="auth_token" set "CFG_PASS=%%~b"
        if /i "%%~a"=="password" if not defined CFG_PASS set "CFG_PASS=%%~b"
        if /i "%%~a"=="minecraft_port" set "CFG_PORT=%%~b"
    )
)

rem 2. Varsa .env dosyasindan ayarlari oku
if exist ".env" (
    for /f "usebackq tokens=1* delims==" %%a in (".env") do (
        if /i "%%a"=="MINECRAFT_HOST" if not defined CFG_HOST set "CFG_HOST=%%~b"
        if /i "%%a"=="MINECRAFT_PORT" set "CFG_PORT=%%~b"
        if /i "%%a"=="MINECRAFT_PASSWORD" if not defined CFG_PASS set "CFG_PASS=%%~b"
        if /i "%%a"=="FLY_AUTH_TOKEN" if not defined CFG_PASS set "CFG_PASS=%%~b"
        if /i "%%a"=="PASSWORD" if not defined CFG_PASS set "CFG_PASS=%%~b"
        if /i "%%a"=="AUTH_TOKEN" if not defined CFG_PASS set "CFG_PASS=%%~b"
        if /i "%%a"=="FLY_PASSWORD" if not defined CFG_PASS set "CFG_PASS=%%~b"
    )
)

rem 3. Komut satiri parametrelerini ayristir: [IP veya IP:PORT] [PASSWORD] [--no-gui]
set "ARG_HOST="
set "ARG_PASS="
set "NO_GUI="

for %%a in (%*) do (
    if /i "%%~a"=="--no-gui" (
        set "NO_GUI=--no-gui"
    ) else if /i "%%~a"=="--nogui" (
        set "NO_GUI=--no-gui"
    ) else if /i "%%~a"=="--headless" (
        set "NO_GUI=--no-gui"
    ) else if not defined ARG_HOST (
        set "ARG_HOST=%%~a"
    ) else if not defined ARG_PASS (
        set "ARG_PASS=%%~a"
    )
)

rem Hedef Sunucu: Arguman > config.json / .env > localhost
set "TARGET_HOST=%ARG_HOST%"
if not defined TARGET_HOST set "TARGET_HOST=%CFG_HOST%"
if not defined TARGET_HOST set "TARGET_HOST=%MINECRAFT_HOST%"
if not defined TARGET_HOST set "TARGET_HOST=%TARGET%"
if not defined TARGET_HOST set "TARGET_HOST=localhost"

rem IP:Port ayristirma destegi
for /f "tokens=1,2 delims=:" %%a in ("%TARGET_HOST%") do (
    set "TARGET_HOST=%%a"
    if not "%%b"=="" set "CFG_PORT=%%b"
)

rem Guvenlik Sifresi: Arguman > config.json / .env > FLY_AUTH_TOKEN > Kullaniciya sor
set "TARGET_PASS=%ARG_PASS%"
if not defined TARGET_PASS set "TARGET_PASS=%CFG_PASS%"
if not defined TARGET_PASS set "TARGET_PASS=%FLY_AUTH_TOKEN%"

if defined TARGET_PASS (
    if not "%TARGET_PASS%"=="" goto PASS_READY
)

:PROMPT_PASSWORD
echo ================================================================
echo   GUVENLIK SIFRESI GEREKLI / PASSWORD REQUIRED
echo ================================================================
echo Minecraft sunucusuyla baglanti icin sifre (token) gereklidir.
echo (Minecraft sunucunuzdaki plugins/FruitFly/config.yml dosyasindaki
echo  brain.auth-token degeri ile birebir ayni olmalidir)
echo.
set /p "TARGET_PASS=Sifre / Token: "
if not defined TARGET_PASS goto PROMPT_PASSWORD
if "%TARGET_PASS%"=="" goto PROMPT_PASSWORD
echo.

:PASS_READY
set "FLY_AUTH_TOKEN=%TARGET_PASS%"
set "MINECRAFT_PASSWORD=%TARGET_PASS%"

echo ================================================================
echo   Hedef Minecraft Sunucusu: ws://%TARGET_HOST%:%CFG_PORT%
if defined NO_GUI (
    echo   Arayuz: Sadece Terminal Modu (--no-gui)
) else (
    echo   Arayuz: Grafik Dashboard (Pygame)
)
echo ================================================================

python run_real.py %TARGET_HOST%:%CFG_PORT% --token %TARGET_PASS% %NO_GUI% --sessiz
if %ERRORLEVEL% equ 0 goto DONE
echo.
pause

:DONE
