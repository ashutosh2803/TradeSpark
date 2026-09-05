"""Generate Trade Spark PWA PNG icons from a vector-style draw."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "icons"
OUT.mkdir(exist_ok=True)

BG = (11, 14, 20, 255)
CYAN = (0, 188, 229, 255)
BLUE = (41, 98, 255, 255)

SIZES = [16, 32, 48, 72, 96, 128, 144, 152, 180, 192, 256, 384, 512]


def draw_mark(size: int, *, maskable: bool = False) -> Image.Image:
    scale = 8
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    inset = int(canvas * (0.18 if maskable else 0.0))
    box = [inset, inset, canvas - 1 - inset, canvas - 1 - inset]
    radius = int((box[2] - box[0]) * 0.22)
    draw.rounded_rectangle(box, radius=radius, fill=BG)

    pad = int((box[2] - box[0]) * 0.18)
    left, top, right, bottom = box[0] + pad, box[1] + pad, box[2] - pad, box[3] - pad
    width = right - left
    height = bottom - top

    def pt(x: float, y: float) -> tuple[int, int]:
        return (int(left + x * width), int(top + y * height))

    stroke = max(scale * 2, int(canvas * 0.055))
    chart = [pt(0.02, 0.78), pt(0.32, 0.42), pt(0.52, 0.58), pt(0.96, 0.08)]
    draw.line(chart, fill=CYAN, width=stroke, joint="curve")
    for p in chart:
        r = stroke // 2
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=CYAN)

    tip = pt(0.96, 0.08)
    arm = int(width * 0.18)
    draw.line([tip, (tip[0], tip[1] + arm)], fill=BLUE, width=stroke)
    draw.line([tip, (tip[0] - arm, tip[1])], fill=BLUE, width=stroke)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    ico_frames = []
    for size in SIZES:
        icon = draw_mark(size)
        icon.save(OUT / f"icon-{size}.png", optimize=True)
        if size in (16, 32, 48):
            ico_frames.append(icon)
        if size in (192, 512):
            draw_mark(size, maskable=True).save(
                OUT / f"icon-{size}-maskable.png", optimize=True
            )

    ico_frames[-1].save(
        ROOT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )


if __name__ == "__main__":
    main()
