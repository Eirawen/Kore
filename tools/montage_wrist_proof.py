# Montage the wrist-surgery proof renders into three labeled grids.
from PIL import Image, ImageDraw, ImageFont
import os

SRC = '/mnt/c/tmp'
DESTS = ['/home/khaled/Kore', '/mnt/c/Users/kmessai/Downloads']

try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
except Exception:
    FONT = FONT_S = ImageFont.load_default()


def cell(path, label):
    im = Image.open(os.path.join(SRC, path)).convert('RGB')
    d = ImageDraw.Draw(im)
    tw = d.textlength(label, font=FONT_S)
    d.rectangle([8, 8, 8 + tw + 16, 44], fill=(0, 0, 0))
    d.text((16, 12), label, fill=(255, 220, 120), font=FONT_S)
    return im


def grid(cells, cols, title, out_name):
    w, h = cells[0].size
    rows = (len(cells) + cols - 1) // cols
    TH = 56
    g = Image.new('RGB', (w * cols + 4 * (cols - 1),
                          TH + h * rows + 4 * (rows - 1)), (24, 24, 28))
    d = ImageDraw.Draw(g)
    d.text((14, 12), title, fill=(240, 240, 240), font=FONT)
    for i, c in enumerate(cells):
        g.paste(c, ((i % cols) * (w + 4), TH + (i // cols) * (h + 4)))
    for dest in DESTS:
        p = os.path.join(dest, out_name)
        g.save(p, quality=90)
        print('saved', p)


grid([cell('wp_old_rest_tight.png', 'OLD rig - rest (tight)'),
      cell('wp_new_rest_tight.png', 'NEW rig - rest (tight)'),
      cell('wp_old_rest_wide.png',  'OLD rig - rest (wide)'),
      cell('wp_new_rest_wide.png',  'NEW rig - rest (wide)')],
     2, 'REST PARITY - wrist split must not change the rest pose (they match)',
     'wrist_parity_grid.jpg')

grid([cell('wp_new_rest_tight.png',    'rest'),
      cell('wp_new_tilt_flex_neg40.png', 'hand flex -40 (extend, palm out)'),
      cell('wp_new_tilt_flex_pos40.png', 'hand flex +40 (curl in)'),
      cell('wp_new_tilt_dev_neg30.png',  'hand deviation -30'),
      cell('wp_new_tilt_dev_pos30.png',  'hand deviation +30')],
     3, 'ANTI-EGG - hand bone tilts, forearm stub stays put (was: whole lump rotated)',
     'wrist_antiegg_grid.jpg')

grid([cell('wp_new_pil_000.png', 'grip at rest: blade PERP to forearm (old rig max)'),
      cell('wp_new_pil_050.png', 'hand rotated 50%'),
      cell('wp_new_pil_100.png', 'POINT-IN-LINE: blade along forearm'),
      cell('wp_new_pil_100_side.png', 'point-in-line, side view (clean wrist)')],
     2, 'POINT-IN-LINE - sword parented to the hand BONE; the lunge the old rig could not do',
     'wrist_pointinline_grid.jpg')
