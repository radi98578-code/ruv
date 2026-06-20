@echo off
setlocal
cd /d "%~dp0\.."

if not exist "data\models" mkdir "data\models"

if exist "data\models\wifi-densepose.rvf" (
  echo [model] data\models\wifi-densepose.rvf already exists
  echo         (starter RVF container; for calibrated weights run training later)
  goto :eof
)

if not exist "v2\target\release\sensing-server.exe" (
  echo [error] Build sensing-server first: cd v2 ^&^& cargo build -p wifi-densepose-sensing-server --release
  exit /b 1
)

echo [model] Exporting WiFi DensePose RVF container...
cd v2
target\release\sensing-server.exe --export-rvf ..\data\models\wifi-densepose.rvf
set ERR=%ERRORLEVEL%
cd ..

if %ERR% neq 0 (
  echo [error] Model export failed with code %ERR%
  exit /b %ERR%
)

if exist "data\models\wifi-densepose.rvf" (
  echo [model] Saved data\models\wifi-densepose.rvf
) else (
  echo [error] Expected output file was not created
  exit /b 1
)
