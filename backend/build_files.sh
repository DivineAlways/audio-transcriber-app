#!/bin/bash
# build_files.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "Installing ffmpeg static build"

# The /tmp directory is writable on Vercel
TMP_DIR="/tmp"
FFMPEG_DIR="$TMP_DIR/ffmpeg"
FFMPEG_ARCHIVE="$TMP_DIR/ffmpeg.tar.xz"
mkdir -p "$FFMPEG_DIR"

# Use a stable URL for the latest release
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

echo "Downloading ffmpeg from $FFMPEG_URL..."
# Download the file first, then extract
curl -L -o "$FFMPEG_ARCHIVE" "$FFMPEG_URL"

echo "Download complete. Extracting archive..."
# Extract the archive from the file
tar -xJf "$FFMPEG_ARCHIVE" -C "$FFMPEG_DIR" --strip-components=1

# Make ffmpeg executable
chmod +x "$FFMPEG_DIR/ffmpeg"

echo "ffmpeg static build installed in $FFMPEG_DIR"
# Clean up the downloaded archive
rm "$FFMPEG_ARCHIVE"
