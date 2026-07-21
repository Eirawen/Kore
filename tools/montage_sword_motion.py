# Montage the sword motion-pass sample renders (tools/animate_sword_attacks.py)
# into per-attack review grids: 2 rows x 6 cols, L->R T->B = time, labeled
# with frame / seconds / phase from the manifest.
#   python3 tools/montage_sword_motion.py
from PIL import Image, ImageDraw, ImageFont
import json, os

SRC = '/mnt/c/tmp'
ATTACKS = {
    'light': 'SWORD LIGHT — lunge motion pass (gather-HOLD-snap, pronated strike)',
    'heavy_lr': 'SWORD HEAVY L->R — motion pass (coil-HOLD-sweep-through)',
    'heavy_rl': 'SWORD HEAVY R->L — motion pass (coil-HOLD-sweep-through)',
}
COLS, ROWS = 6, 2
CELL_W, CELL_H, PAD, HEAD = 480, 360, 6, 42
OUT_DIRS = ['/home/khaled/Kore', '/mnt/c/Users/kmessai/Downloads']


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


for attack, title in ATTACKS.items():
    man_path = f'{SRC}/swm_{attack}_manifest.json'
    if not os.path.exists(man_path):
        print('skip', attack, '(no manifest)')
        continue
    man = json.load(open(man_path))
    samples = man['samples']
    W = PAD + COLS * (CELL_W + PAD)
    H = HEAD + ROWS * (CELL_H + HEAD + PAD)
    grid = Image.new('RGB', (W, H), (24, 26, 32))
    draw = ImageDraw.Draw(grid)
    f_big, f_small = font(26), font(19)
    draw.text((PAD, 8), '%s   (%d f @ %d fps = %.2f s)' % (
        title, man['frames'], man['fps'], (man['frames'] - 1) / man['fps']),
        font=f_big, fill=(235, 230, 220))
    for i, s in enumerate(samples[:COLS * ROWS]):
        r, c = divmod(i, COLS)
        x = PAD + c * (CELL_W + PAD)
        y = HEAD + r * (CELL_H + HEAD + PAD)
        img = Image.open(f'{SRC}/swm_{attack}_{s["index"]:02d}.png').resize(
            (CELL_W, CELL_H), Image.LANCZOS)
        grid.paste(img, (x, y + HEAD - PAD))
        draw.text((x + 4, y + 6), 'f%02d  %.2fs  %s' % (
            s['frame'], s['time'], s['phase']), font=f_small,
            fill=(200, 205, 215))
    for d in OUT_DIRS:
        path = f'{d}/sword_{attack}_motion_grid.jpg'
        grid.save(path, quality=92)
        print('wrote', path)
