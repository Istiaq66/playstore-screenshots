"""Side-by-side contact sheet at 1/3 scale (360x640 per screen) for cheap visual review.

usage: python sheet.py out.png in1.png [in2.png ...]
Prints each input's real size so a wrong capture size is caught early.
"""
import sys
from PIL import Image

ims = []
for p in sys.argv[2:]:
    im = Image.open(p).convert('RGB')
    print(p.replace('\\', '/').split('/')[-1], im.size)
    ims.append(im.resize((360, 640)))
sheet = Image.new('RGB', (370 * len(ims) - 10, 640), 'white')
for i, im in enumerate(ims):
    sheet.paste(im, (i * 370, 0))
sheet.save(sys.argv[1])
