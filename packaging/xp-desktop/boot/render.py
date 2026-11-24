"""Render the AgentLinux boot animation for the Ubuntu Kylin Plymouth script."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
parser.add_argument("font", help="path to a bold TrueType font")
args = parser.parse_args()
args.destination.mkdir(parents=True, exist_ok=True)
emblem = Image.open(Path(__file__).resolve().parents[2] / "branding/greeter-logo.png")
base = Image.new("RGBA", (380, 180))
base.alpha_composite(emblem.resize((92, 92), Image.Resampling.LANCZOS), (13, 12))
draw = ImageDraw.Draw(base)
draw.text((120, 40), "AgentLinux", font=ImageFont.truetype(args.font, 39), fill="white")
draw.rounded_rectangle((103, 135, 277, 150), radius=5, outline="#aaaeb4", width=2)
for frame in range(60):
    image = base.copy()
    draw = ImageDraw.Draw(image)
    for segment in range(3):
        left = 108 + (frame * 3 + segment * 11) % 177 - 9
        start, end = max(108, left), min(272, left + 8)
        if start <= end:
            draw.rectangle((start, 139, end, 146), fill="#397beb")
            draw.line((start, 140, end, 140), fill="#83b3ff")
    image.save(args.destination / f"{frame + 1}.png")
Image.new("RGBA", (1, 1)).save(args.destination / "uk.png")
