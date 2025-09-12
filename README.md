# 🎵 KHInsider FLAC Downloader

A Python script to download full albums in high-quality FLAC format from [KHInsider](https://downloads.khinsider.com). It automatically parses album pages, resolves the obfuscated download links, and downloads all tracks into a dedicated folder for the album.

## ✨ Features

-   **High-Quality Audio**: Downloads albums in lossless FLAC format.
-   **Command-Line Interface**: Simple and easy to use with a single command.
-   **Smart Parsing**: Automatically handles the site's obfuscated links to extract track download links without making extra requests.
-   **Organized Downloads**: Creates a new directory for each album to keep your downloads tidy.

## ⚙️ Installation

1.  **Clone the repository:**
	```bash
	git clone https://github.com/Hyphonical/KHInsiderGrabber.git
	cd KHInsiderGrabber
	```

2.  **Install dependencies:**
	Make sure you have Python 3 installed. Then, install the required packages using `pip`.
	```bash
	pip install -r requirements.txt
	```

## 🚀 Usage

Run the script from your terminal and provide the full URL of the album you wish to download.

**Syntax:**
```bash
python Main.py <album_url>
```