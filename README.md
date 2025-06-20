# YouTube Video Downloader

This repository contains two versions of a YouTube video downloader:

1. **Desktop App (macOS)** - Built with Python and Tkinter
2. **Web App** - Built with Streamlit for browser-based access

## 🌐 Streamlit Web App

The modern, web-based version with advanced features:

- **Multi-URL support** with real-time progress tracking
- **Thread-safe architecture** with robust completion detection
- **Beautiful UI** with progress bars, download speed, and ETA
- **Advanced debugging** and error handling
- **Custom download paths** and ZIP export

### Quick Start (Web App)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run streamlit_app.py
```

Then open your browser to `http://localhost:8501`

---

## 🖥️ Desktop App (macOS)

The original desktop application built with Python and Tkinter to download YouTube videos using `yt-dlp`.

### Features

- Download single or multiple YouTube videos (comma-separated URLs).
- Choose a custom download directory.
- View download progress and status messages.

### Prerequisites

- Python 3 (usually pre-installed on macOS, or can be installed from [python.org](https://www.python.org/))
- `pip` (Python package installer, usually comes with Python)
- `yt-dlp` (command-line program to download videos from YouTube and other sites)
- **`ffmpeg` (Recommended for best format compatibility):** While `yt-dlp` can handle many downloads, `ffmpeg` is often needed for merging video and audio streams, especially when targeting specific formats like MP4. You can install it via Homebrew:
  ```bash
  brew install ffmpeg
  ```

### Setup

1.  **Clone or download this repository/code.**

2.  **Navigate to the application directory in your terminal:**
    ```bash
    cd path/to/Youtube-Downloader
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install dependencies:**
    This will install `yt-dlp` if you don't have it, or ensure you have a compatible version.
    ```bash
    pip install -r requirements.txt
    ```
    *Alternatively, if you prefer to install `yt-dlp` globally or manage it yourself, you can do so via pip (`pip install yt-dlp`) or Homebrew (`brew install yt-dlp`). The application will try to use the `yt-dlp` command available in your system's PATH. Similarly, ensure `ffmpeg` is in your PATH if installed manually.* 

### Running the Desktop Application

1.  **Ensure your virtual environment is activated** (if you created one):
    ```bash
    source venv/bin/activate 
    ```

2.  **Run the Python script:**
    ```bash
    python3 youtube_downloader.py
    ```

### How to Use (Desktop App)

1.  Launch the application.
2.  Enter one or more YouTube video URLs in the input field. If entering multiple URLs, separate them with commas (e.g., `https://www.youtube.com/watch?v=VIDEO_ID_1, https://www.youtube.com/watch?v=VIDEO_ID_2`).
3.  By default, videos will be saved to your `Downloads` folder. You can click "Browse..." to select a different download directory.
4.  Click the "Download Videos" button.
5.  The status area will show the progress of the downloads.

## Troubleshooting

-   **`yt-dlp` issues:** If you encounter issues related to `yt-dlp` (e.g., it can't download a video), ensure it's up to date (`pip install --upgrade yt-dlp`). Sometimes YouTube changes its site structure, requiring an update to `yt-dlp`.
-   **`ffmpeg` not found (for some conversions/merges):** If `yt-dlp` (used as a library) reports it needs `ffmpeg` for a specific operation and can't find it, ensure `ffmpeg` is installed (e.g., `brew install ffmpeg`) and that its location is in your system's PATH.
-   **Permissions:** Ensure the application has write permissions for the chosen download directory.

## Building a Standalone macOS Application (.app)

To create a standalone `.app` bundle that can be run on other Macs without needing a Python installation or manual dependency setup, you can use `PyInstaller`.

1.  **Ensure `PyInstaller` is installed:**
    If you haven't already, install it (it's included in `requirements.txt`):
    ```bash
    pip install -r requirements.txt 
    ```

2.  **Navigate to the application directory in your terminal.**

3.  **Run `PyInstaller`:**
    The following command will create a `.app` bundle in a `dist` folder, bundling `ffmpeg` and `ffprobe`:
    ```bash
    pyinstaller --noconfirm --windowed --name "YouTubeDownloader" \
    --add-binary "/opt/homebrew/bin/ffmpeg:." \
    --add-binary "/opt/homebrew/bin/ffprobe:." \
    --icon="path/to/your/icon.icns" \
    youtube_downloader.py
    ```
    -   `--windowed`: Prevents a terminal window from appearing when the app runs.
    -   `--name "YouTubeDownloader"`: Sets the name of the output `.app` file.
    -   `--add-binary "/opt/homebrew/bin/ffmpeg:."`: Bundles the `ffmpeg` executable into the app. Replace `/opt/homebrew/bin/ffmpeg` if your path is different. The `:.` part means copy it to the root directory within the app bundle.
    -   `--add-binary "/opt/homebrew/bin/ffprobe:."`: Bundles the `ffprobe` executable. Replace `/opt/homebrew/bin/ffprobe` if your path is different.
    -   `--icon="path/to/your/icon.icns"`: (Optional) Specify a path to an `.icns` file to use as the application icon. If you don't have one, you can omit this or create one.
    -   `youtube_downloader.py`: The main script.

    **Important Notes for `PyInstaller`:**
    *   **`yt-dlp` and `tkinter`:** Because we are using `yt-dlp` as a direct Python import and `tkinter` is part of the standard library (once `python-tk` is installed for your Python), `PyInstaller` should be able to find and bundle them correctly.
    *   **Bundled `ffmpeg`/`ffprobe`:** By using `--add-binary`, `ffmpeg` and `ffprobe` are now included within your `.app` bundle. `yt-dlp` (when used as a library) should be able to detect and use these bundled versions, making your application more self-contained. The application will look for these in the same directory as the main executable within the bundle.

4.  **Locate the App:**
    The standalone application (`YouTubeDownloader.app`) will be in the `dist` subdirectory created by `PyInstaller`.

This process bundles your Python script and its Python dependencies into a distributable application.

## License

Open source project - feel free to contribute and improve!
