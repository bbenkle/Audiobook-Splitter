#!/bin/bash
# setup.sh - Downloads ffmpeg and ffprobe for macOS/Linux

set -e

echo "🔧 Audiobook Splitter Setup"
echo ""

# Detect OS
OS="$(uname -s)"

if [ "$OS" = "Darwin" ]; then
    echo "Detected: macOS"
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    FFPROBE_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"

    # Download ffmpeg
    if [ ! -f "ffmpeg" ]; then
        echo "Downloading ffmpeg..."
        curl -L -o ffmpeg.zip "$FFMPEG_URL"
        unzip -o ffmpeg.zip
        rm ffmpeg.zip
        chmod +x ffmpeg
        echo "✓ ffmpeg downloaded"
    else
        echo "✓ ffmpeg already exists, skipping"
    fi

    # Download ffprobe
    if [ ! -f "ffprobe" ]; then
        echo "Downloading ffprobe..."
        curl -L -o ffprobe.zip "$FFPROBE_URL"
        unzip -o ffprobe.zip
        rm ffprobe.zip
        chmod +x ffprobe
        echo "✓ ffprobe downloaded"
    else
        echo "✓ ffprobe already exists, skipping"
    fi

    # Remove macOS quarantine flag so the binaries can run
    echo "Clearing macOS quarantine flags..."
    xattr -d com.apple.quarantine ffmpeg 2>/dev/null || true
    xattr -d com.apple.quarantine ffprobe 2>/dev/null || true

elif [ "$OS" = "Linux" ]; then
    echo "Detected: Linux"
    echo "Installing ffmpeg via package manager..."

    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm ffmpeg
    else
        echo "Could not detect package manager. Please install ffmpeg manually."
        echo "Visit: https://ffmpeg.org/download.html"
        exit 1
    fi

    echo "✓ ffmpeg installed"
else
    echo "Unsupported OS: $OS"
    echo "Please install ffmpeg manually from https://ffmpeg.org/download.html"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""

# Check if ffmpeg is in PATH or local
if command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is in your PATH. You can run:"
    echo "  python3 standalone_wrapper.py --input your_audiobook.m4b"
else
    echo "ffmpeg is in the project directory. Run with:"
    echo "  python3 standalone_wrapper.py --input your_audiobook.m4b --ffmpeg-path ./ffmpeg --ffprobe-path ./ffprobe"
fi
