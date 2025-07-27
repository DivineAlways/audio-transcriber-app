#!/bin/bash
# build_files.sh

set -e # Exit immediately if a command exits with a non-zero status.

echo "Installing ffmpeg static build"

# The /tmp directory is writable on Vercel
FFMPEG_DIR="/tmp/ffmpeg"
mkdir -p "$FFMPEG_DIR"

# Download and extract ffmpeg
# Using a direct link to a specific version for stability
curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-6.0-amd64-static.tar.xz" | tar -xJ -C "$FFMPEG_DIR" --strip-components=1

# Make ffmpeg executable
chmod +x "$FFMPEG_DIR/ffmpeg"

echo "ffmpeg static build installed in $FFMPEG_DIR"
