@echo off
REM Build INTAI.exe

pyinstaller --icon=assets/app_icon.ico --name INTAI main.py ^
  --add-data "config/config.json;config" ^
  --add-data "config/config_default.json;config" ^
  --hidden-import=core.run_arena

echo Build complete. Check the dist folder for INTAI.exe.
pause