#!/bin/bash
# Create a bundled Python runtime for the app

set -e

echo "Creating bundled Python environment..."

# Clean up old bundle
rm -rf python_bundle

# Create a minimal Python bundle directory
mkdir -p python_bundle

# Copy Python scripts
cp audiobook_processor.py python_bundle/
cp audiobook_processor_cli.py python_bundle/

# Make CLI executable
chmod +x python_bundle/audiobook_processor_cli.py

echo "✓ Python bundle created in python_bundle/"
echo ""
echo "Next steps:"
echo "1. Add the entire 'python_bundle' folder to Xcode"
echo "2. Update PythonRunner.swift to use system Python with bundled scripts"
