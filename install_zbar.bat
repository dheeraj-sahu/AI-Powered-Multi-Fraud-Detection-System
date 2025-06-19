@echo off
setlocal

echo === ZBar DLL Installer for pyzbar ===

:: Step 1: Define paths
set "DOWNLOAD_URL=https://github.com/NaturalHistoryMuseum/pyzbar/releases/download/0.1.8/libzbar-32.dll"
set "DLL_NAME=libzbar-64.dll"
set "DEST_DIR=%~dp0myenv\Lib\site-packages\pyzbar"

:: Step 2: Download libzbar-64.dll
echo Downloading %DLL_NAME%...
curl -L -o "%DLL_NAME%" %DOWNLOAD_URL%

if not exist "%DLL_NAME%" (
    echo ❌ Download failed.
    pause
    exit /b 1
)

:: Step 3: Move to pyzbar folder
if exist "%DEST_DIR%" (
    echo Moving %DLL_NAME% to %DEST_DIR%...
    move /Y "%DLL_NAME%" "%DEST_DIR%\%DLL_NAME%"
) else (
    echo ❌ pyzbar directory not found. Check your virtual environment path.
    pause
    exit /b 1
)

:: Step 4: Done
echo ✅ ZBar DLL installed successfully!
pause
endlocal
