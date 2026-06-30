#!/bin/bash
# ============================================================
# Kore Animation Iterate — Single cycle of the animation loop
#
# Usage from the AI:
#   bash /home/khaled/Kore/tools/loop/iterate.sh [animation] [resolution]
#
# Examples:
#   bash /home/khaled/Kore/tools/loop/iterate.sh walk 960x720
#   bash /home/khaled/Kore/tools/loop/iterate.sh feel 480x360
#   bash /home/khaled/Kore/tools/loop/iterate.sh threat
#
# After this completes, read the grid images at:
#   /tmp/kore_output/grids/grid_*.jpg
#
# Iteration workflow:
#   1. Edit animation script (e.g., tools/animate_walk.py)
#   2. Run this script
#   3. Read the grids, evaluate the animation
#   4. Go back to step 1 or commit if satisfied
# ============================================================

set -euo pipefail

ANIMATION="${1:-walk}"
RESOLUTION="${2:-960x720}"
CAMERA="${3:-3/4}"

BLENDER="/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
PIPELINE_SCRIPT='\\wsl.localhost\Ubuntu\home\khaled\Kore\tools\loop\render_pipeline.py'

RENDER_DIR_WIN="C:/Users/kmessai/Downloads/spider_render"
RENDER_DIR_WSL="/mnt/c/Users/kmessai/Downloads/spider_render"

OUTPUT_DIR="/tmp/kore_output"
VIDEO_PATH="${OUTPUT_DIR}/animation.mp4"
GRID_DIR="${OUTPUT_DIR}/grids"

VETINARI_CLI="/home/khaled/stitcher/contentGeneration/vetinari_cli.py"

echo "--- Kore iterate: ${ANIMATION} @ ${RESOLUTION} ---"

# Clean previous output
rm -f "${RENDER_DIR_WSL}"/frame_*.png
rm -rf "${GRID_DIR}"
mkdir -p "${OUTPUT_DIR}" "${GRID_DIR}"

# Step 1: Blender render
echo "[render] Starting Blender headless..."
# Write config to a file that Blender can read (env vars unreliable across WSL→Windows)
CONFIG_FILE="/home/khaled/Kore/tools/loop/.render_config"
cat > "${CONFIG_FILE}" <<CONF
KORE_ANIMATION=${ANIMATION}
KORE_RENDER_DIR=${RENDER_DIR_WIN}
KORE_FRAME_RATE=24
KORE_RESOLUTION=${RESOLUTION}
KORE_CAMERA=${CAMERA}
CONF

export KORE_ANIMATION="${ANIMATION}"
export KORE_RENDER_DIR="${RENDER_DIR_WIN}"
export KORE_FRAME_RATE="24"
export KORE_RESOLUTION="${RESOLUTION}"
export KORE_CAMERA="${CAMERA}"

"${BLENDER}" --background --python "${PIPELINE_SCRIPT}" 2>&1 | \
    grep -E '\[.*\/6\]|Rendered|ERROR|Error|COMPLETE' || true

FRAME_COUNT=$(ls "${RENDER_DIR_WSL}"/frame_*.png 2>/dev/null | wc -l)
echo "[render] ${FRAME_COUNT} frames rendered"

if [ "$FRAME_COUNT" -eq 0 ]; then
    echo "ERROR: No frames rendered!"
    exit 1
fi

# Step 2: ffmpeg
echo "[ffmpeg] Converting to MP4..."
ffmpeg -y -framerate 24 \
    -i "${RENDER_DIR_WSL}/frame_%04d.png" \
    -c:v libx264 -pix_fmt yuv420p \
    -crf 18 -preset fast \
    "${VIDEO_PATH}" 2>/dev/null

echo "[ffmpeg] $(du -h "${VIDEO_PATH}" | cut -f1)"

# Step 3: Grid
echo "[grid] Extracting review grids..."
conda run -n stitcher python "${VETINARI_CLI}" grids \
    "${VIDEO_PATH}" \
    --fps 10 \
    --chunk-size 16 \
    --output "${GRID_DIR}" 2>&1 | grep -E "grid_|saved" || true

# Flatten nested grids dir
if [ -d "${GRID_DIR}/grids" ]; then
    mv "${GRID_DIR}"/grids/* "${GRID_DIR}/" 2>/dev/null
    rmdir "${GRID_DIR}/grids" 2>/dev/null
fi

echo ""
echo "--- Done ---"
echo "Grids at: ${GRID_DIR}/"
ls -1 "${GRID_DIR}"/grid_*.jpg 2>/dev/null || ls -1 "${GRID_DIR}"/grid_*.png 2>/dev/null || echo "(no grids found)"
echo ""
echo "Read these with the Read tool to review the animation."
