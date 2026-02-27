"""
Audiobook processing module - backend logic for splitting audiobooks
"""

import os
import json
import re
import subprocess
import tempfile


class AudiobookProcessor:
    def __init__(self, log_callback=print, ffmpeg_path=None, ffprobe_path=None):
        self.log = log_callback
        self.ffmpeg_path = ffmpeg_path or 'ffmpeg'
        self.ffprobe_path = ffprobe_path or 'ffprobe'
        
        # Debug logging
        self.log(f"AudiobookProcessor initialized:")
        self.log(f"  ffmpeg_path: {self.ffmpeg_path}")
        self.log(f"  ffprobe_path: {self.ffprobe_path}")
        
        import os
        if os.path.exists(self.ffmpeg_path):
            self.log(f"  ✓ ffmpeg exists at path")
        else:
            self.log(f"  ✗ ffmpeg NOT found at path")
        
        if os.path.exists(self.ffprobe_path):
            self.log(f"  ✓ ffprobe exists at path")
        else:
            self.log(f"  ✗ ffprobe NOT found at path")
    
    def get_audio_duration(self, input_file):
        """Get audio duration in seconds"""
        cmd = [
            self.ffprobe_path, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def detect_chapters_from_metadata(self, input_file):
        """Extract chapters from file metadata"""
        self.log("Checking for embedded chapter metadata...")
        
        cmd = [self.ffprobe_path, '-v', 'error', '-show_chapters', '-of', 'json', input_file]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if 'chapters' not in data or not data['chapters']:
            self.log("No embedded chapters found.")
            return None
        
        chapters = []
        chapter_list = data['chapters']
        
        # Check for opening credits
        skip_first = False
        if chapter_list and 'tags' in chapter_list[0]:
            first_title = chapter_list[0].get('tags', {}).get('title', '').lower()
            if 'opening' in first_title and 'credit' in first_title:
                skip_first = True
                self.log("Detected opening credits - merging with first chapter")
        
        start_index = 1 if skip_first else 0
        
        for i in range(start_index, len(chapter_list)):
            chapter = chapter_list[i]
            start = 0 if i == start_index and skip_first else float(chapter['start_time'])
            end = float(chapter['end_time'])
            title = chapter.get('tags', {}).get('title', f'Chapter {i + 1 - start_index}')
            chapters.append((start, end, title))
        
        self.log(f"Found {len(chapters)} chapters")
        return chapters
    
    def detect_chapters_by_silence(self, input_file, threshold=-40, duration=2.0, min_chapter=180):
        """Detect chapters using silence detection"""
        self.log(f"Detecting silence (threshold: {threshold}dB, duration: {duration}s)...")
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-af', f'silencedetect=noise={threshold}dB:d={duration}',
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
        output = result.stdout + result.stderr
        
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
        
        silences = list(zip(silence_starts, silence_ends))
        self.log(f"Found {len(silences)} silent segments")
        
        # Convert to chapters
        audio_duration = self.get_audio_duration(input_file)
        chapters = []
        last_end = 0
        
        for silence_start, silence_end in silences:
            if silence_start - last_end >= min_chapter:
                chapters.append((last_end, silence_start, f'Chapter {len(chapters) + 1}'))
                last_end = silence_end
        
        if audio_duration - last_end >= min_chapter:
            chapters.append((last_end, audio_duration, f'Chapter {len(chapters) + 1}'))
        elif chapters:
            chapters[-1] = (chapters[-1][0], audio_duration, chapters[-1][2])
        else:
            chapters = [(0, audio_duration, 'Chapter 1')]
        
        self.log(f"Detected {len(chapters)} chapters")
        return chapters
    
    def detect_chapters_by_speech(self, input_file, interval=30, window=10):
        """Detect chapters using speech recognition"""
        try:
            import speech_recognition as sr
        except ImportError:
            self.log("Error: speech_recognition not installed")
            return None
        
        self.log("Using speech recognition to detect chapters...")
        self.log("This may take a while...")
        
        duration = self.get_audio_duration(input_file)
        recognizer = sr.Recognizer()
        chapter_markers = []
        
        position = 0
        while position < duration:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            extract_cmd = [
                'ffmpeg', '-ss', str(position), '-i', input_file,
                '-t', str(window), '-ac', '1', '-ar', '16000', '-y', temp_path
            ]
            
            try:
                subprocess.run(extract_cmd, capture_output=True, check=True)
                
                with sr.AudioFile(temp_path) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                    
                    chapter_match = re.search(
                        r'\b(?:chapter|part|section)\s+(\d+|one|two|three|four|five|[ivxlcdm]+)\b',
                        text, re.IGNORECASE
                    )
                    
                    if chapter_match:
                        chapter_name = chapter_match.group(0)
                        self.log(f"  Found: {chapter_name} at {self.format_timestamp(position)}")
                        chapter_markers.append((position, chapter_name))
            
            except:
                pass
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            position += interval
            
            if int(position) % (interval * 5) == 0:
                progress = (position / duration) * 100
                self.log(f"  Progress: {progress:.1f}%")
        
        if not chapter_markers:
            self.log("No chapter announcements detected")
            return None
        
        chapters = []
        for i, (start, name) in enumerate(chapter_markers):
            end = chapter_markers[i + 1][0] if i < len(chapter_markers) - 1 else duration
            chapters.append((start, end, name))
        
        self.log(f"Detected {len(chapters)} chapters")
        return chapters
    
    def load_chapters_from_json(self, json_file, audio_duration):
        """Load chapters from JSON file"""
        self.log(f"Loading chapters from JSON: {json_file}")
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        chapters = []
        for item in data:
            if 'start_ms' in item and 'end_ms' in item:
                start = item['start_ms'] / 1000.0
                end = item['end_ms'] / 1000.0
            elif 'start' in item and 'end' in item:
                start = self.parse_timestamp(item['start'])
                end = self.parse_timestamp(item['end'])
            else:
                raise ValueError("Invalid JSON format")
            
            title = item.get('title', item.get('name', f'Chapter {len(chapters) + 1}'))
            
            if 0 <= start < end <= audio_duration:
                chapters.append((start, end, title))
        
        self.log(f"Loaded {len(chapters)} chapters")
        return chapters
    
    def parse_timestamp(self, timestamp):
        """Convert timestamp to seconds"""
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        
        parts = str(timestamp).split(':')
        if len(parts) == 3:
            h, m, s = map(float, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(float, parts)
            return m * 60 + s
        return float(timestamp)
    
    def format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def split_audio_segment(self, input_file, start, end, output_file, 
                           audio_format='mp3', bitrate='128k', mono=False):
        """Extract audio segment"""
        duration = end - start
        
        if audio_format == 'mp3':
            codec_args = ['-c:a', 'libmp3lame', '-b:a', bitrate]
        elif audio_format in ['m4a', 'm4b']:
            codec_args = ['-c:a', 'aac', '-b:a', bitrate]
        else:
            codec_args = ['-c', 'copy']
        
        if mono and audio_format in ['mp3', 'm4a', 'm4b']:
            codec_args.extend(['-ac', '1'])
        
        cmd = [
            self.ffmpeg_path, '-ss', str(start), '-i', input_file,
            '-t', str(duration), *codec_args, '-vn', '-y', output_file
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
    
    def split_audiobook(self, input_file, output_dir="chapters", method="metadata",
                       json_file=None, format="mp3", bitrate='128k', mono=False,
                       stop_callback=None):
        """Main splitting logic"""
        
        self.log(f"Loading audiobook: {os.path.basename(input_file)}")
        duration = self.get_audio_duration(input_file)
        self.log(f"Duration: {self.format_timestamp(duration)}")
        
        # Detect chapters
        if method == "json":
            if not json_file:
                raise ValueError("JSON file required")
            chapters_data = self.load_chapters_from_json(json_file, duration)
        elif method == "metadata":
            chapters_data = self.detect_chapters_from_metadata(input_file)
            if not chapters_data:
                self.log("Falling back to silence detection...")
                method = "silence"
        elif method == "speech":
            chapters_data = self.detect_chapters_by_speech(input_file)
            if not chapters_data:
                self.log("Falling back to silence detection...")
                method = "silence"
        
        if method == "silence":
            chapters_data = self.detect_chapters_by_silence(input_file)
        
        # Display chapters
        self.log(f"\nDetected {len(chapters_data)} chapters:")
        for i, (start, end, title) in enumerate(chapters_data, 1):
            dur = self.format_timestamp(end - start)
            self.log(f"  {title}: {self.format_timestamp(start)} - {self.format_timestamp(end)} ({dur})")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export chapters
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        self.log(f"\nExporting chapters to {output_dir}/")
        
        for i, (start, end, title) in enumerate(chapters_data, 1):
            if stop_callback and stop_callback():
                self.log("Stopping...")
                return None
            
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            output_file = os.path.join(output_dir, f"{base_name}_{i:02d}_{safe_title}.{format}")
            
            self.log(f"  Exporting {title}...")
            self.split_audio_segment(input_file, start, end, output_file, format, bitrate, mono)
        
        # Save metadata
        metadata = []
        for i, (start, end, title) in enumerate(chapters_data, 1):
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            output_file = os.path.join(output_dir, f"{base_name}_{i:02d}_{safe_title}.{format}")
            metadata.append({
                "chapter": i,
                "title": title,
                "file": output_file,
                "start": self.format_timestamp(start),
                "end": self.format_timestamp(end),
                "duration": self.format_timestamp(end - start)
            })
        
        metadata_file = os.path.join(output_dir, f"{base_name}_chapters.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.log(f"\nMetadata saved to: {metadata_file}")
        return len(chapters_data)