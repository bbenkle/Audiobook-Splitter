#!/usr/bin/env python3
"""
Audiobook Chapter Splitter
Detects chapter breaks and splits audiobook into separate files
Supports large files (>4GB) using ffmpeg directly
"""

import os
import argparse
import json
import re
import subprocess
import tempfile


def get_audio_duration(input_file):
    """Get audio duration in seconds using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error getting audio duration: {e.stderr}")


def get_audio_info(input_file):
    """Get detailed audio information using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'stream=codec_name,sample_rate,channels',
        '-show_entries', 'format=duration,size',
        '-of', 'json',
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error getting audio info: {e.stderr}")


def detect_silence_ffmpeg(input_file, noise_threshold=-40, duration=2.0):
    """
    Detect silence using ffmpeg's silencedetect filter.
    
    Args:
        input_file: Path to audio file
        noise_threshold: Noise threshold in dB (default -40)
        duration: Minimum silence duration in seconds (default 2.0)
    
    Returns:
        List of (start, end) tuples in seconds
    """
    print(f"Detecting silence using ffmpeg (threshold: {noise_threshold}dB, duration: {duration}s)...")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-af', f'silencedetect=noise={noise_threshold}dB:d={duration}',
        '-f', 'null',
        '-'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
        output = result.stdout + result.stderr
        
        # Parse silence detection output
        silence_starts = []
        silence_ends = []
        
        for line in output.split('\n'):
            if 'silencedetect' in line:
                if 'silence_start' in line:
                    match = re.search(r'silence_start: ([\d.]+)', line)
                    if match:
                        silence_starts.append(float(match.group(1)))
                elif 'silence_end' in line:
                    match = re.search(r'silence_end: ([\d.]+)', line)
                    if match:
                        silence_ends.append(float(match.group(1)))
        
        # Pair up starts and ends
        silences = []
        for i in range(min(len(silence_starts), len(silence_ends))):
            silences.append((silence_starts[i], silence_ends[i]))
        
        print(f"Found {len(silences)} silent segments")
        return silences
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error detecting silence: {e}")


def detect_chapters_by_silence(input_file, min_silence_duration=2.0, 
                               silence_threshold=-40, min_chapter_duration=180):
    """
    Detect chapter breaks based on silence.
    
    Args:
        input_file: Path to audio file
        min_silence_duration: Minimum silence duration in seconds
        silence_threshold: Silence threshold in dB
        min_chapter_duration: Minimum chapter duration in seconds
    
    Returns:
        List of (start, end) tuples in seconds
    """
    duration = get_audio_duration(input_file)
    silences = detect_silence_ffmpeg(input_file, silence_threshold, min_silence_duration)
    
    if not silences:
        print("No silence detected. Treating as single chapter.")
        return [(0, duration)]
    
    # Convert silences to chapter breaks
    chapters = []
    last_end = 0
    
    for silence_start, silence_end in silences:
        # Only consider this a chapter break if the chapter is long enough
        if silence_start - last_end >= min_chapter_duration:
            chapters.append((last_end, silence_start))
            last_end = silence_end
    
    # Add final chapter
    if duration - last_end >= min_chapter_duration:
        chapters.append((last_end, duration))
    elif chapters:
        # Extend last chapter to end
        chapters[-1] = (chapters[-1][0], duration)
    else:
        # No valid chapters, return whole file
        chapters = [(0, duration)]
    
    return chapters


def detect_chapters_from_metadata(input_file):
    """
    Extract chapter information from file metadata.
    
    Args:
        input_file: Path to audio file
    
    Returns:
        List of (start, end, title) tuples in seconds, or None if no chapters found
    """
    print("Checking for embedded chapter metadata...")
    
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_chapters',
        '-of', 'json',
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'chapters' not in data or not data['chapters']:
            print("No embedded chapters found.")
            return None
        
        chapters = []
        chapter_list = data['chapters']
        
        # Check if first chapter is opening credits
        skip_first = False
        if chapter_list and 'tags' in chapter_list[0]:
            first_title = chapter_list[0].get('tags', {}).get('title', '').lower()
            if 'opening' in first_title and 'credit' in first_title:
                skip_first = True
                print("Detected opening credits - merging with first chapter")
        
        start_index = 1 if skip_first else 0
        
        for i in range(start_index, len(chapter_list)):
            chapter = chapter_list[i]
            # If we skipped opening credits, start from 0 (beginning of file)
            start = 0 if i == start_index and skip_first else float(chapter['start_time'])
            end = float(chapter['end_time'])
            title = chapter.get('tags', {}).get('title', f'Chapter {i + 1 - start_index}')
            chapters.append((start, end, title))
        
        print(f"Found {len(chapters)} chapters (excluding opening credits)")
        return chapters
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
        print("No embedded chapters found.")
        return None
    """
    Detect chapters using speech recognition (for smaller files or samples).
    
    Args:
        input_file: Path to audio file
        sample_interval: Sampling interval in seconds
        context_window: Context window size in seconds
    
    Returns:
        List of (start, end, title) tuples in seconds
    """
    try:
        import speech_recognition as sr
    except ImportError:
        print("Error: speech_recognition not installed. Install with: pip install speechrecognition")
        return None
    
    print("Detecting chapters using speech recognition...")
    print("Note: This samples the audio and may take a while...")
    
    duration = get_audio_duration(input_file)
    recognizer = sr.Recognizer()
    chapter_markers = []
    
    position = 0
    while position < duration:
        # Extract segment using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        extract_cmd = [
            'ffmpeg',
            '-ss', str(position),
            '-i', input_file,
            '-t', str(context_window),
            '-ac', '1',  # Mono
            '-ar', '16000',  # 16kHz sample rate
            '-y',
            temp_path
        ]
        
        try:
            subprocess.run(extract_cmd, capture_output=True, check=True)
            
            # Perform speech recognition
            with sr.AudioFile(temp_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                
                # Look for chapter patterns
                chapter_match = re.search(
                    r'\b(?:chapter|part|section)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|[ivxlcdm]+)\b',
                    text, re.IGNORECASE
                )
                
                if chapter_match:
                    chapter_name = chapter_match.group(0)
                    print(f"  Found at {format_timestamp(position)}: '{text}'")
                    chapter_markers.append((position, chapter_name))
        
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"  Speech recognition error: {e}")
        except subprocess.CalledProcessError:
            pass
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        position += sample_interval
        
        # Progress indicator
        if int(position) % (sample_interval * 10) == 0:
            progress = (position / duration) * 100
            print(f"  Progress: {progress:.1f}%")
    
    if not chapter_markers:
        print("No chapter announcements detected.")
        return None
    
    # Convert to chapter ranges
    chapters = []
    for i, (start, name) in enumerate(chapter_markers):
        if i < len(chapter_markers) - 1:
            end = chapter_markers[i + 1][0]
        else:
            end = duration
        chapters.append((start, end, name))
    
    print(f"Detected {len(chapters)} chapters via speech recognition")
    return chapters


def load_chapters_from_json(json_file, audio_duration):
    """Load chapter information from JSON file"""
    print(f"Loading chapters from JSON: {json_file}")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    chapters = []
    for item in data:
        # Handle different formats
        if 'start_ms' in item and 'end_ms' in item:
            start = item['start_ms'] / 1000.0
            end = item['end_ms'] / 1000.0
        elif 'start' in item and 'end' in item:
            start = parse_timestamp(item['start'])
            end = parse_timestamp(item['end'])
        else:
            raise ValueError("Each entry must have 'start' and 'end' or 'start_ms' and 'end_ms'")
        
        title = item.get('title', item.get('name', f'Chapter {len(chapters) + 1}'))
        
        # Validate
        if start < 0 or end > audio_duration or start >= end:
            print(f"Warning: Invalid chapter range {start:.1f}-{end:.1f}s (duration: {audio_duration:.1f}s)")
            continue
        
        chapters.append((start, end, title))
    
    print(f"Loaded {len(chapters)} chapters from JSON")
    return chapters


def parse_timestamp(timestamp):
    """Convert timestamp string to seconds"""
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    
    parts = str(timestamp).split(':')
    if len(parts) == 3:
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = map(float, parts)
        return m * 60 + s
    else:
        return float(timestamp)


def format_timestamp(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def split_audio_segment(input_file, start, end, output_file, audio_format='mp3', bitrate='128k', mono=False):
    """Extract audio segment using ffmpeg"""
    duration = end - start
    
    # Build codec command based on format
    if audio_format == 'mp3':
        codec_args = ['-c:a', 'libmp3lame', '-b:a', bitrate]
    elif audio_format in ['m4a', 'm4b']:
        codec_args = ['-c:a', 'aac', '-b:a', bitrate]
    else:
        # For other formats, try copy first
        codec_args = ['-c', 'copy']
    
    # Add mono conversion if requested
    if mono and audio_format in ['mp3', 'm4a', 'm4b']:
        codec_args.extend(['-ac', '1'])
    
    cmd = [
        'ffmpeg',
        '-ss', str(start),
        '-i', input_file,
        '-t', str(duration),
        *codec_args,
        '-vn',  # No video
        '-y',
        output_file
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"Error splitting audio: {error_msg}")


def split_audiobook(input_file, output_dir="chapters", method="silence",
                   json_file=None, min_silence_duration=2.0, silence_threshold=-40,
                   min_chapter_duration=180, format="mp3", bitrate='128k', mono=False,
                   speech_interval=30, speech_window=10):
    """Split audiobook into chapters"""
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  Mac: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        print("  Windows: download from ffmpeg.org")
        return
    
    print(f"Loading audiobook: {input_file}")
    
    # Get audio info
    duration = get_audio_duration(input_file)
    info = get_audio_info(input_file)
    
    file_size_mb = int(info['format']['size']) / (1024 * 1024)
    print(f"Duration: {format_timestamp(duration)}")
    print(f"File size: {file_size_mb:.1f} MB")
    
    if 'streams' in info and info['streams']:
        stream = info['streams'][0]
        print(f"Codec: {stream.get('codec_name', 'unknown')}")
        print(f"Sample rate: {stream.get('sample_rate', 'unknown')} Hz")
        print(f"Channels: {stream.get('channels', 'unknown')}\n")
    
    # Detect chapters
    if method == "json":
        if not json_file:
            print("Error: JSON file required for 'json' method")
            return
        chapters_data = load_chapters_from_json(json_file, duration)
    elif method == "metadata":
        chapters_data = detect_chapters_from_metadata(input_file)
        if chapters_data is None:
            print("Falling back to silence detection...")
            method = "silence"
    elif method == "speech":
        chapters_data = detect_chapters_by_speech(input_file, speech_interval, speech_window)
        if chapters_data is None:
            print("Falling back to silence detection...")
            method = "silence"
    
    if method == "silence":
        chapters_raw = detect_chapters_by_silence(
            input_file, min_silence_duration, silence_threshold, min_chapter_duration
        )
        chapters_data = [(start, end, f"Chapter {i}")
                        for i, (start, end) in enumerate(chapters_raw, 1)]
    
    # Display detected chapters
    print(f"\nDetected {len(chapters_data)} chapters:")
    for i, (start, end, title) in enumerate(chapters_data, 1):
        duration_str = format_timestamp(end - start)
        print(f"  {title}: {format_timestamp(start)} - {format_timestamp(end)} ({duration_str})")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Export chapters
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    metadata = []
    
    print(f"\nExporting chapters to {output_dir}/")
    for i, (start, end, title) in enumerate(chapters_data, 1):
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        output_file = os.path.join(output_dir, f"{base_name}_{i:02d}_{safe_title}.{format}")
        
        print(f"  Exporting {title}...")
        split_audio_segment(input_file, start, end, output_file, format, bitrate, mono)
        
        metadata.append({
            "chapter": i,
            "title": title,
            "file": output_file,
            "start": format_timestamp(start),
            "end": format_timestamp(end),
            "duration": format_timestamp(end - start),
            "start_seconds": start,
            "end_seconds": end
        })
    
    # Save metadata
    metadata_file = os.path.join(output_dir, f"{base_name}_chapters.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nComplete! {len(chapters_data)} chapters exported.")
    print(f"Metadata saved to: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Split large audiobooks into chapters (supports files >4GB)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Detection Methods:
  metadata    Extract chapters from embedded file metadata (fastest, most accurate)
  speech      Use speech recognition to detect "Chapter X" announcements
  silence     Detect chapters based on silence/pauses in audio
  json        Use a pre-defined JSON file with chapter timings

Quality/Size Options:
  -b/--bitrate    Audio bitrate (default: 128k)
                  Lower = smaller files, higher = better quality
                  Recommendations:
                    96k  - Excellent quality, ~495MB for 11.5hrs
                    64k  - Good quality, ~330MB for 11.5hrs
                    48k  - Very good for speech, ~247MB for 11.5hrs (with --mono)
                    32k  - Acceptable, ~165MB for 11.5hrs (with --mono)
  
  --mono          Convert to mono audio (reduces file size by ~50%)
                  Good for audiobooks with single narrator
  
  -f/--format     Output format: mp3, m4a, m4b, wav, etc. (default: mp3)

Silence Detection Options (for --method silence):
  -s/--silence-duration    Minimum silence length in seconds (default: 2.0)
                           Longer = fewer false positives
  
  -t/--threshold          Silence threshold in dB (default: -40)
                          Lower (more negative) = quieter sounds considered silence
                          Examples: -50 (very quiet), -40 (default), -30 (louder)
  
  -m/--min-chapter        Minimum chapter duration in seconds (default: 180)
                          Prevents very short chapters from being created

Speech Recognition Options (for --method speech):
  --speech-interval       How often to sample audio in seconds (default: 30)
                          Lower = more thorough but slower
  
  --speech-window         Audio window size to analyze in seconds (default: 10)

Other Options:
  -o/--output            Output directory (default: chapters)
  --json                 Path to JSON file with chapter definitions

Examples:
  # Use embedded chapters with good compression (recommended)
  python audiobook_splitter.py mybook.m4a --method metadata -b 96k
  
  # Speech recognition (default)
  python audiobook_splitter.py mybook.m4a
  
  # Maximum compression (mono, low bitrate)
  python audiobook_splitter.py mybook.m4a -b 48k --mono
  
  # Custom silence detection
  python audiobook_splitter.py mybook.m4a --method silence -s 3.0 -t -35 -m 300
  
  # Use JSON file with custom output location
  python audiobook_splitter.py mybook.m4a --method json --json chapters.json -o my_chapters

JSON Format Example:
  [
    {"start": "00:00:00", "end": "00:15:30", "title": "Chapter 1"},
    {"start": "00:15:30", "end": "00:32:15", "title": "Chapter 2"}
  ]
  
  Or with milliseconds:
  [
    {"start_ms": 0, "end_ms": 930000, "title": "Chapter 1"},
    {"start_ms": 930000, "end_ms": 1932000, "title": "Chapter 2"}
  ]
        """
    )
    
    parser.add_argument("input", help="Input audiobook file")
    parser.add_argument("-o", "--output", default="chapters",
                       help="Output directory (default: chapters)")
    parser.add_argument("--method", choices=["metadata", "silence", "speech", "json"],
                       default="speech", help="Detection method (default: speech)")
    parser.add_argument("--json", dest="json_file",
                       help="JSON file with chapter definitions")
    parser.add_argument("-s", "--silence-duration", type=float, default=2.0,
                       help="Minimum silence duration in seconds (default: 2.0)")
    parser.add_argument("-t", "--threshold", type=int, default=-40,
                       help="Silence threshold in dB (default: -40)")
    parser.add_argument("-m", "--min-chapter", type=int, default=180,
                       help="Minimum chapter duration in seconds (default: 180)")
    parser.add_argument("-f", "--format", default="mp3",
                       help="Output format (default: mp3)")
    parser.add_argument("-b", "--bitrate", default="128k",
                       help="Audio bitrate (default: 128k). Examples: 48k, 64k, 96k")
    parser.add_argument("--mono", action="store_true",
                       help="Convert to mono (reduces file size by ~50%%)")
    parser.add_argument("--speech-interval", type=int, default=30,
                       help="Speech sampling interval in seconds (default: 30)")
    parser.add_argument("--speech-window", type=int, default=10,
                       help="Speech window size in seconds (default: 10)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return 1
    
    if args.method == "json" and not args.json_file:
        print("Error: --json required for 'json' method")
        return 1
    
    if args.json_file and not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found")
        return 1
    
    split_audiobook(
        args.input,
        args.output,
        args.method,
        args.json_file,
        args.silence_duration,
        args.threshold,
        args.min_chapter,
        args.format,
        args.bitrate,
        args.mono,
        args.speech_interval,
        args.speech_window
    )
    
    return 0


if __name__ == "__main__":
    exit(main())