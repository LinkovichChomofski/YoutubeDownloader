import streamlit as st
import os
import time
import yt_dlp
import stat
import sys
from pathlib import Path
import tempfile
import zipfile
from io import BytesIO
import json
from datetime import datetime
import queue
import threading
import hashlib
import subprocess

# Global queue for thread-safe communication
PROGRESS_QUEUE = queue.Queue()
# Global flag to stop downloads
STOP_DOWNLOAD = threading.Event()
# Global debug list (thread-safe)
DEBUG_INFO = []
DEBUG_LOCK = threading.Lock()
# File-based completion flag
COMPLETION_FLAG_FILE = "/tmp/streamlit_download_complete.flag"

# Initialize session state
if 'download_status' not in st.session_state:
    st.session_state.download_status = []
if 'is_downloading' not in st.session_state:
    st.session_state.is_downloading = False
if 'download_complete' not in st.session_state:
    st.session_state.download_complete = False
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []
if 'current_download' not in st.session_state:
    st.session_state.current_download = {}
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = {}
if 'total_videos' not in st.session_state:
    st.session_state.total_videos = 0
if 'completed_videos' not in st.session_state:
    st.session_state.completed_videos = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

def add_debug_info(message):
    """Add debug information with timestamp - thread safe"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    debug_msg = f"[{timestamp}] DEBUG: {message}"
    
    # Thread-safe debug logging
    with DEBUG_LOCK:
        DEBUG_INFO.append(debug_msg)
        # Keep only last 100 debug messages to prevent memory issues
        if len(DEBUG_INFO) > 100:
            DEBUG_INFO.pop(0)
    
    # Send to queue for UI update
    try:
        PROGRESS_QUEUE.put(('debug', debug_msg), block=False)
    except:
        pass
    
    # Also print to console
    print(debug_msg)

def get_debug_info():
    """Get debug information thread-safely"""
    with DEBUG_LOCK:
        return DEBUG_INFO.copy()

def clear_debug_info():
    """Clear debug information thread-safely"""
    with DEBUG_LOCK:
        DEBUG_INFO.clear()

def add_status_message(message):
    """Add a timestamped status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    st.session_state.download_status.append(full_message)
    st.session_state.last_update = datetime.now()

def monitor_file_changes(download_path, filename_pattern=None):
    """Monitor file changes in download directory"""
    try:
        files_before = set(os.listdir(download_path))
        add_debug_info(f"Files in directory before: {len(files_before)} files")
        
        for f in files_before:
            path = os.path.join(download_path, f)
            if os.path.isfile(path):
                size = os.path.getsize(path)
                add_debug_info(f"Existing file: {f} ({size} bytes)")
        
        return files_before
    except Exception as e:
        add_debug_info(f"Error monitoring directory: {e}")
        return set()

def check_file_integrity(filepath):
    """Check if a file appears to be a valid video"""
    try:
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        size = os.path.getsize(filepath)
        if size < 1024:
            return False, f"File too small: {size} bytes"
        
        # Check file header for common video formats
        with open(filepath, 'rb') as f:
            header = f.read(12)
            
        # MP4 file signature check
        if b'ftyp' in header:
            return True, f"Valid MP4 file ({size} bytes)"
        elif header.startswith(b'\x00\x00\x00'):
            return True, f"Possible MP4 file ({size} bytes)"
        else:
            return False, f"Unknown format, header: {header.hex()}"
            
    except Exception as e:
        return False, f"Error checking file: {e}"

class StreamlitLogger:
    """Logger for yt-dlp that works with Streamlit"""
    def debug(self, msg):
        if not msg.startswith('[debug] '):
            msg = f"[debug] {msg.strip()}"
        add_debug_info(f"yt-dlp: {msg}")
        try:
            PROGRESS_QUEUE.put(('log', msg), block=False)
        except:
            pass

    def info(self, msg):
        add_debug_info(f"yt-dlp INFO: {msg.strip()}")
        try:
            PROGRESS_QUEUE.put(('log', f"ℹ️ {msg.strip()}"), block=False)
        except:
            pass

    def warning(self, msg):
        add_debug_info(f"yt-dlp WARNING: {msg.strip()}")
        try:
            PROGRESS_QUEUE.put(('log', f"⚠️ WARNING: {msg.strip()}"), block=False)
        except:
            pass

    def error(self, msg):
        add_debug_info(f"yt-dlp ERROR: {msg.strip()}")
        try:
            PROGRESS_QUEUE.put(('log', f"❌ ERROR: {msg.strip()}"), block=False)
        except:
            pass

def ytdlp_progress_hook(d):
    """Enhanced progress hook for yt-dlp downloads with detailed debugging"""
    try:
        add_debug_info(f"Progress hook called with status: {d.get('status', 'unknown')}")
        add_debug_info(f"Progress data keys: {list(d.keys())}")
        
        # Log all progress data for debugging
        for key, value in d.items():
            if key not in ['info_dict']:  # Skip large nested data
                add_debug_info(f"Progress {key}: {value}")
        
        # Put progress data in queue for main thread to process
        PROGRESS_QUEUE.put(('progress', d), block=False)
    except Exception as e:
        add_debug_info(f"Progress hook error: {e}")
        print(f"Progress hook error: {e}")

def process_progress_queue():
    """Process messages from the background download thread"""
    processed_any = False
    completion_detected = False
    
    while True:
        try:
            item = PROGRESS_QUEUE.get_nowait()
            processed_any = True
            
            if isinstance(item, tuple) and len(item) == 2:
                msg_type, data = item
                
                if msg_type == 'log':
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.download_status.append(f"[{timestamp}] {data}")
                    st.session_state.last_update = datetime.now()
                
                elif msg_type == 'complete':
                    # Handle download completion
                    add_debug_info("Completion signal received from download thread")
                    print("🎉 COMPLETION SIGNAL RECEIVED - Setting completion flags")
                    completion_detected = True
                    st.session_state.is_downloading = False
                    st.session_state.download_complete = True
                    st.session_state.current_download = {}
                    STOP_DOWNLOAD.clear()  # Reset stop flag
                    
                    # Final status message
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.download_status.append(f"[{timestamp}] 🎉 **DOWNLOAD SESSION COMPLETED**")
                    st.session_state.last_update = datetime.now()
                    
                    # Force immediate UI refresh
                    print(f"🎉 UI STATE: is_downloading={st.session_state.is_downloading}, download_complete={st.session_state.download_complete}")
                
                elif msg_type == 'progress':
                    d = data
                    if d.get('status') == 'downloading':
                        # Extract progress information
                        filename = d.get('filename') or d.get('info_dict', {}).get('title', 'Unknown')
                        filename = os.path.basename(filename)
                        
                        # Get progress metrics
                        downloaded_bytes = d.get('downloaded_bytes', 0)
                        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        speed = d.get('speed', 0)
                        eta = d.get('eta', 0)
                        
                        # Calculate percentage
                        if total_bytes > 0:
                            percent = (downloaded_bytes / total_bytes) * 100
                        else:
                            percent = 0
                        
                        # Format file sizes
                        def format_bytes(bytes_val):
                            if bytes_val is None or bytes_val == 0:
                                return "0 B"
                            for unit in ['B', 'KB', 'MB', 'GB']:
                                if bytes_val < 1024.0:
                                    return f"{bytes_val:.1f} {unit}"
                                bytes_val /= 1024.0
                            return f"{bytes_val:.1f} TB"
                        
                        # Format speed
                        speed_str = format_bytes(speed) + "/s" if speed else "0 B/s"
                        
                        # Format ETA
                        if eta:
                            eta_str = f"{eta//60:02d}:{eta%60:02d}"
                        else:
                            eta_str = "--:--"
                        
                        # Update session state with current download info
                        st.session_state.current_download = {
                            'filename': filename,
                            'percent': percent,
                            'downloaded': format_bytes(downloaded_bytes),
                            'total': format_bytes(total_bytes),
                            'speed': speed_str,
                            'eta': eta_str,
                            'status': 'downloading',
                            'last_update': datetime.now()
                        }
                        
                        # Store progress for this specific file
                        st.session_state.download_progress[filename] = {
                            'percent': percent,
                            'downloaded': downloaded_bytes,
                            'total': total_bytes,
                            'speed': speed,
                            'status': 'downloading'
                        }
                        
                        st.session_state.last_update = datetime.now()
                        
                        # Add periodic progress messages (every 5%)
                        if percent > 0 and int(percent) % 5 == 0 and int(percent) != getattr(st.session_state, 'last_percent', -1):
                            st.session_state.last_percent = int(percent)
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            st.session_state.download_status.append(f"[{timestamp}] 🔄 {filename}: {percent:.1f}% ({format_bytes(downloaded_bytes)}/{format_bytes(total_bytes)}) at {speed_str}")
                    
                    elif d.get('status') == 'finished':
                        filename = d.get('filename') or d.get('info_dict', {}).get('title', 'Unknown')
                        full_filename = filename
                        filename = os.path.basename(filename)
                        
                        # Update progress
                        st.session_state.download_progress[filename] = {
                            'percent': 100,
                            'status': 'completed'
                        }
                        
                        # Add to completed files
                        st.session_state.downloaded_files.append(full_filename)
                        st.session_state.completed_videos += 1
                        
                        # Update current download status
                        st.session_state.current_download = {
                            'filename': filename,
                            'percent': 100,
                            'status': 'completed'
                        }
                        
                        # Log completion
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.download_status.append(f"[{timestamp}] ✅ Completed: {filename}")
                        st.session_state.last_update = datetime.now()
                    
                    elif d.get('status') == 'preparing':
                        filename = d.get('filename') or d.get('info_dict', {}).get('title', 'Unknown')
                        filename = os.path.basename(filename)
                        
                        st.session_state.current_download = {
                            'filename': filename,
                            'status': 'preparing'
                        }
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.download_status.append(f"[{timestamp}] 🔄 Preparing: {filename}")
                        st.session_state.last_update = datetime.now()
                
                elif msg_type == 'debug':
                    # Debug messages are already handled by add_debug_info
                    pass
                
        except queue.Empty:
            break
        except Exception as e:
            add_debug_info(f"Error processing queue: {e}")
            break
    
    return processed_any, completion_detected

def setup_ffmpeg():
    """Setup ffmpeg path if bundled"""
    ffmpeg_executable_path = None
    
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        bundle_dir = sys._MEIPASS
        
        # Platform-specific ffmpeg naming
        if sys.platform == "win32":
            ffmpeg_name = "ffmpeg.exe"
            ffprobe_name = "ffprobe.exe"
        else:
            ffmpeg_name = "ffmpeg"
            ffprobe_name = "ffprobe"

        potential_ffmpeg_path = os.path.join(bundle_dir, ffmpeg_name)
        potential_ffprobe_path = os.path.join(bundle_dir, ffprobe_name)

        if os.path.exists(potential_ffmpeg_path):
            try:
                current_mode = os.stat(potential_ffmpeg_path).st_mode
                if not (current_mode & stat.S_IXUSR):
                    os.chmod(potential_ffmpeg_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                ffmpeg_executable_path = potential_ffmpeg_path
            except Exception as e:
                st.session_state.download_status.append(f"ERROR: Could not set permissions for {ffmpeg_name}: {e}")
    
    return ffmpeg_executable_path

def download_videos(urls, download_path):
    """Download videos using yt-dlp with extensive debugging - NO SESSION STATE ACCESS"""
    try:
        add_debug_info(f"Starting download_videos function")
        add_debug_info(f"URLs to download: {urls}")
        add_debug_info(f"Download path: {download_path}")
        
        # Monitor initial directory state
        initial_files = monitor_file_changes(download_path)
        
        # Simple yt-dlp configuration for debugging
        ydl_opts = {
            'format': 'best[height<=480]/best',  # Very conservative for testing
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'logger': StreamlitLogger(),
            'progress_hooks': [ytdlp_progress_hook],
            'ignoreerrors': True,
            'retries': 1,  # Only 1 retry for faster debugging
            'socket_timeout': 15,  # Shorter timeout
            'noplaylist': False,
            'extract_flat': False,
            'continue_dl': True,
            'overwrites': False,
            'verbose': True,
            'quiet': False,
            'no_warnings': False,
        }
        
        add_debug_info(f"yt-dlp options configured")
        
        # Setup ffmpeg
        ffmpeg_executable_path = setup_ffmpeg()
        if ffmpeg_executable_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_executable_path
            add_debug_info(f"ffmpeg configured at: {ffmpeg_executable_path}")
            PROGRESS_QUEUE.put(('log', f"🔧 Using ffmpeg: {ffmpeg_executable_path}"), block=False)
        else:
            add_debug_info("ffmpeg not found")
            PROGRESS_QUEUE.put(('log', f"⚠️ Warning: ffmpeg not found"), block=False)
        
        PROGRESS_QUEUE.put(('log', f"🚀 **Starting download of {len(urls)} video(s)**"), block=False)
        
        # Create yt-dlp instance
        add_debug_info("Creating yt-dlp instance")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            add_debug_info("yt-dlp instance created successfully")
            
            for i, url_to_download in enumerate(urls):
                if STOP_DOWNLOAD.is_set():
                    add_debug_info("Download stopped by user")
                    break
                    
                add_debug_info(f"Processing URL {i+1}/{len(urls)}: {url_to_download}")
                PROGRESS_QUEUE.put(('log', f"📺 **Video {i+1}/{len(urls)}**: Starting {url_to_download}"), block=False)
                
                try:
                    add_debug_info("Starting yt-dlp.download()")
                    download_start_time = datetime.now()
                    
                    # Try download with timeout mechanism
                    ydl.download([url_to_download])
                    
                    download_end_time = datetime.now()
                    download_duration = (download_end_time - download_start_time).total_seconds()
                    add_debug_info(f"Download completed in {download_duration:.2f} seconds")
                    
                    PROGRESS_QUEUE.put(('log', f"✅ Completed: {url_to_download}"), block=False)
                    
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    add_debug_info(f"yt-dlp DownloadError: {error_msg}")
                    PROGRESS_QUEUE.put(('log', f"❌ Download error: {error_msg}"), block=False)
                    
                except Exception as e:
                    add_debug_info(f"Unexpected error during download: {str(e)}")
                    PROGRESS_QUEUE.put(('log', f"❌ Unexpected error: {str(e)}"), block=False)
        
        # Final file analysis
        add_debug_info("Performing final file analysis...")
        try:
            final_files = set(os.listdir(download_path))
            all_new_files = final_files - initial_files
            add_debug_info(f"All files created during session: {list(all_new_files)}")
            
            valid_downloads = []
            for filename in all_new_files:
                if filename.endswith('.mp4'):
                    file_path = os.path.join(download_path, filename)
                    is_valid, message = check_file_integrity(file_path)
                    add_debug_info(f"Final check for {filename}: {message}")
                    if is_valid:
                        valid_downloads.append(filename)
            
            success_count = len(valid_downloads)
            total_count = len(urls)
            
            add_debug_info(f"Final summary: {success_count}/{total_count} successful downloads")
            
            if success_count > 0:
                PROGRESS_QUEUE.put(('log', f"🎉 **{success_count}/{total_count} video(s) downloaded successfully!**"), block=False)
                PROGRESS_QUEUE.put(('log', f"📁 Downloaded files: {', '.join(valid_downloads)}"), block=False)
            else:
                PROGRESS_QUEUE.put(('log', f"❌ **No videos were downloaded successfully**"), block=False)
                
        except Exception as e:
            add_debug_info(f"Error during file analysis: {e}")
        
    except Exception as e:
        add_debug_info(f"Critical error in download_videos: {str(e)}")
        PROGRESS_QUEUE.put(('log', f"❌ Critical error: {str(e)}"), block=False)
    finally:
        add_debug_info("download_videos function completed")
        # Mark download as complete - send multiple times to ensure delivery
        try:
            PROGRESS_QUEUE.put(('complete', None), block=False)
            PROGRESS_QUEUE.put(('complete', None), block=False)  # Send twice for reliability
            print("🎉 COMPLETION SIGNAL SENT TO QUEUE")
        except Exception as e:
            print(f"❌ Error sending completion signal: {e}")
            add_debug_info(f"Error sending completion signal: {e}")
        
        # Create file-based completion flag as backup
        try:
            with open(COMPLETION_FLAG_FILE, 'w') as f:
                f.write(f"completed_{datetime.now().isoformat()}")
            print("📁 COMPLETION FLAG FILE CREATED")
        except Exception as e:
            print(f"❌ Error creating completion flag file: {e}")

def create_zip_download():
    """Create a zip file of all downloaded videos for download"""
    if not st.session_state.downloaded_files:
        return None
        
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in st.session_state.downloaded_files:
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="YouTube Video Downloader",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube Video Downloader")
    st.markdown("---")
    
    # Process any pending messages from download thread
    processed_any, completion_detected = process_progress_queue()
    
    # Check for file-based completion flag
    if not completion_detected and st.session_state.is_downloading:
        if os.path.exists(COMPLETION_FLAG_FILE):
            print("📁 COMPLETION FLAG FILE DETECTED - Download complete!")
            completion_detected = True
            try:
                os.remove(COMPLETION_FLAG_FILE)
                print("📁 Completion flag file removed")
            except:
                pass
    
    # Fallback completion detection - if no activity for 3 seconds and we think we're downloading
    if st.session_state.is_downloading and st.session_state.last_update:
        time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
        if time_since_update > 3.0:  # 3 seconds of no activity
            print(f"🕐 FALLBACK: No activity for {time_since_update:.1f}s, assuming download complete")
            completion_detected = True
            st.session_state.download_status.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🕐 Download completed (timeout detection)")
    
    if completion_detected:
        print("🚀 MAIN UI: Completion detected, updating state")
        st.session_state.is_downloading = False
        st.session_state.download_complete = True
        st.session_state.current_download = {}
        STOP_DOWNLOAD.clear()  # Reset stop flag
        print(f"🚀 MAIN UI STATE UPDATED: is_downloading={st.session_state.is_downloading}")
        # Force immediate rerun to update UI
        st.rerun()
    
    # Sidebar for settings and debugging
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Download path selection
        download_path = st.text_input(
            "Download Path",
            value=os.path.join(os.path.expanduser("~"), "Downloads"),
            help="Enter the path where videos should be downloaded"
        )
        
        # Create directory if it doesn't exist
        if download_path and not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
                st.success(f"✅ Created directory: {download_path}")
            except Exception as e:
                st.error(f"❌ Cannot create directory: {e}")
                download_path = tempfile.gettempdir()
                st.warning(f"Using temporary directory: {download_path}")
        
        st.info(f"📁 Current download path: `{download_path}`")
        
        # Debug mode toggle
        debug_mode = st.checkbox("🐛 Debug Mode", value=True, help="Show detailed debugging information")
        
        # Stop download button
        if st.session_state.is_downloading:
            if st.button("🛑 Stop Download", type="secondary"):
                STOP_DOWNLOAD.set()
                st.warning("Stopping download...")
                st.rerun()
        
        # Download Statistics
        if st.session_state.is_downloading or st.session_state.download_complete:
            st.markdown("---")
            st.subheader("📊 Download Stats")
            
            # Show download status indicator
            if st.session_state.is_downloading:
                st.error("🔴 **DOWNLOADING ACTIVE**")
                if st.session_state.last_update:
                    time_diff = (datetime.now() - st.session_state.last_update).total_seconds()
                    st.caption(f"Last update: {time_diff:.1f}s ago")
            
            # Overall progress
            if st.session_state.total_videos > 0:
                overall_progress = st.session_state.completed_videos / st.session_state.total_videos
                st.progress(overall_progress, f"Overall: {st.session_state.completed_videos}/{st.session_state.total_videos}")
            
            # Current file progress
            if st.session_state.current_download:
                current = st.session_state.current_download
                if current.get('status') == 'downloading':
                    st.progress(current.get('percent', 0) / 100, f"Current: {current.get('percent', 0):.1f}%")
                    st.caption(f"📁 {current.get('filename', 'Unknown')}")
                    st.caption(f"🔽 {current.get('downloaded', '0 B')} / {current.get('total', 'Unknown')}")
                    st.caption(f"🚀 {current.get('speed', '0 B/s')} | ⏱️ ETA: {current.get('eta', '--:--')}")
                elif current.get('status') == 'preparing':
                    st.info("🔄 Preparing download...")
                    st.caption(f"📺 {current.get('filename', 'Unknown')}")
        
        # Debug information
        if debug_mode:
            st.markdown("---")
            st.subheader("🐛 Debug Info")
            
            # Get debug info from global thread-safe storage
            debug_info = get_debug_info()
            if debug_info:
                debug_text = "\n".join(debug_info[-50:])  # Last 50 debug messages
                st.text_area(
                    "Debug Log",
                    value=debug_text,
                    height=200,
                    disabled=True,
                    key="debug_log"
                )
            else:
                st.info("No debug information yet")
            
            if st.button("Clear Debug Log"):
                clear_debug_info()
                st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Enter YouTube URL(s)")
        
        # URL input
        urls_input = st.text_area(
            "YouTube URLs",
            height=100,
            placeholder="Enter YouTube URL(s) here, one per line or comma-separated",
            help="You can enter multiple URLs separated by commas or new lines"
        )
        
        # Parse URLs
        urls = []
        if urls_input:
            # Split by both commas and newlines, then clean up
            raw_urls = [url.strip() for url in urls_input.replace(',', '\n').split('\n')]
            # More flexible URL validation - check for common YouTube patterns
            urls = []
            invalid_urls = []
            
            for url in raw_urls:
                if url:  # Skip empty strings
                    # Check for various YouTube URL patterns
                    if any(pattern in url.lower() for pattern in [
                        'youtube.com/watch',
                        'youtu.be/',
                        'youtube.com/playlist',
                        'youtube.com/channel',
                        'youtube.com/c/',
                        'youtube.com/@',
                        'm.youtube.com'
                    ]):
                        urls.append(url)
                    else:
                        invalid_urls.append(url)
        
        # Show URL validation results
        if urls_input:
            if urls:
                st.success(f"✅ Found {len(urls)} valid YouTube URL(s)")
                with st.expander("📋 URLs to download"):
                    for i, url in enumerate(urls, 1):
                        st.write(f"{i}. {url}")
            
            if invalid_urls:
                st.warning(f"⚠️ Found {len(invalid_urls)} invalid URL(s)")
                with st.expander("❌ Invalid URLs (not recognized as YouTube)"):
                    for i, url in enumerate(invalid_urls, 1):
                        st.write(f"{i}. {url}")
                st.info("💡 **Tip**: Make sure URLs contain 'youtube.com/watch', 'youtu.be/', or other valid YouTube patterns")
        
        # Download button
        download_disabled = not urls or st.session_state.is_downloading
        
        # Show why download might be disabled
        if urls_input and not urls:
            st.error("❌ **Download disabled**: No valid YouTube URLs found")
        elif st.session_state.is_downloading:
            st.info("⏳ **Download in progress**: Please wait for current download to complete")
        elif not urls_input:
            st.info("📝 **Enter YouTube URLs above to enable download**")
        
        if st.button(
            "🚀 Download Videos" if not st.session_state.is_downloading else "⏳ Downloading...",
            disabled=download_disabled,
            type="primary",
            use_container_width=True
        ):
            if urls and download_path:
                # Reset state
                st.session_state.is_downloading = True
                st.session_state.download_status = []
                st.session_state.downloaded_files = []
                st.session_state.download_complete = False
                st.session_state.current_download = {}
                st.session_state.download_progress = {}
                st.session_state.total_videos = len(urls)
                st.session_state.completed_videos = 0
                
                # Clear debug info and queue
                clear_debug_info()
                while not PROGRESS_QUEUE.empty():
                    try:
                        PROGRESS_QUEUE.get_nowait()
                    except queue.Empty:
                        break
                
                STOP_DOWNLOAD.clear()
                
                add_debug_info(f"Starting new download session with {len(urls)} URLs")
                add_debug_info(f"Download path: {download_path}")
                
                # Remove any existing completion flag
                try:
                    if os.path.exists(COMPLETION_FLAG_FILE):
                        os.remove(COMPLETION_FLAG_FILE)
                        print("📁 Removed existing completion flag file")
                except:
                    pass
                
                # Start download in a thread
                download_thread = threading.Thread(
                    target=download_videos,
                    args=(urls, download_path),
                    daemon=True,
                    name="DownloadThread"
                )
                download_thread.start()
                add_debug_info(f"Download thread started: {download_thread.name}")
                # Force immediate refresh
                st.rerun()
    
    with col2:
        st.header("📊 Download Status")
        
        # Show active download indicator
        if st.session_state.is_downloading:
            st.error("🔴 **DOWNLOAD IN PROGRESS**")
            if st.session_state.current_download:
                current = st.session_state.current_download
                if current.get('status') == 'downloading':
                    st.info("⏳ **Currently Downloading**")
                    
                    # Progress bar
                    progress_val = current.get('percent', 0) / 100
                    st.progress(progress_val, f"{current.get('percent', 0):.1f}%")
                    
                    # File info
                    st.caption(f"📁 **File**: {current.get('filename', 'Unknown')}")
                    st.caption(f"📊 **Progress**: {current.get('downloaded', '0 B')} / {current.get('total', 'Unknown')}")
                    st.caption(f"🚀 **Speed**: {current.get('speed', '0 B/s')} | ⏱️ **ETA**: {current.get('eta', '--:--')}")
                elif current.get('status') == 'preparing':
                    st.info("🔄 **Preparing Download**")
                    st.caption(f"📺 Getting info for: {current.get('filename', 'Unknown')}")
                
                st.markdown("---")
        
        # Status log
        if st.session_state.download_status:
            # Show recent status messages (last 20)
            recent_status = st.session_state.download_status[-20:]
            
            # Create scrollable text area for status
            status_text = "\n".join(recent_status)
            st.text_area(
                "Status Log",
                value=status_text,
                height=300,
                disabled=True,
                key="status_log"
            )
        
        # Individual file progress (if downloading multiple files)
        if st.session_state.download_progress:
            st.markdown("---")
            st.subheader("📁 File Progress")
            
            for filename, progress in st.session_state.download_progress.items():
                status_icon = "✅" if progress['status'] == 'completed' else "❌" if progress['status'] == 'error' else "⏳"
                st.caption(f"{status_icon} {filename}")
                if progress['status'] == 'downloading':
                    st.progress(progress['percent'] / 100, f"{progress['percent']:.1f}%")
                elif progress['status'] == 'completed':
                    st.progress(1.0, "100% ✅")
                else:  # error
                    st.progress(0.0, "Failed ❌")
        
        # Download completed actions
        if st.session_state.download_complete and st.session_state.downloaded_files:
            st.markdown("---")
            success_count = len(st.session_state.downloaded_files)
            st.success(f"🎉 Downloaded {success_count} file(s)")
            
            # Show downloaded files
            with st.expander("📁 Downloaded Files"):
                for file_path in st.session_state.downloaded_files:
                    filename = os.path.basename(file_path)
                    file_size = ""
                    if os.path.exists(file_path):
                        size_bytes = os.path.getsize(file_path)
                        for unit in ['B', 'KB', 'MB', 'GB']:
                            if size_bytes < 1024.0:
                                file_size = f" ({size_bytes:.1f} {unit})"
                                break
                            size_bytes /= 1024.0
                    st.write(f"✅ {filename}{file_size}")
            
            # Create zip download
            if st.button("📦 Download All as ZIP", type="secondary"):
                zip_data = create_zip_download()
                if zip_data:
                    st.download_button(
                        label="⬇️ Download ZIP File",
                        data=zip_data,
                        file_name="youtube_downloads.zip",
                        mime="application/zip"
                    )
    
    # Auto-refresh while downloading
    if st.session_state.is_downloading:
        time.sleep(0.5)  # Slower refresh for stability
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "💡 **Tips:** "
        "• Enter multiple URLs separated by commas or new lines "
        "• Videos are downloaded in MP4 format with best quality "
        "• Watch real-time progress in the status panel "
        "• Use Debug Mode for detailed troubleshooting "
        "• Use Stop Download button if needed"
    )

if __name__ == "__main__":
    main()
