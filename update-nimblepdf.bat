@echo off
setlocal

cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
    echo Git was not found. Install Git, then run this file again.
    pause
    exit /b 1
)

git rev-parse --show-toplevel >nul 2>nul
if errorlevel 1 (
    echo This folder is not a Git repository.
    echo Run the initial Git setup before using this updater.
    pause
    exit /b 1
)

echo Checking for changes...
git status --short
if errorlevel 1 (
    echo Unable to read the Git status.
    pause
    exit /b 1
)

for /f "delims=" %%A in ('git status --porcelain') do set "has_changes=1"
if not defined has_changes (
    echo No changes to upload.
    pause
    exit /b 0
)

echo.
set /p "message=Commit message (default: Update NimblePDF): "
if not defined message set "message=Update NimblePDF"

echo.
echo Staging changes...
git add -A
if errorlevel 1 (
    echo Failed to stage changes.
    pause
    exit /b 1
)

echo Creating commit...
git commit -m "%message%"
if errorlevel 1 (
    echo Commit failed. Check the message above for details.
    pause
    exit /b 1
)

echo Pushing to GitHub...
git push
if errorlevel 1 (
    echo Push failed. Your changes are committed locally but not uploaded.
    echo Run this file again after fixing the GitHub authentication or network issue.
    pause
    exit /b 1
)

echo.
echo Update uploaded successfully.
echo Netlify will deploy it automatically.
pause
exit /b 0
