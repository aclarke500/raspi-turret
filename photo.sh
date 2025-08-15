# fswebcam -r 640x480 ./test.jpg #!/usr/bin/env bash
set -euo pipefail
DEV=${1:-/dev/video0}
OUT="test.jpg"

if v4l2-ctl -d "$DEV" --list-formats-ext | grep -q MJPG; then
  ffmpeg -hide_banner -loglevel error \
    -f v4l2 -input_format mjpeg -framerate 30 -video_size 640x480 -i "$DEV" \
    -frames:v 1 -y "$OUT"
else
  ffmpeg -hide_banner -loglevel error \
    -f v4l2 -input_format yuyv422 -framerate 30 -video_size 640x480 -i "$DEV" \
    -frames:v 1 -y "$OUT"
fi

sync
[ -s "$OUT" ]
