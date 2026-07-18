#!/usr/bin/env python3
"""Generic montage: <prefix>_<name>_NN.png frames (from /mnt/c/tmp) into a
labeled 4x3 grid. Same format as montage_casts.py, parametrized prefix.

Usage: python3 tools/montage_grid.py <prefix> <name> [<name> ...]
e.g.   python3 tools/montage_grid.py sword sword_light sword_parry
Saves <name>_grid.jpg to ~/Kore and the Windows Downloads dir.
"""
import json
import sys
import os
from PIL import Image, ImageDraw, ImageFont

SRC = '/mnt/c/tmp'
DESTS = ['/home/khaled/Kore', '/mnt/c/Users/kmessai/Downloads']
COLS, ROWS = 4, 3
BAR = 26

def font(size=15):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def montage(prefix, name):
    with open(f'{SRC}/{prefix}_{name}_manifest.json') as fh:
        man = json.load(fh)
    samples = man['samples']
    cells = [Image.open(f'{SRC}/{prefix}_{name}_{s["index"]:02d}.png').convert('RGB')
             for s in samples]
    w, h = cells[0].size
    fnt, big = font(15), font(20)
    grid = Image.new('RGB', (COLS * w, ROWS * (h + BAR) + 34), (10, 10, 12))
    d = ImageDraw.Draw(grid)
    d.text((10, 7), f'{name}  —  {man["frames"]} frames @ {man["fps"]} fps '
           f'({(man["frames"]-1)/man["fps"]:.2f}s)  —  time reads L→R, T→B',
           fill=(235, 235, 235), font=big)
    for i, (img, s) in enumerate(zip(cells, samples)):
        r, c = divmod(i, COLS)
        x, y = c * w, 34 + r * (h + BAR)
        grid.paste(img, (x, y + BAR))
        d.rectangle([x, y, x + w, y + BAR], fill=(24, 24, 28))
        d.text((x + 8, y + 5),
               f'f{s["frame"]:>2}  {s["time"]:.2f}s   {s["phase"]}',
               fill=(255, 220, 120), font=fnt)
    grid.thumbnail((2200, 10000), Image.LANCZOS)
    for dest in DESTS:
        out = f'{dest}/{name}_grid.jpg'
        grid.save(out, quality=88)
        print('saved', out)

prefix = sys.argv[1]
for nm in sys.argv[2:]:
    montage(prefix, nm)
