# YouTube Downloader - Streamlit Web App

A modern web interface for downloading YouTube videos using Streamlit and yt-dlp.

## Features

- 🎯 **Simple Web Interface**: Clean, user-friendly Streamlit interface
- 📺 **Multiple URL Support**: Download multiple videos at once
- 📁 **Custom Download Path**: Choose where to save your videos
- 📊 **Real-time Progress**: Live status updates during downloads
- 📦 **Batch Download**: Download all files as a ZIP archive
- 🔧 **Error Handling**: Robust error handling and logging
- 🎬 **High Quality**: Downloads best available MP4 format

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Streamlit App**:
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Open Your Browser**: 
   - The app will automatically open at `http://localhost:8501`

## Usage

1. **Enter YouTube URLs**: 
   - Paste one or multiple YouTube URLs in the text area
   - Separate multiple URLs with commas or new lines

2. **Set Download Path** (Optional):
   - Use the sidebar to specify a custom download directory
   - Default is your Downloads folder

3. **Start Download**:
   - Click "🚀 Download Videos" to begin
   - Monitor progress in the status panel

4. **Download Files**:
   - Individual files are saved to your specified directory
   - Use "📦 Download All as ZIP" for easy bulk download

## Supported URLs

- Standard YouTube videos: `https://www.youtube.com/watch?v=...`
- YouTube Shorts: `https://www.youtube.com/shorts/...`
- Short URLs: `https://youtu.be/...`
- Playlists: `https://www.youtube.com/playlist?list=...`

## Technical Details

- **Backend**: yt-dlp library for video downloading
- **Frontend**: Streamlit for web interface
- **Format**: Downloads best quality MP4 with audio
- **Threading**: Non-blocking downloads with real-time updates

## Comparison with Desktop App

| Feature | Desktop (Tkinter) | Web (Streamlit) |
|---------|------------------|-----------------|
| Interface | Native GUI | Web Browser |
| Installation | Standalone executable | Python + Browser |
| Accessibility | Local only | Web accessible |
| Updates | Manual | Live refresh |
| File Management | Direct file access | ZIP download option |

## Deployment Options

### Local Development
```bash
streamlit run streamlit_app.py
```

### Production Deployment
- **Streamlit Cloud**: Connect your GitHub repo
- **Heroku**: Use provided `Procfile`
- **Docker**: Create containerized deployment
- **Local Network**: Use `--server.address 0.0.0.0` for network access

## Environment Variables

- `STREAMLIT_SERVER_PORT`: Custom port (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Custom address (default: localhost)

## Troubleshooting

### Common Issues:

1. **"No module named 'streamlit'"**
   ```bash
   pip install streamlit
   ```

2. **ffmpeg not found**
   - Install ffmpeg: `brew install ffmpeg` (macOS) or system equivalent
   - The app will work without ffmpeg but with limited format options

3. **Download fails**
   - Check internet connection
   - Verify URL is accessible
   - Check download path permissions

### Support

- Check the status log for detailed error messages
- Ensure you have write permissions to the download directory
- Verify YouTube URLs are valid and accessible

## License

Same as the original YouTube Downloader project.

# 📺 YouTube Video Downloader - Streamlit App

A powerful, user-friendly YouTube video downloader built with Streamlit and yt-dlp. Download single videos, playlists, or multiple URLs with real-time progress tracking and detailed debugging information.

## ✨ Features

- **🎯 Multi-URL Support**: Download multiple videos by entering URLs separated by commas or new lines
- **📁 Custom Download Path**: Choose where to save your downloaded videos  
- **📊 Real-time Progress**: Live progress bars, download speed, and ETA for each video
- **🔄 Robust Downloads**: Built-in retry logic, network timeout handling, and resume capability
- **🐛 Advanced Debugging**: Comprehensive logging and debugging mode for troubleshooting
- **📦 Batch Download**: Download all videos as a convenient ZIP file
- **🛑 Download Control**: Stop downloads in progress safely
- **✅ File Validation**: Automatic integrity checking of downloaded files

## 🚀 Quick Start

1. **Enter YouTube URLs** in the text area (supports various formats):
   - Standard: `https://www.youtube.com/watch?v=VIDEO_ID`
   - Short: `https://youtu.be/VIDEO_ID`
   - Playlists: `https://www.youtube.com/playlist?list=PLAYLIST_ID`
   - Channels: `https://www.youtube.com/channel/CHANNEL_ID`

2. **Select Download Path** (optional - defaults to Downloads folder)

3. **Click "Download Videos"** and watch real-time progress

4. **Download ZIP** of all videos when complete (optional)

## 🔧 Technical Features

### **Thread-Safe Architecture**
- Background download threads with queue-based communication
- No UI blocking during downloads
- Proper thread cleanup and error handling

### **Triple-Layer Completion Detection**
- Queue-based signals (primary)
- File-based flags (secondary)  
- Timeout-based fallback (tertiary)
- Ensures UI always recognizes download completion

### **Robust Error Handling**
- Network timeout protection
- Partial download recovery
- File integrity validation
- Detailed error reporting

### **Advanced Progress Tracking**
- Per-file progress with speed and ETA
- Overall session progress
- Real-time status updates every 0.5 seconds
- Download statistics and metrics

## 🛠️ Installation & Development

### Prerequisites
- Python 3.11+
- ffmpeg (for video processing)

### Local Development
```bash
# Clone the repository
git clone <your-repo-url>
cd Youtube\ Downloader

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

### Deployment
This app is configured for deployment on Streamlit Community Cloud:
- `streamlit_app.py` - Main application file
- `requirements.txt` - Python dependencies
- `netlify.toml` - Deployment configuration

## 📋 Supported Formats

- **Input**: All YouTube video/playlist/channel URLs
- **Output**: MP4 format (up to 720p for reliability)
- **Quality**: Automatically selects best available quality within limits

## 🐛 Debugging Mode

Enable **Debug Mode** in the sidebar to see:
- Detailed download progress logs
- File system monitoring
- yt-dlp internal messages
- Network status and errors
- Thread communication status

## ⚙️ Configuration

The app uses conservative settings for maximum reliability:
- **Format**: Best MP4 ≤720p resolution
- **Retries**: 1 retry per download for faster debugging
- **Timeout**: 15-second network timeout
- **Chunks**: 1MB download chunks for progress monitoring

## 🔒 Privacy & Security

- **No data storage**: Downloads are temporary and not stored on servers
- **Local processing**: All video processing happens client-side
- **No tracking**: No user data collection or analytics

## 🆘 Troubleshooting

### Common Issues:
1. **"Invalid URL"**: Ensure URLs contain valid YouTube patterns
2. **"Download stuck"**: Check debug mode for detailed error information  
3. **"File corrupted"**: Network issues - try downloading again
4. **"ffmpeg not found"**: Install ffmpeg for video processing

### Debug Tips:
- Enable Debug Mode for detailed logs
- Check console output for technical details
- Use Stop Download button if needed
- Try individual URLs if batch download fails

## 📄 License

Open source project - feel free to contribute and improve!

## 🤝 Contributing

Issues and pull requests welcome! Areas for improvement:
- Additional video formats support
- Enhanced error recovery
- UI/UX improvements
- Performance optimizations

---

**Built with ❤️ using Streamlit and yt-dlp**
