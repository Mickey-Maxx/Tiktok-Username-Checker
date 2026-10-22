#!/usr/bin/env bash
set -e

echo "Building executable with PyInstaller..."

# Determine app name based on OS
OS_NAME=$(uname -s)
if [ "$OS_NAME" = "Darwin" ]; then
    EXE_NAME="TikTok Username Checker"
else
    EXE_NAME="TikTokUsernameChecker"
fi

# Clean previous builds
rm -rf build dist

# Run PyInstaller
pyinstaller --noconfirm --clean --onefile --windowed \
  --name "$EXE_NAME" \
  --collect-all customtkinter \
  tiktok_username_checker_gui.py

echo "Organizing output folder..."
mkdir -p dist/TikTokUserChecker/data

if [ -d "dist/$EXE_NAME.app" ]; then
    mv "dist/$EXE_NAME.app" dist/TikTokUserChecker/
elif [ -f "dist/$EXE_NAME" ]; then
    mv "dist/$EXE_NAME" dist/TikTokUserChecker/
fi

echo "Build complete!"
