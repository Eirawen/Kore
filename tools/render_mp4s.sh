#!/usr/bin/env bash
# Render every frame for all first-person animations and encode to MP4.
# Casts are re-rendered post chirality-fix + air/fire polish (old mp4s were stale).
set -u
BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
BLEND='\\wsl.localhost\Ubuntu/home/khaled/Kore/cgtrader_hand.blend'
UNC='\\wsl.localhost\Ubuntu/home/khaled/Kore/tools'
TMP=/mnt/c/tmp
OUT=/mnt/c/Users/kmessai/Downloads
FPS=60
mkdir -p "$TMP" "$OUT"

CASTS="air_strike water_strike fire_strike earth_strike"
SWORDS="sword_light sword_heavy sword_thrust sword_guard sword_parry"
KNIVES="knife_throw_blade_first knife_throw_handle_first"

render_group () {  # $1=script  $2=names
  local script="$1"; shift
  local names="$*"
  echo "=== render $script : $names ==="
  # clear stale full-sequence frames for these names
  for n in $names; do rm -f "$TMP/${n}_"[0-9][0-9][0-9][0-9].png; done
  "$BLENDER" --background "$BLEND" --python "$UNC/$script" -- $names --full 2>&1 \
    | grep -iE "rendered full|error|traceback|exception" | tail -20
}

encode () {  # $1=name
  local n="$1"
  local first
  first=$(ls "$TMP/${n}_"[0-9][0-9][0-9][0-9].png 2>/dev/null | head -1)
  if [ -z "$first" ]; then echo "!! no frames for $n — skipping"; return 1; fi
  # detect starting frame number for ffmpeg -start_number
  local start
  start=$(basename "$first" | sed -E "s/^${n}_0*([0-9]+)\.png/\1/")
  ffmpeg -y -loglevel error -framerate $FPS -start_number "$start" \
    -i "$TMP/${n}_%04d.png" -pix_fmt yuv420p -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" \
    "$OUT/${n}.mp4" \
    && echo "  -> ${n}.mp4  ($(ls "$TMP/${n}_"[0-9][0-9][0-9][0-9].png | wc -l) frames)"
}

render_group animate_casts.py  $CASTS
render_group animate_sword.py  $SWORDS
render_group animate_knife.py  $KNIVES

echo "=== encoding ==="
for n in $CASTS $SWORDS $KNIVES; do encode "$n"; done

echo "=== DONE — mp4s in $OUT ==="
ls -la --time-style=+%H:%M "$OUT"/*.mp4 2>/dev/null | grep -E "$(echo "$CASTS $SWORDS $KNIVES" | tr ' ' '|')"
