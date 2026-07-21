# Montage the sword attack key-pose renders (tools/sword_attack_keys.py) into
# per-attack approval grids. Columns L->R = key order; rows = FP, side.
#   python3 tools/montage_attack_keys.py
from PIL import Image, ImageDraw, ImageFont
import os

SRC = '/mnt/c/tmp'
ATTACKS = {
    'light': (['1_ready', '2_drive', '3_strike', '4_recover'],
              'SWORD LIGHT — quick lunge (Khaled grip, side sword)'),
    'heavy_lr': (['1_ready', '2_windup', '3_sweep', '4_through', '5_recover'],
                 'SWORD HEAVY L->R — committed horizontal cut'),
    'heavy_rl': (['1_ready', '2_windup', '3_sweep', '4_through', '5_recover'],
                 'SWORD HEAVY R->L — committed horizontal cut'),
}
VIEWS = [('fp', 'FP (player)'), ('side', 'side')]
CELL_W, CELL_H, PAD, HEAD = 560, 420, 6, 40
OUT_DIRS = ['/home/khaled/Kore', '/mnt/c/Users/kmessai/Downloads']


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


for attack, (keys, title) in ATTACKS.items():
    W = PAD + len(keys) * (CELL_W + PAD)
    H = HEAD + len(VIEWS) * (CELL_H + HEAD + PAD)
    grid = Image.new('RGB', (W, H), (24, 26, 32))
    draw = ImageDraw.Draw(grid)
    f_big, f_small = font(26), font(20)
    draw.text((PAD, 8), title, font=f_big, fill=(235, 230, 220))
    for r, (view, vlabel) in enumerate(VIEWS):
        y = HEAD + r * (CELL_H + HEAD + PAD)
        for c, key in enumerate(keys):
            x = PAD + c * (CELL_W + PAD)
            img = Image.open(f'{SRC}/sk_{attack}_{key}_{view}.png').resize(
                (CELL_W, CELL_H), Image.LANCZOS)
            grid.paste(img, (x, y + HEAD - PAD))
            draw.text((x + 4, y + 6), f'{key[2:]} — {vlabel}', font=f_small,
                      fill=(200, 205, 215))
    for d in OUT_DIRS:
        path = f'{d}/sword_{attack}_keys_grid.jpg'
        grid.save(path, quality=92)
        print('wrote', path)
