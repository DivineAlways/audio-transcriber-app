#!/bin/bash
# build_files.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "Installing ffmpeg static build into the function bundle"

# Create a bin directory in the root of the build environment
# This directory will be included in the serverless function package.
BIN_DIR="bin"
mkdir -p "$BIN_DIR"

FFMPEG_ARCHIVE="/tmp/ffmpeg.tar.xz"

# Use a stable URL for the latest release
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

echo "Downloading ffmpeg from $FFMPEG_URL..."
# Download the file first, then extract
curl -L -o "$FFMPEG_ARCHIVE" "$FFMPEG_URL"

echo "Download complete. Extracting archive into $BIN_DIR..."
# Extract the archive, but only pull out the ffmpeg and ffprobe binaries
tar -xJf "$FFMPEG_ARCHIVE" --strip-components=1 -C "$BIN_DIR" ffmpeg-release-amd64-static/ffmpeg ffmpeg-release-amd64-static/ffprobe

# Make ffmpeg and ffprobe executable
chmod +x "$BIN_DIR/ffmpeg"
chmod +x "$BIN_DIR/ffprobe"

echo "ffmpeg and ffprobe are now in the $BIN_DIR directory."
# Clean up the downloaded archive
rm "$FFMPEG_ARCHIVE"

echo "Build script finished."
