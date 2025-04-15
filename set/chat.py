import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Add path to import Waveshare LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib.LCD_2inch4 import LCD_2inch4

# Initialize LCD
lcd = LCD_2inch4()
lcd.Init()
lcd.clear()

# Set up dimensions for landscape mode
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Paths
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Fonts
font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

# Image canvas
img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
draw = ImageDraw.Draw(img)

# Draw text
draw.text((130, 5), "12:00", font=font_large, fill="black")
draw.text((10, 50), "Storage Space\nAvailable", font=font_medium, fill="black")
draw.text((220, 50), "10 GB", font=font_medium, fill="black")
draw.text((10, 110), "Volume", font=font_medium, fill="black")
draw.text((237, 115), "5", font=font_medium, fill="black")
draw.text((10, 170), "Time Zone", font=font_medium, fill="black")
draw.text((200, 170), "Cupertino", font=font_medium, fill="black")

# Rectangles (like separators)
draw.rectangle([0, 35, SCREEN_WIDTH, 37], fill="black")
draw.rectangle([0, 95, SCREEN_WIDTH, 97], fill="black")
draw.rectangle([0, 155, SCREEN_WIDTH, 157], fill="black")

# Box for icon
draw.rectangle([5, 5, 35, 35], fill="white")

# Images
def paste_image(filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
    except Exception as e:
        print(f"[WARN] Could not load {filename}: {e}")

paste_image("image_1.png", (275, 5), resize=(36, 26))
paste_image("image_2.png", (10, 10), resize=(24, 24))
paste_image("button_1.png", (200, 110), resize=(24, 24))
paste_image("button_2.png", (260, 110), resize=(24, 24))

# Rotate image for landscape display (if needed based on your LCD orientation)
# Comment out the next line if your screen already aligns in landscape natively
img = img.rotate(90, expand=True)

# Show image
lcd.ShowImage(img)

# Keep screen on
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    lcd.module_exit()
    print("Exited cleanly.")
