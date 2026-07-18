# Montage the thrust key-pose renders (tools/thrust_keys.py) into the
# approval grid. Columns L->R = time (ready, drive, strike, recover);
# rows = FP (player) view, side view. Labeled, house style.
#   python3 tools/montage_thrust.py
from PIL import Image, ImageDraw, ImageFont
import os

SRC = '/mnt/c/tmp'
KEYS = ['1_ready', '2_drive', '3_strike', '4_recover']
VIEWS = [('fp', 'FP (player)'), ('side', 'side')]
CELL_W, CELL_H, PAD, HEAD = 640, 480, 6, 40
OUT = ['/home/khaled/Kore/thrust_pose_grid.jpg',
       '/mnt/c/Users/kmessai/Downloads/thrust_pose_grid.jpg']


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


W = PAD + len(KEYS) * (CELL_W + PAD)
H = HEAD + len(VIEWS) * (CELL_H + HEAD + PAD)
grid = Image.new('RGB', (W, H), (24, 26, 32))
draw = ImageDraw.Draw(grid)
f_big, f_small = font(26), font(20)
draw.text((PAD, 8), 'THRUST — key poses (wristed rig, in-line rapier grip, '
          '2-DOF wrist)', font=f_big, fill=(235, 230, 220))

for r, (view, vlabel) in enumerate(VIEWS):
    y = HEAD + r * (CELL_H + HEAD + PAD)
    for c, key in enumerate(KEYS):
        x = PAD + c * (CELL_W + PAD)
        img = Image.open(f'{SRC}/tk_{key}_{view}.png').resize(
            (CELL_W, CELL_H), Image.LANCZOS)
        grid.paste(img, (x, y + HEAD - PAD))
        label = f'{key[2:]} — {vlabel}'
        draw.text((x + 4, y + 6), label, font=f_small, fill=(200, 205, 215))

for path in OUT:
    grid.save(path, quality=92)
    print('wrote', path)
