#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
from pathlib import Path
import logging

try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    print("Error: RPi.GPIO not found. Please install it with 'pip install RPi.GPIO'")
    sys.exit(1)

# Library path for Waveshare e-Paper
base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
libdir = '/home/advented/audioProductV1/projectCode/e-Paper/RaspberryPi_JetsonNano/python/lib/'

if os.path.exists(libdir):
    sys.path.append(libdir)
    print(f"Using library path: {libdir}")
else:
    print(f"Error: Library directory {libdir} not found")
    sys.exit(1)

# Add path for button firmware file
button_firmware_dir = '/home/advented/audioProductV1/projectCode/'
button_firmware_path = os.path.join(button_firmware_dir, 'button_firmware.py')
if os.path.exists(button_firmware_path):
    sys.path.append(button_firmware_dir)  # Append the directory containing the file
    print(f"Button firmware file found at: {button_firmware_path}")
else:
    print(f"Error: Button firmware file {button_firmware_path} not found")
    sys.exit(1)

try:
    from waveshare_epd import epd1in54_V2
    from button_firmware import ButtonFirmware  # Import from button_firmware.py
except ModuleNotFoundError as e:
    print(f"Error: Could not import module - {e}")
    sys.exit(1)

import time
from PIL import Image, ImageDraw, ImageFont

# Asset path
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("assets/frame0")

logging.basicConfig(level=logging.DEBUG)

# Initialize e-ink display
print("Initializing e-ink display...")
epd = epd1in54_V2.EPD()
epd.init(isPartial=False)
epd.Clear()

# Scaling for 200x200 display, reduced by 10%
SCALE_X = 200 / 800  # Original 800px width scaled down to 720px
SCALE_Y = 200 / 800  # Original 600px height scaled down to 540px

def scale_x(x):
    return int(x * SCALE_X)

def scale_y(y):
    return int(y * SCALE_Y)

# Menu items with adjusted coordinates
MENU_ITEMS = [
    {"text": "Tip Toe", "x": scale_x(65), "y": scale_y(128)},
    {"text": "NIGHT DANCER", "x": scale_x(65), "y": scale_y(485)},
    {"text": "Source Separation", "x": scale_x(616), "y": scale_y(89)},
]
SELECTED_INDEX = 0

def draw_gui(selected_index):
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf', 9)

    # Static elements with scaled coordinates
    draw.text((scale_x(355), scale_y(15)), "12:00", font=font, fill=0)
    draw.text((scale_x(356), scale_y(128)), "HYBS", font=font, fill=0)
    draw.text((scale_x(356), scale_y(485)), "imase", font=font, fill=0)
    draw.rectangle([scale_x(-3), scale_y(411), scale_x(799), scale_y(415)], fill=0)
    draw.rectangle([scale_x(-3), scale_y(63), scale_x(800), scale_y(66)], fill=0)
    draw.rectangle([scale_x(-3), scale_y(229), scale_x(799), scale_y(233)], fill=0)
    draw.rectangle([scale_x(20), scale_y(12), scale_x(65), scale_y(57)], fill=255)
    draw.rectangle([scale_x(27), scale_y(19), scale_x(57), scale_y(49)], fill=255)

    # Menu items with highlight
    for i, item in enumerate(MENU_ITEMS):
        text = item["text"]
        x, y = item["x"], item["y"]
        if i == selected_index:
            draw.rectangle([x - 2, y - 2, x + 45, y + 11], fill=0)
            draw.text((x, y), text, font=font, fill=255)
        else:
            draw.text((x, y), text, font=font, fill=0)

    # Images with scaled sizes
    try:
        img_1 = Image.open(ASSETS_PATH / "image_1.png").convert('1').resize((scale_x(45), scale_y(45)))
        image.paste(img_1, (scale_x(754), scale_y(35)))
        img_2 = Image.open(ASSETS_PATH / "image_2.png").convert('1').resize((scale_x(27), scale_y(27)))
        image.paste(img_2, (scale_x(41), scale_y(34)))
        img_3 = Image.open(ASSETS_PATH / "image_3.png").convert('1').resize((scale_x(27), scale_y(27)))
        image.paste(img_3, (scale_x(41), scale_y(499)))
        img_4 = Image.open(ASSETS_PATH / "image_4.png").convert('1').resize((scale_x(27), scale_y(27)))
        image.paste(img_4, (scale_x(41), scale_y(147)))
        btn_img = Image.open(ASSETS_PATH / "button_1.png").convert('1').resize((scale_x(705), scale_y(122)))
        image.paste(btn_img, (scale_x(7), scale_y(252)))
    except FileNotFoundError as e:
        logging.warning(f"Asset not found: {e}")

    return image

def update_display(epd, image):
    epd.init(isPartial=False)
    epd.display(epd.getbuffer(image))

# Callback for button firmware to update GUI
def gui_callback(selected_index):
    print(f"Current selection: {MENU_ITEMS[selected_index]['text']}")
    new_image = draw_gui(selected_index)
    update_display(epd, new_image)

# Main execution
print("Drawing initial GUI...")
initial_image = draw_gui(SELECTED_INDEX)
update_display(epd, initial_image)

print("Setting up button firmware...")
button_fw = ButtonFirmware(MENU_ITEMS, SELECTED_INDEX, callback=gui_callback)
button_fw.start()

print("Button navigation active. Press Ctrl+C to exit")
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    logging.info("Exiting via Ctrl+C...")
except Exception as e:
    logging.error(f"Error: {e}")
    raise
finally:
    logging.info("Cleaning up...")
    button_fw.cleanup()  # Use firmware cleanup
    epd.sleep()
    sys.exit(0)
