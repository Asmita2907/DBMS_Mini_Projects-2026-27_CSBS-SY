@echo off
setlocal
cd /d "%~dp0"
title AURA Health Launcher

where python >nul 2>&1
if %errorlevel%==0 goto use_python
where py >nul 2>&1
if %errorlevel%==0 goto use_py

echo Python was not found on this computer.
echo Install Python from https://www.python.org/downloads/ and select "Add Python to PATH" during installation.
echo Then double-click START_WEBSITE.bat again.
pause
exit /b 1

:use_python
start "AURA Health Server" cmd /k "cd /d ""%~dp0"" && python local_server.py"
goto open_browser

:use_py
start "AURA Health Server" cmd /k "cd /d ""%~dp0"" && py local_server.py"

:open_browser
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"
echo.
echo AURA Health should open in your browser.
echo Keep the AURA Health Server command window open while using the website.
echo To stop the website, close the server window.
exit /b 0
