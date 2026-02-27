@echo off
:: setup.bat - Downloads ffmpeg and ffprobe for Windows
:: Uses PowerShell to download and extract binaries

echo.
echo  Audiobook Splitter Setup
echo.

:: Check for Python
echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python not found.
    echo  Please install Python 3 from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo [OK] Python found

:: Check for PowerShell (needed for downloads)
powershell -Command "exit" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: PowerShell not found. Cannot download ffmpeg.
    echo  Please install ffmpeg manually from https://ffmpeg.org/download.html
    echo.
    pause
    exit /b 1
)

:: Download ffmpeg if not already present
if exist ffmpeg.exe (
    echo [OK] ffmpeg.exe already exists, skipping
) else (
    echo Downloading ffmpeg...
    powershell -Command "& { Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg_download.zip' -UseBasicParsing }"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to download ffmpeg. Check your internet connection.
        pause
        exit /b 1
    )

    echo Extracting ffmpeg...
    powershell -Command "& { Expand-Archive -Path 'ffmpeg_download.zip' -DestinationPath 'ffmpeg_temp' -Force }"
    
    :: Find and copy the executables from the nested folder structure
    powershell -Command "& { $exe = Get-ChildItem -Path 'ffmpeg_temp' -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1; Copy-Item $exe.FullName -Destination '.' }"
    powershell -Command "& { $exe = Get-ChildItem -Path 'ffmpeg_temp' -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1; Copy-Item $exe.FullName -Destination '.' }"

    :: Clean up
    rmdir /s /q ffmpeg_temp
    del ffmpeg_download.zip

    echo [OK] ffmpeg downloaded
)

:: Verify the executables exist
if not exist ffmpeg.exe (
    echo ERROR: ffmpeg.exe not found after extraction.
    pause
    exit /b 1
)

if not exist ffprobe.exe (
    echo ERROR: ffprobe.exe not found after extraction.
    pause
    exit /b 1
)

echo.
echo  Setup complete!
echo.
echo  Run the splitter with:
echo    python standalone_wrapper.py --input your_audiobook.m4b --ffmpeg-path .\ffmpeg.exe --ffprobe-path .\ffprobe.exe
echo.
echo  Or launch the GUI:
echo    python audiobook_splitter_gui.py
echo.
pause
