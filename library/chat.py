import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to import Waveshare's LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))

from lib.LCD_2inch4 import LCD_2inch4  # Correct import

# Initialize the LCD
lcd = LCD_2inch4()
lcd.Init()
lcd.clear()

# Define screen dimensions for landscape layout (width x height)
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Asset path setup
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Load scaled fonts
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)

# Create image in landscape resolution
img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
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

# Draw all GUI elements (landscape layout)
draw.text((140, 5), "12:00", font=font_large, fill="black")
draw.text((140, 60), "HYBS", font=font_medium, fill="black")
draw.text((140, 210), "imase", font=font_medium, fill="#515151")
draw.text((250, 60), "Source\nAvailable", font=font_small, fill="black")
draw.text((180, 130), "Source\nUnavailable", font=font_small, fill="black")
draw.text((30, 60), "Tip Toe", font=font_small, fill="black")
draw.text((30, 210), "NIGHT DANCER", font=font_small, fill="black")

# Draw lines and rectangles
draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="black")
draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="black")
draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="black")
draw.rectangle([65, 15, 85, 35], fill="white")

# Paste images
paste_image("image_1.png", (275, 5), resize=(36, 26))
paste_image("image_2.png", (5, 5), resize=(32, 32))
paste_image("image_3.png", (5, 200), resize=(32, 32))
paste_image("image_3.png", (5, 60), resize=(32, 32))
paste_image("button_1.png", (5, 120), resize=(310, 40))

# 🌀 Rotate image for landscape display on portrait-oriented LCD
img = img.rotate(90, expand=True)

# Show on screen
lcd.ShowImage(img)

# Keep screen on
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    lcd.module_exit()
    print("Exited cleanly.")
