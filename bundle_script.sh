#!/bin/bash
# Bundle Dependencies Script
# Creates a standalone Python executable with all dependencies

set -e

echo "🔨 Bundling Audiobook Splitter Dependencies..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Install PyInstaller if not already installed
echo -e "${BLUE}Installing PyInstaller...${NC}"
pip3 install pyinstaller

# 2. Create a standalone executable from Python script
echo -e "${BLUE}Creating standalone Python executable...${NC}"
pyinstaller --onefile \
    --name audiobook_processor_standalone \
    --hidden-import json \
    --hidden-import re \
    --hidden-import subprocess \
    --hidden-import tempfile \
    --hidden-import os \
    --clean \
    audiobook_processor.py

# 3. Download ffmpeg binaries
echo -e "${BLUE}Downloading ffmpeg binaries...${NC}"
cd dist

if [ ! -f "ffmpeg" ]; then
    curl -L -O https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip
    unzip zip
    rm zip
fi

if [ ! -f "ffprobe" ]; then
    curl -L -O https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip
    unzip zip
    rm zip
fi

# Make binaries executable
chmod +x ffmpeg
chmod +x ffprobe
chmod +x audiobook_processor_standalone

cd ..

echo -e "${GREEN}✅ Dependencies bundled successfully!${NC}"
echo ""
echo "Bundled files are in: ./dist/"
echo "  - audiobook_processor_standalone (Python executable)"
echo "  - ffmpeg"
echo "  - ffprobe"
echo ""
echo "Next steps:"
echo "  1. Add these files to your Xcode project Resources folder"
echo "  2. Update PythonRunner.swift to use bundled binaries"
