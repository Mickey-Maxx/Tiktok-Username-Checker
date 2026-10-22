name: Build Cross-Platform Executables

on:
  release:
    types: [published]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    name: Build on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-latest
            asset_name: TikTokUserChecker-macOS.zip
            exe_name: TikTokUsernameChecker
          - os: ubuntu-latest
            asset_name: TikTokUserChecker-Linux.zip
            exe_name: TikTokUsernameChecker

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install system dependencies (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y zip libtk8.6 python3-tk

      - name: Install Python packages
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller requests customtkinter

      - name: Build Executable with PyInstaller
        run: |
          pyinstaller --noconfirm --clean --onefile --windowed \
            --name "${{ matrix.exe_name }}" \
            --collect-all customtkinter \
            tiktok_username_checker_gui.py

      - name: Prepare Folder and Data Directory
        run: |
          mkdir -p dist/TikTokUserChecker/data
          if [ -d "dist/${{ matrix.exe_name }}.app" ]; then
            mv "dist/${{ matrix.exe_name }}.app" dist/TikTokUserChecker/
          elif [ -f "dist/${{ matrix.exe_name }}" ]; then
            mv "dist/${{ matrix.exe_name }}" dist/TikTokUserChecker/
          fi

      - name: Zip Package
        run: |
          cd dist
          zip -r ../${{ matrix.asset_name }} TikTokUserChecker

      - name: Upload Release Asset
        uses: softprops/action-gh-release@v2
        with:
          files: ${{ matrix.asset_name }}
          tag_name: v1.0.0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
