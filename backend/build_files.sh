#!/bin/bash
# build_files.sh
echo "Installing system dependencies..."
apt-get update && apt-get install -y ffmpeg
