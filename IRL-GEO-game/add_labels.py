import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

INPUT_DIR = Path(__file__).parent
OUTPUT_DIR = INPUT_DIR / "labeled"
OUTPUT_DIR.mkdir(exist_ok=True)

PADDING = 32
BADGE_PADDING_X = 36
BADGE_PADDING_Y = 22
CORNER_RADIUS = 18
FONT_COLOR = (255, 255, 255)
BADGE_COLOR = (20, 20, 20, 210)
BORDER_COLOR = (255, 255, 255, 120)

def get_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_rounded_rect(draw, xy, radius, fill, outline=None, outline_width=2):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill,
                            outline=outline, width=outline_width)

def add_label(img_path: Path):
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    label = img_path.stem
    font_size = max(48, min(80, h // 14))
    font = get_font(font_size)

    # Measure text
    dummy = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy)
    bbox = draw_dummy.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    badge_w = text_w + BADGE_PADDING_X * 2
    badge_h = text_h + BADGE_PADDING_Y * 2

    # Position: bottom-right corner
    bx1 = w - PADDING - badge_w
    by1 = h - PADDING - badge_h
    bx2 = w - PADDING
    by2 = h - PADDING

    # Draw overlay on a separate RGBA layer
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw_rounded_rect(draw, (bx1, by1, bx2, by2),
                      radius=CORNER_RADIUS,
                      fill=BADGE_COLOR,
                      outline=BORDER_COLOR,
                      outline_width=3)

    # Center text in badge
    tx = bx1 + BADGE_PADDING_X - bbox[0]
    ty = by1 + BADGE_PADDING_Y - bbox[1]
    draw.text((tx, ty), label, font=font, fill=FONT_COLOR)

    composite = Image.alpha_composite(img, overlay).convert("RGB")
    out_path = OUTPUT_DIR / img_path.name
    composite.save(out_path, quality=95)
    print(f"  {img_path.name} -> {out_path.name}")

images = sorted(INPUT_DIR.glob("*.jpeg")) + sorted(INPUT_DIR.glob("*.jpg")) + sorted(INPUT_DIR.glob("*.png"))
images = [p for p in images if p.parent == INPUT_DIR]  # skip output dir

print(f"Processing {len(images)} images...")
for img_path in images:
    add_label(img_path)
print(f"\nDone. Labeled images saved to: {OUTPUT_DIR}")
