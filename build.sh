#!/usr/bin/env bash
# Build the INTAI executable for Linux.
set -euo pipefail

pyinstaller --noconfirm --name INTAI main.py \
  --add-data "config/config.json:config" \
  --add-data "templates:templates" \
  --hidden-import=core.run_arena \
  --hidden-import=core.run_aram \
  --hidden-import=core.run_test \
  --hidden-import=core.run_yuumi_sr

echo "Build complete. Check the dist folder for the INTAI executable."
