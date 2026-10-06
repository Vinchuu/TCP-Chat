@echo off
title Push to GitHub - Vinchuu/TCP-Chat
color 0B
echo ========================================================
echo       Pushing Project to GitHub Repository
echo       Repository: https://github.com/Vinchuu/TCP-Chat
echo ========================================================
echo.
git push -u origin main
echo.
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Pushed successfully to https://github.com/Vinchuu/TCP-Chat
) else (
    echo [NOTICE] If prompted, sign in via browser or Personal Access Token (PAT).
)
echo.
pause
