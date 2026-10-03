@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ================================================================
echo   Drosophila - Meyve Sinegi Beyin Simulasyonu Kurulumu
echo   MaleCNS v1.0 Connectome Simulation Setup
echo ================================================================
echo.

rem 1. Python Kontrolu
set "PYTHON_EXE="
where python >nul 2>nul
if %ERRORLEVEL% equ 0 set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 set "PYTHON_EXE=py"
)

if defined PYTHON_EXE goto PYTHON_OK
echo [HATA / ERROR] Python bulunamadi!
echo Lutfen Python 3.10 veya daha yeni bir surum kurun: https://www.python.org/downloads/
echo Kurulum sirasinda "Add Python to PATH" secenegini isaretlemeyi unutmayin!
echo.
pause
exit /b 1

:PYTHON_OK
for /f "tokens=2" %%v in ('%PYTHON_EXE% --version 2^>nul') do set "PY_VER=%%v"
echo [OK] Python surumu: %PY_VER%
echo.

rem 2. Virtual Environment (venv) Kurulumu
if exist "venv\Scripts\activate.bat" goto VENV_EXISTS
echo [1/3] Python sanal ortami (venv) olusturuluyor...
%PYTHON_EXE% -m venv venv
if %ERRORLEVEL% equ 0 goto VENV_CREATED
echo [HATA / ERROR] Sanal ortam olusturulamadi!
echo.
pause
exit /b 1

:VENV_CREATED
echo [OK] venv basariyla olusturuldu.
goto VENV_DONE

:VENV_EXISTS
echo [OK] venv zaten mevcut.

:VENV_DONE
echo.

rem 3. Bagimliliklarin Kurulumu
echo [2/3] Bagimliliklar yukleniyor (requirements.txt)...
echo Lutfen bekleyin, bu islem 1-2 dakika surebilir...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% equ 0 goto REQ_OK
echo [HATA / ERROR] Bagimliliklar yuklenirken hata olustu!
echo.
pause
exit /b 1

:REQ_OK
echo [OK] Bagimliliklar basariyla yuklendi.
echo.

rem 4. Model / Konektom Verisi Kontrolu
echo [3/3] Konektom modeli kontrol ediliyor...
if not exist "connectome" mkdir "connectome"

set "GRAPH_FILE=connectome\malecns_behavior.W.npz"

if not exist "%GRAPH_FILE%" goto DOWNLOAD_CONNECTOME
echo [OK] Hazir davranis grafigi bulundu (19 MB). Ek indirme gerekmez!
goto CONFIGURE_CONNECTION

:DOWNLOAD_CONNECTOME
echo [BILGI] Davranis alt-grafigi bulunamadi. Ham konektom verisi (~1.1 GB) indirilecek...
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

echo   -^> Davranis alt-grafigi derleniyor (1-2 dakika surer)...
"venv\Scripts\python.exe" connectome_loader.py
if %ERRORLEVEL% equ 0 goto COMPILE_OK
echo [HATA / ERROR] Davranis grafigi derlenirken hata olustu!
echo.
pause
exit /b 1

:COMPILE_OK
echo [OK] Davranis grafigi basariyla derlendi!

:CONFIGURE_CONNECTION
"venv\Scripts\python.exe" run_real.py --setup

:FINISH_SETUP
echo.
echo ================================================================
echo   KURULUM TAMAMLANDI / SETUP COMPLETED!
echo   Calistirma Secenekleri / Run Options:
echo.
echo   1. Kayitli Ayarlarla Baslatma (Grafik Arayuz / GUI):
echo      start.bat
echo.
echo   2. Sadece Terminal Modu (GUI Yok, Dusuk Kaynak Kullanimi):
echo      start.bat --no-gui
echo.
echo   3. Ozel IP veya IP:Port ve Sifre ile Baslatma:
echo      start.bat 1.2.3.4
echo      start.bat 1.2.3.4:8765
echo      start.bat 1.2.3.4:8765 mypassword
echo      start.bat 1.2.3.4:8765 mypassword --no-gui
echo ================================================================
echo.
pause
