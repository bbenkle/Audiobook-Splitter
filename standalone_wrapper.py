#!/usr/bin/env python3
"""
Audiobook Processor CLI Wrapper
Standalone executable version with command-line arguments
"""

import argparse
import sys
import os

# Import the processor module
from audiobook_processor import AudiobookProcessor


def main():
    parser = argparse.ArgumentParser(description="Audiobook Chapter Splitter")
    parser.add_argument("--input", required=True, help="Input audiobook file")
    parser.add_argument("--output", default="chapters", help="Output directory")
    parser.add_argument("--method", default="metadata", 
                       choices=["metadata", "silence", "speech", "json"],
                       help="Detection method")
    parser.add_argument("--json", help="JSON file with chapters")
    parser.add_argument("--format", default="mp3", help="Output format")
    parser.add_argument("--bitrate", default="96k", help="Audio bitrate")
    parser.add_argument("--mono", action="store_true", help="Convert to mono")
    parser.add_argument("--ffmpeg-path", default="ffmpeg", help="Path to ffmpeg executable")
    parser.add_argument("--ffprobe-path", default="ffprobe", help="Path to ffprobe executable")
    
    args = parser.parse_args()
    
    def log(message):
        print(message, flush=True)
    
    # Debug logging
    log(f"Received ffmpeg path: {args.ffmpeg_path}")
    log(f"Received ffprobe path: {args.ffprobe_path}")
    
    # Check if they exist
    import os
    if os.path.exists(args.ffmpeg_path):
        log(f"✓ ffmpeg found at: {args.ffmpeg_path}")
    else:
        log(f"✗ ffmpeg NOT found at: {args.ffmpeg_path}")
    
    if os.path.exists(args.ffprobe_path):
        log(f"✓ ffprobe found at: {args.ffprobe_path}")
    else:
        log(f"✗ ffprobe NOT found at: {args.ffprobe_path}")
    
    try:
        processor = AudiobookProcessor(log, args.ffmpeg_path, args.ffprobe_path)
        
        result = processor.split_audiobook(
            input_file=args.input,
            output_dir=args.output,
            method=args.method,
            json_file=args.json,
            format=args.format,
            bitrate=args.bitrate,
            mono=args.mono
        )
        
        # Output chapter count for Swift to parse
        print(f"CHAPTER_COUNT:{result}", flush=True)
        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
