@echo off
setlocal

REM ===== CONFIG =====
set IMAGE_NAME=anaf-validator
set CONTAINER_NAME=anaf-validator-container
set PORT=8000

echo.
echo 🔨 Building Docker image...
docker build -t %IMAGE_NAME% .

if %ERRORLEVEL% neq 0 (
    echo ❌ Build failed
    exit /b %ERRORLEVEL%
)

echo.
echo 🧹 Removing old container (if exists)...
docker rm -f %CONTAINER_NAME% >nul 2>&1

echo.
echo 🚀 Running container...
docker run -d ^
  --name %CONTAINER_NAME% ^
  -p %PORT%:%PORT% ^
  %IMAGE_NAME%

if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to start container
    exit /b %ERRORLEVEL%
)

echo.
echo ✅ Container started!
echo 🌐 http://localhost:%PORT%

endlocal
pause