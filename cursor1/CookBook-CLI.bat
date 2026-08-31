@echo off
setlocal EnableDelayedExpansion
title CookBook CLI
cd /d "%~dp0"

if not exist ".env" (
    echo .env not found. Run CookBook-Setup.bat first.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Start Docker Desktop first.
    pause
    exit /b 1
)

REM Load GPU flag from .env
set "COMPOSE_FILES=-f docker-compose.phase0.yml"
findstr /i "WHISPER_DEVICE=cuda" .env >nul && set "COMPOSE_FILES=!COMPOSE_FILES! -f docker-compose.gpu.yml"

:Menu
cls
echo.
echo ============================================================
echo   CookBook CLI
echo ============================================================
echo   1) Download videos from URL list
echo   2) Fetch metadata only (no re-download)
echo   3) Transcribe downloaded videos (Whisper)
echo   4) Run tests
echo   5) Stack status (full compose)
echo   6) Exit
echo.
set /p "CHOICE=Select [1-6]: "

if "!CHOICE!"=="1" goto :Download
if "!CHOICE!"=="2" goto :Metadata
if "!CHOICE!"=="3" goto :Transcribe
if "!CHOICE!"=="4" goto :Test
if "!CHOICE!"=="5" goto :Status
if "!CHOICE!"=="6" exit /b 0
goto :Menu

:Download
set /p "URLFILE=Container path to URL list [/data/dataset/urls.example.txt]: "
if "!URLFILE!"=="" set "URLFILE=/data/dataset/urls.example.txt"
set /p "LIMIT=Max URLs [50]: "
if "!LIMIT!"=="" set "LIMIT=50"
docker compose !COMPOSE_FILES! run --rm -e MODE=download cookbook --urls-file "!URLFILE!" --limit !LIMIT!
pause
goto :Menu

:Metadata
docker compose !COMPOSE_FILES! run --rm -e MODE=download cookbook --urls-file /data/dataset/urls.example.txt --metadata-only --limit 50
pause
goto :Menu

:Transcribe
echo Starting Whisper transcription (may take several minutes^)...
docker compose !COMPOSE_FILES! run --rm -e MODE=transcribe cookbook
pause
goto :Menu

:Test
docker compose -f docker-compose.test.yml run --rm cookbook
pause
goto :Menu

:Status
set "FULL=-f docker-compose.yml"
findstr /i "WHISPER_DEVICE=cuda" .env >nul && set "FULL=!FULL! -f docker-compose.gpu.yml"
docker compose !FULL! ps
pause
goto :Menu
