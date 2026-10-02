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
goto FINISH_SETUP

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

:FINISH_SETUP
echo.
echo ================================================================
echo   KURULUM TAMAMLANDI / SETUP COMPLETED!
echo   Çalıştırmak için / To run:
echo     start.bat              (Aynı makinedeki Minecraft için / Localhost)
echo     start.bat 1.2.3.4      (Minecraft başka IP'deyse / Remote host)
echo ================================================================
echo.
pause
