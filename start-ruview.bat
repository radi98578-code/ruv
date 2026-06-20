@echo off
setlocal EnableDelayedExpansion

echo Uruchamianie RuView CSI Stack...
cd /d "%~dp0"

rem ESP32 target port (provision with: provision.py --target-port 5555)
rem Port 5005 is the firmware default but is often taken by wmpnetwk on Windows.
set CSI_PORT=5555
set RECORDER_PORT=5006
set SNN_PORT=5007
set RFSCAN_PORT=5008

if not exist "data\recordings" mkdir "data\recordings"

set FANOUT_PORTS=%RECORDER_PORT%,%RFSCAN_PORT%

call :ensure_port %RECORDER_PORT% "CSI Recorder" python scripts\record-csi-udp.py --port %RECORDER_PORT% --duration 86400 --output data\recordings

call :ensure_port 7878 "CSI Bridge" python scripts\csi-ws-bridge.py

call scripts\setup-densepose-model.bat
call :start_sensing_server

call :try_snn

call :ensure_port %RFSCAN_PORT% "RF Scan" node scripts\rf-scan.js --port %RFSCAN_PORT%

call :ensure_port 5173 "Dashboard" cmd /c "cd /d dashboard && npm run dev"

call :ensure_udp %CSI_PORT% "UDP Fanout" python scripts\udp-fanout.py --listen-port %CSI_PORT% --forward-ports %FANOUT_PORTS%

echo.
echo Gotowe!
echo   Dashboard:      http://localhost:5173
echo   Pose UI:        http://localhost:8080/ui/pose-fusion.html
echo   Sensing API:    http://localhost:8080/health
echo   Model info:     http://localhost:8080/api/v1/model/info
echo   CSI bridge:     http://localhost:7878  (WS: /ws/stream)
echo   ESP32 -^> UDP:  %CSI_PORT%  fanout -^> %FANOUT_PORTS%
echo.
echo   Uwaga: port 5005 jest czesto zajety przez Windows Media Player (wmpnetwk).
echo   ESP32 musi wysylac na port %CSI_PORT% (provision.py --target-port %CSI_PORT%).
echo.
pause
goto :eof

rem Start sensing-server; load RVF model when data\models\wifi-densepose.rvf exists.
:start_sensing_server
set "SENSING_ARGS=--ui-path ..\ui"
if exist "data\models\wifi-densepose.rvf" (
  set "SENSING_ARGS=--model ..\data\models\wifi-densepose.rvf --load-rvf ..\data\models\wifi-densepose.rvf --progressive --ui-path ..\ui"
  echo [model] DensePose RVF: data\models\wifi-densepose.rvf
) else (
  echo [model] Brak RVF - uruchom scripts\setup-densepose-model.bat
)
call :ensure_port 8080 "Sensing Server" cmd /c "cd /d v2 && set MODELS_DIR=..\data\models&& target\release\sensing-server.exe %SENSING_ARGS%"
goto :eof

rem Start SNN only when @ruvector/spiking-neural is available.
:try_snn
node -e "try{require('@ruvector/spiking-neural');process.exit(0)}catch(e){process.exit(1)}" >nul 2>&1
if errorlevel 1 (
  echo [skip] SNN Processor - brak @ruvector/spiking-neural (opcjonalny)
  goto :eof
)
set FANOUT_PORTS=%FANOUT_PORTS%,%SNN_PORT%
call :ensure_port %SNN_PORT% "SNN Processor" node scripts\snn-csi-processor.js --port %SNN_PORT%
goto :eof

rem Skip if TCP port already listening; otherwise start in a new window.
:ensure_port
set "_PORT=%~1"
set "_TITLE=%~2"
shift
shift
netstat -an | findstr /R /C:":%_PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [skip] %_TITLE% - port %_PORT% already in use
  goto :eof
)
echo [start] %_TITLE% - port %_PORT%
start "%_TITLE%" %*
goto :eof

rem Skip if UDP port already bound; otherwise start in a new window.
:ensure_udp
set "_PORT=%~1"
set "_TITLE=%~2"
shift
shift
netstat -an | findstr /R /C:"UDP .*:%_PORT% " >nul 2>&1
if not errorlevel 1 (
  echo [skip] %_TITLE% - UDP %_PORT% already in use
  goto :eof
)
echo [start] %_TITLE% - UDP %_PORT%
start "%_TITLE%" %*
goto :eof
