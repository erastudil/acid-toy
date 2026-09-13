@echo off
cd /d "%~dp0"
where wt >nul 2>nul
if %errorlevel%==0 (
  wt -d "%~dp0" --title acid-toy python -m acidtoy
  exit /b 0
)
python -m acidtoy
if errorlevel 1 pause
