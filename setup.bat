@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo   Drosophila — Meyve Sineği Beyin Simülasyonu Kurulumu
echo   MaleCNS v1.0 Connectome Simulation Setup
echo ================================================================
echo.

rem 1. Python kontrolü
set "PYTHON_EXE="
where python >nul 2>nul
if %ERRORLEVEL% equ 0 set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 set "PYTHON_EXE=py"
)

if defined PYTHON_EXE goto PYTHON_OK
echo [HATA / ERROR] Python bulunamadı!
echo Lütfen Python 3.10 veya daha yeni bir sürüm kurun: https://www.python.org/downloads/
echo Kurulum sırasında "Add Python to PATH" seçeneğini işaretlemeyi unutmayın!
echo.
pause
exit /b 1

:PYTHON_OK
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do set "PY_VER=%%v"
echo [OK] Python sürümü: %PY_VER%
echo.

rem 2. Virtual Environment (venv) Kurulumu
if exist "venv\Scripts\activate.bat" goto VENV_EXISTS
echo [1/3] Python sanal ortamı (venv) oluşturuluyor...
%PYTHON_EXE% -m venv venv
if %ERRORLEVEL% equ 0 goto VENV_CREATED
echo [HATA / ERROR] Sanal ortam oluşturulamadı!
echo.
pause
exit /b 1

:VENV_CREATED
echo [OK] venv başarıyla oluşturuldu.
goto VENV_DONE

:VENV_EXISTS
echo [OK] venv zaten mevcut.

:VENV_DONE
echo.

rem 3. Bağımlılıkların Kurulumu
echo [2/3] Bağımlılıklar yükleniyor (requirements.txt)...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% equ 0 goto REQ_OK
echo [HATA / ERROR] Bağımlılıklar yüklenirken hata oluştu!
echo.
pause
exit /b 1

:REQ_OK
echo [OK] Bağımlılıklar başarıyla yüklendi.
echo.

rem 4. Model / Konektom Verisi Kontrolü
echo [3/3] Konektom modeli kontrol ediliyor...
if not exist "connectome" mkdir "connectome"

set "GRAPH_FILE=connectome\malecns_behavior.W.npz"

if not exist "%GRAPH_FILE%" goto DOWNLOAD_CONNECTOME
echo [OK] Hazır davranış grafiği bulundu (19 MB). Ek indirme gerekmez!
goto CONFIGURE_CONNECTION

:DOWNLOAD_CONNECTOME
echo [BİLGİ] Davranış alt-grafiği bulunamadı. Ham konektom verisi (~1.1 GB) indirilecek...
set "BASE_URL=https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"

if exist "connectome\weights.feather" goto SKIP_WEIGHTS
echo   -^> weights.feather (~1 GB) indiriliyor...
curl -L -o "connectome\weights.feather" "%BASE_URL%/connectome-weights-male-cns-v1.0-minconf-0.5.feather"
:SKIP_WEIGHTS

if exist "connectome\annotations.feather" goto SKIP_ANNOTATIONS
echo   -^> annotations.feather (~14 MB) indiriliyor...
curl -L -o "connectome\annotations.feather" "%BASE_URL%/body-annotations-male-cns-v1.0-minconf-0.5.feather"
:SKIP_ANNOTATIONS

if exist "connectome\neurotransmitters.feather" goto SKIP_NT
echo   -^> neurotransmitters.feather (~41 MB) indiriliyor...
curl -L -o "connectome\neurotransmitters.feather" "%BASE_URL%/body-neurotransmitters-male-cns-v1.0.feather"
:SKIP_NT

echo   -^> Davranış alt-grafiği derleniyor (1-2 dakika sürer)...
python connectome_loader.py
if %ERRORLEVEL% equ 0 goto COMPILE_OK
echo [HATA / ERROR] Davranış grafiği derlenirken hata oluştu!
echo.
pause
exit /b 1

:COMPILE_OK
echo [OK] Davranış grafiği başarıyla derlendi!

:CONFIGURE_CONNECTION
echo.
echo ================================================================
echo   [4/4] BAĞLANTI VE GÜVENLİK AYARLARI / CONFIGURATION
echo ================================================================
echo.
echo Minecraft Sunucu Adresi (IP veya IP:Port):
echo   - Başka bir sunucuya bağlamak istiyorsanız IP veya IP:Port yazın (örn: 1.2.3.4 veya 1.2.3.4:8765).
echo   - Aynı makinedeki sunucu için doğrudan [ENTER]'a basın (localhost).
set "INPUT_HOST="
set /p "INPUT_HOST=Sunucu IP [localhost]: "
if not defined INPUT_HOST set "INPUT_HOST=localhost"
if "%INPUT_HOST%"=="" set "INPUT_HOST=localhost"

rem IP:Port ayrıştırma desteği
set "INPUT_PORT=8765"
echo %INPUT_HOST% | findstr ":" >nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1,2 delims=:" %%h in ("%INPUT_HOST%") do (
        set "INPUT_HOST=%%~h"
        if not "%%~i"=="" set "INPUT_PORT=%%~i"
    )
)

:ASK_PASSWORD
echo.
echo Minecraft Güvenlik Şifresi / Token (ZORUNLU):
echo (Minecraft sunucusundaki plugins/DrosophilaBee/config.yml dosyasındaki
echo  brain.auth-token değeri ile birebir aynı olmalıdır)
set "INPUT_PASS="
set /p "INPUT_PASS=Şifre / Token: "
if not defined INPUT_PASS goto PASS_REQUIRED
if "%INPUT_PASS%"=="" goto PASS_REQUIRED
goto SAVE_CONFIG

:PASS_REQUIRED
echo.
echo [UYARI / WARNING] Şifre zorunludur, boş bırakılamaz!
goto ASK_PASSWORD

:SAVE_CONFIG
echo.
echo [BİLGİ] Ayarlar config.json ve .env dosyalarına kaydediliyor...

rem config.json dosyasına JSON formatında yaz
(
  echo {
  echo   "minecraft_host": "%INPUT_HOST%",
  echo   "minecraft_port": %INPUT_PORT%,
  echo   "auth_token": "%INPUT_PASS%"
  echo }
) > "config.json"

rem .env dosyasına yaz
(
  echo # Drosophila Otomatik Yapılandırma
  echo MINECRAFT_HOST=%INPUT_HOST%
  echo MINECRAFT_PORT=%INPUT_PORT%
  echo MINECRAFT_PASSWORD=%INPUT_PASS%
  echo FLY_AUTH_TOKEN=%INPUT_PASS%
) > ".env"

echo [OK] Yapılandırma başarıyla kaydedildi! (config.json, .env)

:FINISH_SETUP
echo.
echo ================================================================
echo   KURULUM TAMAMLANDI / SETUP COMPLETED!
echo   Çalıştırma Seçenekleri / Run Options:
echo.
echo   1. Kayıtlı Ayarlarla Başlatma (Grafik Arayüz / GUI):
echo      start.bat
echo.
echo   2. Sadece Terminal Modu (GUI Yok, Düşük Kaynak Kullanımı):
echo      start.bat --no-gui
echo.
echo   3. Özel IP veya IP:Port ve Şifre ile Başlatma:
echo      start.bat 1.2.3.4
echo      start.bat 1.2.3.4:8765
echo      start.bat 1.2.3.4:8765 mypassword
echo      start.bat 1.2.3.4:8765 mypassword --no-gui
echo ================================================================
echo.
pause
