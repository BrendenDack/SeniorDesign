import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Waveshare LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib.LCD_2inch4 import LCD_2inch4

# Initialize the LCD
lcd = LCD_2inch4()
lcd.Init()
lcd.clear()

# Display dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)

# Paths
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Create blank image
img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
draw = ImageDraw.Draw(img)

# Helper: paste images with transparency
def paste_image(filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
    except Exception as e:
        print(f"[WARN] Could not load {filename}: {e}")

draw.text((140, 5), "12:00", font=font_large, fill="black")
draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="black")
draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="black")
draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="black")
draw.rectangle([65, 15, 85, 35], fill="white")

# Place images to simulate GUI layout (scaled to LCD resolution)
paste_image("image_1 copy.png", (275, 5), resize=(36, 26))
paste_image("button_3.png", (10, 50), resize=(310, 50))
paste_image("button_2.png", (10, 115), resize=(310, 50))
paste_image("button_1.png", (10, 190), resize=(310, 50))
# paste_image("image_1.png", (0, 5), resize=(100, 240))  # centered lower image

# Rotate image for landscape screen
img = img.rotate(90, expand=True)

# Show on LCD
lcd.ShowImage(img)

# Keep alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    lcd.module_exit()
    print("Exited cleanly.")
