#!/bin/bash
# ============================================================
# Kore Animation Loop — Render + Grid Pipeline
#
# Usage:
#   ./run.sh              # defaults: walk animation
#   ./run.sh feel         # run the 'feel' animation
#   ./run.sh threat       # run the 'threat' animation
#   ./run.sh walk 30      # walk animation, 30fps grid sampling
#
# Steps:
#   1. Run Blender headlessly: import mesh, rig, animate, render
#   2. Convert image sequence to MP4 via ffmpeg
#   3. Generate review grids via vetinari_cli.py
#   4. Print grid paths for review
#
# After this runs, the AI reads the grid images and decides
# what to change in the animation script, then re-runs.
# ============================================================

set -e

# --- Configuration ---
ANIMATION="${1:-walk}"
GRID_FPS="${2:-10}"
GRID_CHUNK="${3:-16}"

BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
PIPELINE_SCRIPT='\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\loop\render_pipeline.py'

# Render output on Windows filesystem (Blender writes here)
RENDER_DIR_WIN="C:/Users/kmessai/Downloads/spider_render"
RENDER_DIR_WSL="/mnt/c/Users/kmessai/Downloads/spider_render"

# Final outputs on WSL filesystem
OUTPUT_DIR="/tmp/kore_output"
VIDEO_PATH="${OUTPUT_DIR}/animation.mp4"
GRID_DIR="${OUTPUT_DIR}/grids"

VETINARI_CLI="/home/khaled/stitcher/contentGeneration/vetinari_cli.py"

echo "============================================================"
echo "KORE ANIMATION LOOP"
echo "  Animation: ${ANIMATION}"
echo "  Grid FPS: ${GRID_FPS}, Chunk: ${GRID_CHUNK}"
echo "============================================================"

# --- Step 1: Blender headless render ---
echo ""
echo "[1/3] Running Blender headless render..."
echo "  This takes ~30-60 seconds..."

export KORE_ANIMATION="${ANIMATION}"
export KORE_RENDER_DIR="${RENDER_DIR_WIN}"
export KORE_FRAME_RATE="24"
export KORE_RESOLUTION="960x720"

"${BLENDER}" --background --python "${PIPELINE_SCRIPT}" 2>&1 | while IFS= read -r line; do
    # Filter out Blender noise, show progress
    if [[ "$line" == *"[1/6]"* ]] || [[ "$line" == *"[2/6]"* ]] || \
       [[ "$line" == *"[3/6]"* ]] || [[ "$line" == *"[4/6]"* ]] || \
       [[ "$line" == *"[5/6]"* ]] || [[ "$line" == *"[6/6]"* ]] || \
       [[ "$line" == *"COMPLETE"* ]] || [[ "$line" == *"Rendered"* ]] || \
       [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"Error"* ]]; then
        echo "  $line"
    fi
done

BLENDER_EXIT=${PIPESTATUS[0]}
if [ $BLENDER_EXIT -ne 0 ]; then
    echo "ERROR: Blender exited with code $BLENDER_EXIT"
    echo "Full output above. Check for Python errors."
    exit 1
fi

# Count rendered frames
FRAME_COUNT=$(ls "${RENDER_DIR_WSL}"/frame_*.png 2>/dev/null | wc -l)
echo "  Frames rendered: ${FRAME_COUNT}"

if [ "$FRAME_COUNT" -eq 0 ]; then
    echo "ERROR: No frames rendered. Check Blender output."
    exit 1
fi

# --- Step 2: ffmpeg to MP4 ---
echo ""
echo "[2/3] Converting image sequence to MP4..."

mkdir -p "${OUTPUT_DIR}"

# ffmpeg: PNG sequence → MP4
# The frames are named frame_0001.png, frame_0002.png, etc.
ffmpeg -y -framerate 24 \
    -i "${RENDER_DIR_WSL}/frame_%04d.png" \
    -c:v libx264 -pix_fmt yuv420p \
    -crf 18 -preset fast \
    "${VIDEO_PATH}" 2>&1 | tail -3

if [ -f "${VIDEO_PATH}" ]; then
    SIZE=$(du -h "${VIDEO_PATH}" | cut -f1)
    echo "  Video: ${VIDEO_PATH} (${SIZE})"
else
    echo "ERROR: ffmpeg failed to create video."
    exit 1
fi

# --- Step 3: Grid extraction ---
echo ""
echo "[3/3] Extracting review grids..."

rm -rf "${GRID_DIR}"
mkdir -p "${GRID_DIR}"

conda run -n stitcher python "${VETINARI_CLI}" grids \
    "${VIDEO_PATH}" \
    --fps "${GRID_FPS}" \
    --chunk-size "${GRID_CHUNK}" \
    --output "${GRID_DIR}" 2>&1 | tail -5

# The grid tool creates a 'grids' subdirectory — flatten it
if [ -d "${GRID_DIR}/grids" ]; then
    mv "${GRID_DIR}"/grids/* "${GRID_DIR}/" 2>/dev/null
    rmdir "${GRID_DIR}/grids" 2>/dev/null
fi

GRID_COUNT=$(ls "${GRID_DIR}"/*.jpg "${GRID_DIR}"/*.png 2>/dev/null | wc -l)
echo "  Grids generated: ${GRID_COUNT}"

# --- Done ---
echo ""
echo "============================================================"
echo "PIPELINE COMPLETE"
echo ""
echo "Review grids:"
ls -1 "${GRID_DIR}"/*.jpg "${GRID_DIR}"/*.png 2>/dev/null | head -20
echo ""
echo "Video: ${VIDEO_PATH}"
echo ""
echo "To review: read the grid images with the Read tool."
echo "To iterate: edit the animation script, then re-run this."
echo "============================================================"
