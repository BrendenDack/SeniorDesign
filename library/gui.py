import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Add parent directory to import Waveshare's LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))

from lib.LCD_2inch4 import LCD_2inch4  # Correct import

# Initialize the LCD
lcd = LCD_2inch4()
lcd.Init()
lcd.clear()

# Asset path setup
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Load fonts (adjust paths/sizes as needed)
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

# Create the GUI image
img = Image.new("RGB", (lcd.width, lcd.height), "WHITE")
draw = ImageDraw.Draw(img)

# Helper to draw an image safely
def paste_image(filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
    except Exception as e:
        print(f"[WARN] Could not load {filename}: {e}")

# Draw all GUI elements
draw.text((100, 5), "12:00", font=font_large, fill="black")
draw.text((356, 128), "HYBS", font=font_medium, fill="black")
draw.text((356, 485), "imase", font=font_medium, fill="#515151")
draw.text((616, 89), "Source\nSeparation\nAvailable", font=font_medium, fill="black")
draw.text((610, 446), "Source\nSeparation\nUnavailable", font=font_medium, fill="black")
draw.text((65, 128), "Tip Toe", font=font_large, fill="black")
draw.text((65, 485), "NIGHT DANCER", font=font_large, fill="black")

# Draw rectangles
draw.rectangle([-3, 411, lcd.width, 415], fill="black")
draw.rectangle([-3, 63, lcd.width, 66], fill="black")
draw.rectangle([-3, 229, lcd.width, 233], fill="black")
draw.rectangle([20, 12, 65, 57], fill="white")
draw.rectangle([27, 19, 57, 49], fill="white")

# Draw images
paste_image("image_1.png", (754 - 25, 35 - 25), resize=(50, 50))  # centered around (754, 35)
paste_image("image_2.png", (20, 10), resize=(42, 42))
paste_image("image_3.png", (20, 478), resize=(42, 42))
paste_image("image_4.png", (20, 126), resize=(42, 42))
paste_image("button_1.png", (7, 252), resize=(783, 136))

# Display it
lcd.ShowImage(img)

# Keep the screen on
while True:
    time.sleep(1)
