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

## Quick Start

### macOS / Linux

```bash
git clone https://github.com/bbenkle/audiobook-splitter.git
cd audiobook-splitter
bash setup.sh
python3 standalone_wrapper.py --input your_audiobook.m4b
```

### Windows

```powershell
git clone https://github.com/bbenkle/audiobook-splitter.git
cd audiobook-splitter
.\setup.bat
python standalone_wrapper.py --input your_audiobook.m4b
```

The setup scripts will automatically download ffmpeg and ffprobe for you.

---

## Requirements

### Python 3

**macOS:** Python 3 is pre-installed. Open Terminal and verify with:
```bash
python3 --version
```

**Linux:** Python 3 is pre-installed on most distributions. If not:
```bash
sudo apt-get install python3   # Ubuntu/Debian
sudo dnf install python3       # Fedora
```

**Windows:** Python 3 is not included with Windows and must be installed manually:
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3 installer
3. Run the installer — **make sure to check "Add Python to PATH"** during installation
4. Verify in Command Prompt: `python --version`

### ffmpeg

Handled automatically by the setup scripts below. If you prefer to install manually:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH, or just use the setup script.

### Optional (for speech recognition method)
```bash
pip3 install SpeechRecognition    # macOS/Linux
pip install SpeechRecognition     # Windows
```

---

## Setup Scripts

### macOS / Linux — `setup.sh`

Downloads ffmpeg and ffprobe into the project directory:

```bash
bash setup.sh
```

After running, use the `--ffmpeg-path` and `--ffprobe-path` flags if ffmpeg is not in your PATH:
```bash
python3 standalone_wrapper.py --input audiobook.m4b --ffmpeg-path ./ffmpeg --ffprobe-path ./ffprobe
```

### Windows — `setup.bat`

Downloads ffmpeg and ffprobe into the project directory using PowerShell:

```powershell
.\setup.bat
```

After running, use the `--ffmpeg-path` and `--ffprobe-path` flags:
```powershell
python standalone_wrapper.py --input audiobook.m4b --ffmpeg-path .\ffmpeg.exe --ffprobe-path .\ffprobe.exe
```

> **Note for Windows users:** If you see a security warning when running the setup script, right-click `setup.bat` and choose **Run as administrator**.

---

## Usage

### Command Line

```bash
python3 standalone_wrapper.py --input audiobook.m4b   # macOS/Linux
python standalone_wrapper.py --input audiobook.m4b    # Windows
```

#### Help

```
$ python3 standalone_wrapper.py --help

usage: standalone_wrapper.py [-h] --input INPUT [--output OUTPUT]
                             [--method {metadata,silence,speech,json}]
                             [--json JSON] [--format FORMAT]
                             [--bitrate BITRATE] [--mono]
                             [--ffmpeg-path FFMPEG_PATH]
                             [--ffprobe-path FFPROBE_PATH]

Audiobook Chapter Splitter

options:
  -h, --help            show this help message and exit
  --input INPUT         Input audiobook file
  --output OUTPUT       Output directory
  --method {metadata,silence,speech,json}
                        Detection method
  --json JSON           JSON file with chapters
  --format FORMAT       Output format
  --bitrate BITRATE     Audio bitrate
  --mono                Convert to mono
  --ffmpeg-path FFMPEG_PATH
                        Path to ffmpeg executable
  --ffprobe-path FFPROBE_PATH
                        Path to ffprobe executable
```

#### All Options

```bash
python3 standalone_wrapper.py \
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
python3 audiobook_splitter_gui.py   # macOS/Linux
python audiobook_splitter_gui.py    # Windows
```

A Tkinter-based GUI with all the same options, real-time progress logging, and a stop button.

---

## Detection Methods

### `metadata` *(Recommended — fastest)*
Extracts chapter markers embedded in the audiobook file. Most M4B audiobooks from Audible or ripped from CD include these. Falls back to silence detection if none are found.

```bash
python3 standalone_wrapper.py --input audiobook.m4b --method metadata
```

### `silence`
Detects chapter breaks by finding silent gaps in the audio. Works well for audiobooks without embedded metadata.

```bash
python3 standalone_wrapper.py --input audiobook.mp3 --method silence
```

### `speech`
Uses Google Speech Recognition to detect spoken chapter announcements (e.g. "Chapter One"). Slowest method — scans the entire file.

```bash
python3 standalone_wrapper.py --input audiobook.mp3 --method speech
```

### `json`
Load chapter timestamps from a JSON file you define. Useful if you already know the chapter positions.

```bash
python3 standalone_wrapper.py --input audiobook.mp3 --method json --json chapters.json
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
├── setup.sh                    # macOS/Linux setup script
├── setup.bat                   # Windows setup script
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
