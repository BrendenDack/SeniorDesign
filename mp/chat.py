import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to import Waveshare's LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib.LCD_2inch4 import LCD_2inch4

# Initialize the LCD
lcd = LCD_2inch4()
lcd.Init()
lcd.clear()

# Define screen dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Asset paths
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Fonts
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)

# Create blank image
img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
draw = ImageDraw.Draw(img)

# Helper: Paste image safely
def paste_image(filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
    except Exception as e:
        print(f"[WARN] Could not load {filename}: {e}")

# ========== Draw elements based on Tkinter layout ==========

# Time top center
draw.text((130, 10), "12:00", font=font_large, fill="black")

# Track name
draw.text((100, 120), "mona lisa", font=font_large, fill="black")

# "PRYVT" subtitle
draw.text((140, 160), "PRYVT", font=font_medium, fill="black")

# Left time (start)
draw.text((30, 200), "1:00", font=font_small, fill="black")

# Right time (end)
draw.text((260, 200), "2:53", font=font_small, fill="black")

# Horizontal divider lines
draw.rectangle([0, 50, 320, 52], fill="black")
draw.rectangle([40, 180, 280, 185], fill="black")

# Simulate "white square" around menu icon
draw.rectangle([10, 10, 40, 40], fill="white")

# ========== Paste images ==========
paste_image("image_1.png", (15, 15), resize=(24, 24))        # Top-left icon
paste_image("image_2.png", (144, 80), resize=(48, 48))       # Central image
paste_image("image_3.png", (140, 190), resize=(40, 5))       # Progress bar

paste_image("image_4.png", (280, 10), resize=(32, 32))       # Top-right icon
paste_image("image_5.png", (110, 210), resize=(24, 24))      # Music control
paste_image("image_6.png", (60, 210), resize=(24, 24))
paste_image("image_7.png", (210, 210), resize=(24, 24))
paste_image("image_8.png", (260, 210), resize=(24, 24))
paste_image("image_9.png", (160, 210), resize=(24, 24))

# Rotate image to match landscape display on portrait LCD
img = img.rotate(90, expand=True)

# Display on screen
lcd.ShowImage(img)

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    lcd.module_exit()
    print("Exited cleanly.")
