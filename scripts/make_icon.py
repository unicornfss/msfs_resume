from PIL import Image, ImageDraw
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)


def make_image(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = max(2, size // 16)
    draw.ellipse((pad, pad, size - pad, size - pad), fill=(22, 24, 29, 255))
    draw.ellipse((pad * 2, pad * 2, size - pad * 2, size - pad * 2), outline=(212, 180, 90, 255), width=max(2, size // 16))
    cx, cy = size // 2, size // 2
    draw.polygon([(cx, pad * 4), (size - pad * 5, size - pad * 5), (pad * 5, size - pad * 5)], fill=(212, 180, 90, 255))
    return image


def main() -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    images = [make_image(s) for s in sizes]
    ico = OUT / "msfs-resume.ico"
    images[0].save(ico, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(ico)


if __name__ == "__main__":
    main()
