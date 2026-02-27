# Audiobook Chapter Splitter

A Python tool to split audiobook files into individual chapter files. Supports multiple chapter detection methods including embedded metadata, silence detection, speech recognition, and JSON-defined chapters.

---

## Features

- **Multiple detection methods** — metadata, silence, speech recognition, or JSON
- **No file size limits** — uses ffmpeg directly, handles files over 4GB
- **Flexible output** — MP3, M4A, M4B, or WAV
- **Configurable quality** — bitrate from 32k to 192k
- **Mono conversion** — reduce file size by ~50%
- **Auto chapter naming** — sanitized filenames with chapter titles
- **Opening credits handling** — automatically merges opening credits into the first chapter
- **Metadata export** — saves chapter info to a JSON file alongside output

---

## Requirements

- Python 3.x
- ffmpeg and ffprobe

### Install ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**  
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.

### Optional (for speech recognition method)
```bash
pip install SpeechRecognition
```

---

## Installation

```bash
git clone https://github.com/bbenkle/audiobook-splitter.git
cd audiobook-splitter
```

No additional Python dependencies required for the core functionality.

---

## Usage

### Command Line

```bash
python standalone_wrapper.py --input audiobook.m4b
```

#### All Options

```bash
python standalone_wrapper.py \
  --input audiobook.m4b \
  --output ./chapters \
  --method metadata \
  --format mp3 \
  --bitrate 96k \
  --mono
```

| Argument | Default | Description |
|---|---|---|
| `--input` | *(required)* | Path to the input audiobook file |
| `--output` | `chapters` | Output directory for chapter files |
| `--method` | `metadata` | Detection method (see below) |
| `--format` | `mp3` | Output format: `mp3`, `m4a`, `m4b`, `wav` |
| `--bitrate` | `96k` | Audio bitrate: `32k`, `48k`, `64k`, `96k`, `128k`, `192k` |
| `--mono` | off | Convert to mono (flag, no value needed) |
| `--json` | — | Path to JSON chapter file (required for `json` method) |
| `--ffmpeg-path` | `ffmpeg` | Custom path to ffmpeg binary |
| `--ffprobe-path` | `ffprobe` | Custom path to ffprobe binary |

### GUI

```bash
python audiobook_splitter_gui.py
```

A Tkinter-based GUI with all the same options, real-time progress logging, and a stop button.

---

## Detection Methods

### `metadata` *(Recommended — fastest)*
Extracts chapter markers embedded in the audiobook file. Most M4B audiobooks from Audible or ripped from CD include these. Falls back to silence detection if none are found.

```bash
python standalone_wrapper.py --input audiobook.m4b --method metadata
```

### `silence`
Detects chapter breaks by finding silent gaps in the audio. Works well for audiobooks without embedded metadata.

```bash
python standalone_wrapper.py --input audiobook.mp3 --method silence
```

### `speech`
Uses Google Speech Recognition to detect spoken chapter announcements (e.g. "Chapter One"). Slowest method — scans the entire file.

```bash
python standalone_wrapper.py --input audiobook.mp3 --method speech
```

### `json`
Load chapter timestamps from a JSON file you define. Useful if you already know the chapter positions.

```bash
python standalone_wrapper.py --input audiobook.mp3 --method json --json chapters.json
```

#### JSON Format

```json
[
  { "title": "Chapter 1", "start": "00:00:00", "end": "00:45:12" },
  { "title": "Chapter 2", "start": "00:45:12", "end": "01:32:44" }
]
```

You can also use milliseconds:
```json
[
  { "title": "Chapter 1", "start_ms": 0, "end_ms": 2712000 }
]
```

---

## Output

Chapter files are saved to the output directory with names like:

```
audiobook_01_Chapter_One.mp3
audiobook_02_Chapter_Two.mp3
...
audiobook_chapters.json   ← metadata for all chapters
```

The metadata JSON contains start/end times, duration, and file paths for each chapter.

---

## File Structure

```
audiobook-splitter/
├── audiobook_processor.py      # Core processing logic
├── standalone_wrapper.py       # CLI entry point
├── audiobook_splitter_gui.py   # Tkinter GUI
└── README.md
```

---

## Supported Input Formats

Any format supported by ffmpeg, including:
- `.m4b` — Audiobook (most common)
- `.m4a` — iTunes audio
- `.mp3` — MP3
- `.mp4` — MPEG-4
- `.wav` — Waveform audio
- `.aac` — AAC audio

---

## License

MIT
