#!/usr/bin/env python3
"""
Audiobook Chapter Splitter - GUI Version
User-friendly interface for splitting audiobooks into chapters
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import json
import re
import subprocess
import tempfile
import queue


class AudiobookSplitterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audiobook Chapter Splitter")
        self.root.geometry("800x700")
        
        # Queue for thread-safe logging
        self.log_queue = queue.Queue()
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar(value="chapters")
        self.method = tk.StringVar(value="metadata")
        self.format_var = tk.StringVar(value="mp3")
        self.bitrate = tk.StringVar(value="96k")
        self.mono = tk.BooleanVar(value=False)
        self.json_file = tk.StringVar()
        self.processing = False
        
        self.create_widgets()
        self.check_log_queue()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Title
        title = ttk.Label(main_frame, text="Audiobook Chapter Splitter", 
                         font=('Helvetica', 16, 'bold'))
        title.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1
        
        # Input file section
        ttk.Label(main_frame, text="Input Audiobook:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        input_frame.columnconfigure(0, weight=1)
        
        input_entry = ttk.Entry(input_frame, textvariable=self.input_file)
        input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).grid(
            row=0, column=1)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Settings section
        ttk.Label(main_frame, text="Settings:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1
        
        # Detection method
        ttk.Label(main_frame, text="Detection Method:").grid(
            row=row, column=0, sticky=tk.W, pady=5)
        method_frame = ttk.Frame(main_frame)
        method_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        methods = [
            ("Metadata (Fastest)", "metadata"),
            ("Speech Recognition", "speech"),
            ("Silence Detection", "silence"),
            ("JSON File", "json")
        ]
        
        for i, (text, value) in enumerate(methods):
            ttk.Radiobutton(method_frame, text=text, variable=self.method, 
                          value=value, command=self.on_method_change).grid(
                              row=0, column=i, padx=(0, 15))
        row += 1
        
        # JSON file selection (initially hidden)
        self.json_frame = ttk.Frame(main_frame)
        self.json_label = ttk.Label(self.json_frame, text="JSON File:")
        self.json_entry = ttk.Entry(self.json_frame, textvariable=self.json_file)
        self.json_browse = ttk.Button(self.json_frame, text="Browse...", 
                                     command=self.browse_json)
        row += 1
        
        # Output format
        ttk.Label(main_frame, text="Output Format:").grid(
            row=row, column=0, sticky=tk.W, pady=5)
        format_combo = ttk.Combobox(main_frame, textvariable=self.format_var, 
                                   values=["mp3", "m4a", "m4b", "wav"], 
                                   state="readonly", width=15)
        format_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Bitrate
        ttk.Label(main_frame, text="Bitrate:").grid(
            row=row, column=0, sticky=tk.W, pady=5)
        bitrate_frame = ttk.Frame(main_frame)
        bitrate_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        bitrate_combo = ttk.Combobox(bitrate_frame, textvariable=self.bitrate,
                                    values=["32k", "48k", "64k", "96k", "128k", "192k"],
                                    state="readonly", width=10)
        bitrate_combo.grid(row=0, column=0)
        
        ttk.Label(bitrate_frame, text="  (Lower = smaller files)", 
                 foreground="gray").grid(row=0, column=1, sticky=tk.W)
        row += 1
        
        # Mono checkbox
        ttk.Checkbutton(main_frame, text="Convert to Mono (reduces file size ~50%)", 
                       variable=self.mono).grid(row=row, column=0, columnspan=2, 
                                               sticky=tk.W, pady=5)
        row += 1
        
        # Output directory
        ttk.Label(main_frame, text="Output Directory:").grid(
            row=row, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).grid(
            row=0, column=1)
        row += 1
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        row += 1
        
        # Progress and log section
        ttk.Label(main_frame, text="Progress:", font=('Helvetica', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(main_frame, height=12, width=70, 
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), 
                          pady=(0, 10))
        main_frame.rowconfigure(row, weight=1)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Processing", 
                                       command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                      command=self.stop_processing, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", 
                  command=self.clear_log).grid(row=0, column=2, padx=5)
        
    def on_method_change(self):
        """Show/hide JSON file selector based on method"""
        if self.method.get() == "json":
            self.json_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.json_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
            self.json_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
            self.json_frame.columnconfigure(1, weight=1)
            self.json_browse.grid(row=0, column=2)
        else:
            self.json_frame.grid_forget()
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Audiobook File",
            filetypes=[
                ("Audio Files", "*.m4a *.m4b *.mp3 *.mp4 *.wav *.aac"),
                ("All Files", "*.*")
            ]
        )
        if filename:
            self.input_file.set(filename)
            self.log(f"File selected: {os.path.basename(filename)}")
    
    def browse_json(self):
        filename = filedialog.askopenfilename(
            title="Select JSON Chapter File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            self.json_file.set(filename)
    
    def browse_output(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir.set(directory)
    
    def log(self, message):
        """Thread-safe logging"""
        self.log_queue.put(message)
    
    def check_log_queue(self):
        """Check for log messages and update GUI"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_log_queue)
    
    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def validate_inputs(self):
        """Validate user inputs before processing"""
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input audiobook file.")
            return False
        
        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("Error", "Input file does not exist.")
            return False
        
        if self.method.get() == "json" and not self.json_file.get():
            messagebox.showerror("Error", "Please select a JSON file for the JSON method.")
            return False
        
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", 
                "ffmpeg not found. Please install ffmpeg:\n\n"
                "Mac: brew install ffmpeg\n"
                "Ubuntu: sudo apt-get install ffmpeg\n"
                "Windows: download from ffmpeg.org")
            return False
        
        return True
    
    def start_processing(self):
        """Start processing in a separate thread"""
        if not self.validate_inputs():
            return
        
        self.processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress.start()
        
        # Run processing in separate thread
        thread = threading.Thread(target=self.process_audiobook, daemon=True)
        thread.start()
    
    def stop_processing(self):
        """Stop the processing"""
        self.processing = False
        self.log("Stopping... (current chapter will complete)")
    
    def process_audiobook(self):
        """Main processing logic (runs in separate thread)"""
        try:
            from audiobook_processor import AudiobookProcessor
            
            processor = AudiobookProcessor(self.log)
            
            result = processor.split_audiobook(
                input_file=self.input_file.get(),
                output_dir=self.output_dir.get(),
                method=self.method.get(),
                json_file=self.json_file.get() if self.json_file.get() else None,
                format=self.format_var.get(),
                bitrate=self.bitrate.get(),
                mono=self.mono.get(),
                stop_callback=lambda: not self.processing
            )
            
            if result and self.processing:
                self.log("\n✓ Processing complete!")
                messagebox.showinfo("Success", 
                    f"Successfully split audiobook into {result} chapters!")
            elif not self.processing:
                self.log("\n✗ Processing stopped by user")
        
        except Exception as e:
            self.log(f"\n✗ Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n\n{str(e)}")
        
        finally:
            self.root.after(0, self.processing_complete)
    
    def processing_complete(self):
        """Clean up after processing"""
        self.progress.stop()
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.processing = False


def main():
    root = tk.Tk()
    app = AudiobookSplitterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()