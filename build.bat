@echo off
REM Build INTAI.exe

pyinstaller --noconfirm --uac-admin --icon=assets/app_icon.ico --name INTAI main.py ^
  --add-data "config/config.json;config" ^
  --add-data "templates;templates" ^
  --hidden-import=core.run_arena ^
  --hidden-import=core.run_aram ^
  --hidden-import=core.run_test ^
  --hidden-import=core.run_yuumi_sr
  
echo Build complete. Check the dist folder for INTAI.exe.
pause