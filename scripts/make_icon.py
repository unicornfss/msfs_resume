from PIL import Image, ImageDraw
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
GOLD = (212, 180, 90, 255)
NAVY = (18, 28, 48, 255)


def make_image(size: int) -> Image.Image:
    """Solid gold disc with a navy resume mark — readable at 16px title-bar size."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, size - 1, size - 1), fill=GOLD)
    margin = max(2, size // 6)
    bar_w = max(2, size // 7)
    bar_l = margin
    bar_t = margin
    bar_b = size - margin
    draw.rectangle((bar_l, bar_t, bar_l + bar_w, bar_b), fill=NAVY)
    tri_l = bar_l + bar_w + max(1, size // 20)
    draw.polygon(
        [(tri_l, bar_t), (size - margin, size // 2), (tri_l, bar_b)],
        fill=NAVY,
    )
    return image


def main() -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    images = [make_image(s) for s in sizes]
    ico = OUT / "msfs-resume.ico"
    images[0].save(ico, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    images[-1].save(OUT / "msfs-resume.png", format="PNG")
    print(ico)


if __name__ == "__main__":
    main()
