@echo off
setlocal

set "ROOT_DIR=%~dp0.."
if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8080"
set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  py -3 -m consensus_web --host "%HOST%" --port "%PORT%" %*
) else (
  python -m consensus_web --host "%HOST%" --port "%PORT%" %*
)
