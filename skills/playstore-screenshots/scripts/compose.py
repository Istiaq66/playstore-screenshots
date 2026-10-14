"""Captioned Play Store phone screenshots (1080x1920), same layout as
play-store-assets/js/render.js drawScreenshot: caption band on top, screen
inset with rounded top corners running off the bottom edge, soft shadow,
optional decor circle in the top-right corner.

usage: python compose.py spec.json
spec: {"out": dir, "font": ttf (optional, defaults to bundled Plus Jakarta Sans),
       "background": "#hex", "text": "#hex",
       "decor": "#hex" | null, "shots": [{"file": png, "caption": str, "name": str}]}
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SIDE = round(W * 0.0926)
BAND = round(H * 0.185)
RADIUS = round(W * 0.044)


def load_font(path, size):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([800])  # variable font: ExtraBold
    except Exception:
        pass
    return f


def width(font, s, tracking):
    return font.getlength(s) + tracking * max(len(s) - 1, 0)


def wrap_balanced(text, max_w, font, tracking):
    words = text.split()
    whole = ' '.join(words)
    if width(font, whole, tracking) <= max_w:
        return [whole]
    best = None
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        widest = max(width(font, a, tracking), width(font, b, tracking))
        if widest <= max_w and (best is None or widest < best[0]):
            best = (widest, [a, b])
    return best[1] if best else None


def fit(text, font_path):
    top = round(W * 0.07)
    for size in range(top, round(top * 0.6) - 1, -2):
        font = load_font(font_path, size)
        lines = wrap_balanced(text, W - SIDE * 2, font, -0.02 * size)
        if lines:
            return font, size, lines, True
    font = load_font(font_path, round(top * 0.6))
    return font, round(top * 0.6), [text], False


def draw_text(d, xy, s, font, fill, tracking):
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill, anchor='lm')
        x += font.getlength(ch) + tracking


def compose(spec, shot):
    img = Image.new('RGB', (W, H), spec['background'])
    d = ImageDraw.Draw(img)
    if spec.get('decor'):
        r = W * 0.065
        cx = W * 0.87
        d.ellipse((cx - r, -r, cx + r, r), fill=spec['decor'])

    font, size, lines, ok = fit(shot['caption'], spec['font'])
    lh = size * 1.1
    y0 = BAND / 2 - (len(lines) - 1) * lh / 2
    for i, line in enumerate(lines):
        draw_text(d, (SIDE, y0 + i * lh), line, font, spec['text'], -0.02 * size)

    screen = Image.open(shot['file']).convert('RGB')
    sw = W - SIDE * 2
    sh = round(sw * screen.height / screen.width)
    screen = screen.resize((sw, sh), Image.LANCZOS)
    box_h = max(sh, H - BAND)

    mask = Image.new('L', (sw, box_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, box_h + RADIUS), RADIUS, fill=255)

    shadow = Image.new('L', (W, H), 0)
    shadow.paste(mask, (SIDE, BAND - 10))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    img = Image.composite(Image.new('RGB', (W, H), '#000000'), img, shadow.point(lambda v: v * 0.3))

    frame = Image.new('RGB', (sw, box_h), '#ffffff')
    frame.paste(screen, (0, 0))
    img.paste(frame, (SIDE, BAND), mask)

    problems = []
    if not ok:
        problems.append('caption too long for two lines')
    elif size < round(W * 0.07) * 0.8:
        problems.append(f'caption shrunk to {size}px, shorten it')
    if screen.width < sw * 0.9:
        problems.append('screenshot narrow, will look soft')
    if BAND + sh < H - 2:
        problems.append('screenshot shorter than frame, white shows at bottom')
    return img, problems


def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    here = os.path.dirname(os.path.abspath(__file__))
    spec.setdefault('font', os.path.join(here, '..', 'assets', 'PlusJakartaSans-var.ttf'))
    os.makedirs(spec['out'], exist_ok=True)
    for i, shot in enumerate(spec['shots'], 1):
        img, problems = compose(spec, shot)
        name = shot.get('name') or f'{i:02d}'
        path = os.path.join(spec['out'], f'{name}.png')
        img.save(path, optimize=True)  # RGB, no alpha: Play-safe
        kb = os.path.getsize(path) // 1024
        print(f'{name}.png {img.size} {kb}KB', '; '.join(problems) or 'ok')


if __name__ == '__main__':
    main()
