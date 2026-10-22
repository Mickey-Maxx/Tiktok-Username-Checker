#!/usr/bin/env bash
# ------------------------------------------------------------------
# Builds and packages TikTok Username Checker for macOS / Linux.
# ------------------------------------------------------------------

set -e # Exit immediately if a command exits with a non-zero status

echo "Cleaning old build artifacts..."
rm -rf build dist

echo ""
echo "Installing/updating build tools..."
python3 -m pip install --upgrade pyinstaller requests customtkinter

echo ""
echo "Building the application..."

# Detect Operating System for proper path separators and extensions
OS_NAME=$(uname -s)

if [ "$OS_NAME" = "Darwin" ]; then
    echo "Detected OS: macOS"
    
    # macOS PyInstaller build
    python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
      --name "TikTok Username Checker" \
      --icon "Assets/app_icon.png" \
      --add-data "Assets/app_icon.png:." \
      --hidden-import tiktok_username_checker \
      --collect-all customtkinter \
      tiktok_username_checker_gui.py

    echo ""
    echo "Organizing final distribution package for macOS..."
    mkdir -p dist/TikTokUserChecker/data
    mv "dist/TikTok Username Checker.app" dist/TikTokUserChecker/ 2>/dev/null || mv "dist/TikTok Username Checker" dist/TikTokUserChecker/

else
    echo "Detected OS: Linux"

    # Linux PyInstaller build
    python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
      --name "TikTokUsernameChecker" \
      --icon "Assets/app_icon.png" \
      --add-data "Assets/app_icon.png:." \
      --hidden-import tiktok_username_checker \
      --collect-all customtkinter \
      tiktok_username_checker_gui.py

    echo ""
    echo "Organizing final distribution package for Linux..."
    mkdir -p dist/TikTokUserChecker/data
    mv dist/TikTokUsernameChecker dist/TikTokUserChecker/
fi

echo ""
echo "Done! Your packaged folder is located at: dist/TikTokUserChecker"