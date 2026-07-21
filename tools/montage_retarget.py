# Montage the grip-retarget proof renders (tools/retarget_grip.py) into the
# approval grid: palm-side / FP / back-of-hand, labeled, house style.
#   python3 tools/montage_retarget.py
from PIL import Image, ImageDraw, ImageFont
import os

SRC = '/mnt/c/tmp'
SHOTS = [('palm', 'palm side — fingers on handle'),
         ('fp', 'FP (player)'),
         ('back', 'back of hand (downrange)')]
CELL_W, CELL_H, PAD, HEAD = 640, 480, 6, 44
OUT = ['/home/khaled/Kore/grip_retarget_grid.jpg',
       '/mnt/c/Users/kmessai/Downloads/grip_retarget_grid.jpg']


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


W = PAD + len(SHOTS) * (CELL_W + PAD)
H = HEAD + CELL_H + HEAD + PAD
grid = Image.new('RGB', (W, H), (24, 26, 32))
draw = ImageDraw.Draw(grid)
f_big, f_small = font(26), font(20)
draw.text((PAD, 8), "KHALED'S GRIP retargeted onto the constrained rig — "
          'radial parity exact, twist -> forearm roll +40.7', font=f_big,
          fill=(235, 230, 220))

for c, (shot, label) in enumerate(SHOTS):
    x = PAD + c * (CELL_W + PAD)
    img = Image.open(f'{SRC}/rg_{shot}.png').resize((CELL_W, CELL_H),
                                                    Image.LANCZOS)
    grid.paste(img, (x, HEAD + HEAD - PAD))
    draw.text((x + 4, HEAD + 6), label, font=f_small, fill=(200, 205, 215))

for path in OUT:
    grid.save(path, quality=92)
    print('wrote', path)
