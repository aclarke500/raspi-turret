#!/usr/bin/env bash
set -euo pipefail

OUT="test.jpg"

pick_node() {
  for n in /dev/video*; do
    if v4l2-ctl -d "$n" --all 2>/dev/null | grep -q "Video Capture"; then
      echo "$n"; return 0
    fi
  done
  echo "No Video Capture node found" >&2; exit 1
}

DEV="${1:-$(pick_node)}"

# prefer mjpeg if the cam supports it
if v4l2-ctl -d "$DEV" --list-formats-ext | grep -q MJPG; then
  IN_FMT=mjpeg
else
  IN_FMT=yuyv422
fi

SIZE="${SIZE:-640x480}"
FPS="${FPS:-30}"

echo "Using $DEV ($IN_FMT $SIZE@$FPS)"
ffmpeg -hide_banner -loglevel error \
  -f v4l2 -input_format "$IN_FMT" -framerate "$FPS" -video_size "$SIZE" -i "$DEV" \
  -vf "select=gte(n\,10)" -vframes 1 -y "$OUT"

sync
[ -s "$OUT" ] && echo "Saved $OUT"
