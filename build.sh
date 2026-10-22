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
      matrix:
        include:
          - os: macos-latest
            asset_name: TikTokUserChecker-macOS.zip
          - os: ubuntu-latest
            asset_name: TikTokUserChecker-Linux.zip

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies (Linux)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y zip

      - name: Run Build Script
        run: |
          chmod +x build.sh
          ./build.sh

      - name: Compress Build Output
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
