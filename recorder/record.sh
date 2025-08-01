#!/bin/bash
STREAM_URL=$1
DURATION=10
OUTPUT="$(date +"%Y%m%d_%H%M%S").mp4"
ffmpeg -y -i "$STREAM_URL" -t "$DURATION" -c:v libx264 -c:a aac -movflags +faststart -profile:v main -pix_fmt yuv420p "$OUTPUT"
echo $OUTPUT

