#!/bin/bash
# build_files.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "Installing ffmpeg static build into the function bundle"

# --- Configuration ---
# Directory to place the final binaries
BIN_DIR="bin"
mkdir -p "$BIN_DIR"

# Temporary directories for download and extraction
TMP_DIR="/tmp"
FFMPEG_ARCHIVE="$TMP_DIR/ffmpeg.tar.xz"
EXTRACT_DIR="$TMP_DIR/ffmpeg_extracted"
mkdir -p "$EXTRACT_DIR"

# Use a stable URL for the latest release
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

# --- Execution ---
echo "Downloading ffmpeg from $FFMPEG_URL..."
curl -L -o "$FFMPEG_ARCHIVE" "$FFMPEG_URL"

echo "Download complete. Extracting full archive to temporary directory..."
tar -xJf "$FFMPEG_ARCHIVE" -C "$EXTRACT_DIR" --strip-components=1

echo "Searching for ffmpeg and ffprobe binaries..."
FFMPEG_BIN=$(find "$EXTRACT_DIR" -type f -name "ffmpeg")
FFPROBE_BIN=$(find "$EXTRACT_DIR" -type f -name "ffprobe")

if [ -z "$FFMPEG_BIN" ] || [ -z "$FFPROBE_BIN" ]; then
    echo "Error: Could not find ffmpeg or ffprobe binaries in the extracted archive."
    exit 1
fi

echo "Found binaries. Moving them to $BIN_DIR"
mv "$FFMPEG_BIN" "$BIN_DIR/"
mv "$FFPROBE_BIN" "$BIN_DIR/"

# Make the binaries executable
chmod +x "$BIN_DIR/ffmpeg"
chmod +x "$BIN_DIR/ffprobe"

echo "ffmpeg and ffprobe are now in the $BIN_DIR directory."

# --- Cleanup ---
echo "Cleaning up temporary files..."
rm "$FFMPEG_ARCHIVE"
rm -rf "$EXTRACT_DIR"

# Create a dummy output directory to satisfy the Vercel static builder
echo "Creating dummy output directory for Vercel..."
mkdir -p public
touch public/placeholder.txt

echo "Build script finished successfully."
