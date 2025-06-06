import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import yt_dlp # Changed from subprocess to direct library import
import sys # To detect if running as a bundle
import stat # For chmod constants

# Helper for yt-dlp logging
class YtdlpLogger:
    def __init__(self, app_logger_func):
        self.app_logger_func = app_logger_func

    def debug(self, msg):
        # yt-dlp can be very verbose in debug, pass through for now
        if msg.startswith('[debug] '):
            self.app_logger_func(msg.strip())
        else:
            self.app_logger_func(f"[debug] {msg.strip()}")

    def info(self, msg):
        self.app_logger_func(msg.strip())

    def warning(self, msg):
        self.app_logger_func(f"WARNING: {msg.strip()}")

    def error(self, msg):
        self.app_logger_func(f"ERROR: {msg.strip()}")

# Helper for yt-dlp progress hooks
def ytdlp_progress_hook(d, app_logger_func):
    if d['status'] == 'downloading':
        # filename = d.get('filename') or d.get('info_dict', {}).get('title', 'N/A')
        # total_bytes_str = d.get('_total_bytes_str', 'N/A')
        # speed_str = d.get('_speed_str', 'N/A')
        # eta_str = d.get('_eta_str', 'N/A')
        # percent_str = d.get('_percent_str', 'N/A').strip()
        # app_logger_func(f"Downloading {filename}: {percent_str} of {total_bytes_str} at {speed_str}, ETA {eta_str}")
        # The logger itself will print detailed download progress, so this can be minimal
        pass
    elif d['status'] == 'finished':
        filename = d.get('filename') or d.get('info_dict', {}).get('title', 'N/A')
        app_logger_func(f"Finished downloading: {filename}")
        if d.get('total_bytes') is not None:
             app_logger_func(f"Total size: {d.get('_total_bytes_str', 'N/A')}")
    elif d['status'] == 'error':
        filename = d.get('filename') or d.get('info_dict', {}).get('title', 'N/A')
        app_logger_func(f"Error downloading {filename}. Check logs for details.")

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("600x400")

        # Style
        style = ttk.Style()
        style.theme_use('clam') # Using a theme that works well on macOS

        # Frame for URL input
        input_frame = ttk.LabelFrame(root, text="Enter YouTube URL(s)", padding=(10, 5))
        input_frame.pack(padx=10, pady=10, fill="x")

        self.url_label = ttk.Label(input_frame, text="YouTube URL(s) (comma-separated for multiple):")
        self.url_label.pack(side=tk.LEFT, padx=5)

        self.url_entry = ttk.Entry(input_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill="x", padx=5)

        # Frame for download options (initially just path)
        options_frame = ttk.LabelFrame(root, text="Download Options", padding=(10, 5))
        options_frame.pack(padx=10, pady=5, fill="x")

        self.path_label = ttk.Label(options_frame, text="Download Path:")
        self.path_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.download_path_var = tk.StringVar()
        self.download_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads")) # Default to ~/Downloads

        self.path_entry = ttk.Entry(options_frame, textvariable=self.download_path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, expand=True, fill="x", padx=5, pady=5)

        self.browse_button = ttk.Button(options_frame, text="Browse...", command=self.browse_download_path)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Download button
        self.download_button = ttk.Button(root, text="Download Videos", command=self.start_download_thread)
        self.download_button.pack(pady=10)

        # Status area
        status_frame = ttk.LabelFrame(root, text="Status", padding=(10, 5))
        status_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.status_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar for status_text
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text['yscrollcommand'] = scrollbar.set

    def browse_download_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_path_var.set(directory)

    def log_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks() # Ensure GUI updates

    def start_download_thread(self):
        urls_string = self.url_entry.get()
        if not urls_string:
            messagebox.showwarning("Input Error", "Please enter at least one YouTube URL.")
            return

        urls = [url.strip() for url in urls_string.split(',') if url.strip()]
        if not urls:
            messagebox.showwarning("Input Error", "No valid URLs provided.")
            return
        
        download_path = self.download_path_var.get()
        if not os.path.isdir(download_path):
            messagebox.showerror("Path Error", f"The download path '{download_path}' does not exist or is not a directory.")
            return

        self.download_button.config(state=tk.DISABLED)
        self.log_status(f"Starting download of {len(urls)} video(s)...")
        
        # Run download in a separate thread to keep GUI responsive
        download_thread = threading.Thread(target=self.download_videos, args=(urls, download_path), daemon=True)
        download_thread.start()

    def download_videos(self, urls, download_path):
        # Prepare yt-dlp options
        # The YtdlpLogger and ytdlp_progress_hook are defined globally in this script
        # and receive self.log_status as the app_logger_func argument.
        ffmpeg_executable_path = None
        # ffprobe_executable_path = None # yt-dlp usually finds ffprobe relative to ffmpeg

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Application is running as a PyInstaller bundle
            meipass_path = sys._MEIPASS
            self.log_status(f"INFO: Running as bundle. MEIPASS (bundle root): {meipass_path}")
            
            ffmpeg_name = 'ffmpeg'
            ffprobe_name = 'ffprobe' # yt-dlp expects this name

            potential_ffmpeg_path = os.path.join(meipass_path, ffmpeg_name)
            potential_ffprobe_path = os.path.join(meipass_path, ffprobe_name)

            self.log_status(f"INFO: Checking for bundled ffmpeg at: {potential_ffmpeg_path}")
            if os.path.exists(potential_ffmpeg_path):
                self.log_status(f"INFO: Found {ffmpeg_name} at {potential_ffmpeg_path}")
                try:
                    current_mode = os.stat(potential_ffmpeg_path).st_mode
                    if not (current_mode & stat.S_IXUSR):
                        self.log_status(f"INFO: Attempting to make {ffmpeg_name} executable...")
                        os.chmod(potential_ffmpeg_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    if os.access(potential_ffmpeg_path, os.X_OK):
                        ffmpeg_executable_path = potential_ffmpeg_path
                        self.log_status(f"INFO: {ffmpeg_name} is executable.")
                    else:
                        self.log_status(f"WARNING: {ffmpeg_name} at {potential_ffmpeg_path} is NOT executable even after chmod.")
                except Exception as e:
                    self.log_status(f"ERROR: Could not check/set permissions for {ffmpeg_name}: {e}")
            else:
                self.log_status(f"WARNING: Bundled {ffmpeg_name} NOT found at {potential_ffmpeg_path}")

            # Check for ffprobe as well, for logging, though yt-dlp mainly uses ffmpeg_location
            self.log_status(f"INFO: Checking for bundled ffprobe at: {potential_ffprobe_path}")
            if os.path.exists(potential_ffprobe_path):
                self.log_status(f"INFO: Found {ffprobe_name} at {potential_ffprobe_path}")
                try:
                    current_mode = os.stat(potential_ffprobe_path).st_mode
                    if not (current_mode & stat.S_IXUSR):
                        self.log_status(f"INFO: Attempting to make {ffprobe_name} executable...")
                        os.chmod(potential_ffprobe_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    if not os.access(potential_ffprobe_path, os.X_OK):
                         self.log_status(f"WARNING: {ffprobe_name} at {potential_ffprobe_path} is NOT executable even after chmod.")
                except Exception as e:
                    self.log_status(f"ERROR: Could not check/set permissions for {ffprobe_name}: {e}")
            else:
                self.log_status(f"WARNING: Bundled {ffprobe_name} NOT found at {potential_ffprobe_path}")
        else:
            self.log_status("INFO: Running as script. yt-dlp will search for ffmpeg/ffprobe in system PATH.")

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'logger': YtdlpLogger(self.log_status),
            'progress_hooks': [lambda d: ytdlp_progress_hook(d, self.log_status)],
            'noplaylist': False,
            'ignoreerrors': True,
            # 'verbose': True, # Uncomment for more detailed yt-dlp output
        }

        if ffmpeg_executable_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_executable_path
            self.log_status(f"INFO: Setting ffmpeg_location in yt-dlp options to: {ffmpeg_executable_path}")
        else:
            self.log_status("WARNING: ffmpeg_location not set. yt-dlp will rely on system PATH or internal fallbacks.")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for i, url_to_download in enumerate(urls):
                    self.log_status(f"--- Starting download for: {url_to_download} ({i+1}/{len(urls)}) ---")
                    try:
                        # The download method expects a list of URLs
                        ydl.download([url_to_download])
                        self.log_status(f"--- Finished processing: {url_to_download} ---")
                    except yt_dlp.utils.DownloadError as e:
                        # This exception is often caught by yt-dlp's own error handling and logger
                        self.log_status(f"DownloadError for {url_to_download}: {e}")
                    except Exception as e:
                        self.log_status(f"An unexpected error occurred with {url_to_download}: {str(e)}")
            
            self.log_status("All downloads attempted.")
            messagebox.showinfo("Download Process Complete", "All specified videos have been processed. Check status for details.")

        except Exception as e:
            # This would catch errors in yt_dlp.YoutubeDL instantiation itself
            self.log_status(f"An critical error occurred with yt-dlp setup: {str(e)}")
            messagebox.showerror("yt-dlp Error", f"A critical error occurred with yt-dlp: {str(e)}\nEnsure yt-dlp is correctly installed ('pip install -r requirements.txt').")
        finally:
            self.download_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
