import sys
import time
import logging
import subprocess
import os
import RPi.GPIO as GPIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Add paths for library and music player scripts
sys.path.append("/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/library")
sys.path.append("/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/mp")
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from firmware.button_firmware import setup_button_firmware
    from firmware.battery_firmwareV2 import setup_battery_monitor
    from lib.LCD_2inch4 import LCD_2inch4
    from library.chat_libraryV3 import show_library
    from mp import chat_musicplayer
except ImportError as e:
    logging.error("Failed to import module: %s", e)
    sys.exit(1)

# Initialize the LCD
lcd = LCD_2inch4()
try:
    lcd.Init()
    lcd.clear()
    logging.debug("Initialized LCD")
except Exception as e:
    logging.error("Failed to initialize LCD: %s", e)
    sys.exit(1)

# Check for existing GPIO processes
def check_gpio_processes():
    try:
        result = subprocess.run(['sudo', 'lsof', '/dev/gpio*'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'python' in line:
                pid = int(line.split()[1])
                if pid != os.getpid():
                    logging.warning(f"Found process using GPIO: PID {pid}, killing it")
                    subprocess.run(['sudo', 'kill', '-9', str(pid)])
    except Exception as e:
        logging.warning(f"Failed to check GPIO processes: {e}")

# Initialize the battery monitor
try:
    check_gpio_processes()
    battery_monitor = setup_battery_monitor(use_gpio=False)
    logging.debug("Battery monitor initialized")
except Exception as e:
    logging.error("Failed to initialize battery monitor: %s", e)
    battery_monitor = None

# Display dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Fonts
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_menu = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

# Paths
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/mp3_files")

# Menu items
MENU_ITEMS = [
    {"text": "Library", "x": 20, "y": 60, "action": "library"},
    {"text": "Music Player", "x": 20, "y": 100, "action": "music_player"},
    {"text": "Settings", "x": 20, "y": 140, "action": "settings"},
    {"text": "Exit", "x": 20, "y": 180, "action": "exit"},
]
SELECTED_INDEX = 0
VOLUME_LEVEL = 50
BATTERY_INFO = {"capacity": 100.0, "icon": "battery_unknown.png"}
LAST_BATTERY_UPDATE = 0

# Utility functions
def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(ASSETS_PATH / filename).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: {e}")

def draw_gui(selected_index, volume_level, battery_info):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)
    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")

    cap = battery_info.get("capacity", 0)
    icon = battery_info.get("icon", "battery_unknown.png")
    draw.text((240, 5), f"{cap:.0f}%", font=font_menu, fill="BLACK")
    paste_image(img, icon, (275, 5), resize=(36, 26))

    draw.text((220, 20), f"Vol: {volume_level}%", font=font_menu, fill="BLACK")

    for i, item in enumerate(MENU_ITEMS):
        x, y = item["x"], item["y"]
        if i == selected_index:
            draw.rectangle([x - 5, y - 5, x + 100, y + 20], fill="GRAY")
            draw.text((x, y), item["text"], font=font_menu, fill="WHITE")
        else:
            draw.text((x, y), item["text"], font=font_menu, fill="BLACK")

    logging.debug("Drew GUI with selected index: %d, volume: %d%%, battery: %.0f%%",
                  selected_index, volume_level, battery_info.get('capacity', 0))
    return img.rotate(90, expand=True)

def update_display(img):
    try:
        lcd.ShowImage(img)
        time.sleep(0.01)
        logging.debug("Updated display")
    except Exception as e:
        logging.error("Failed to update display: %s", e)

def custom_callback(index, channel):
    global SELECTED_INDEX, VOLUME_LEVEL

    SELECTED_INDEX = index

    if channel == 13:
        item = MENU_ITEMS[SELECTED_INDEX]
        logging.info("Selected: %s", item["text"])
        if item["action"] == "library":
            try:
                bf.stop()
                show_library(lcd, FILESYSTEM_PATH)
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, custom_callback)
                bf.start()
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO))
            except Exception as e:
                logging.error("Failed to launch library: %s", e)
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, custom_callback)
                bf.start()
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO))
        elif item["action"] == "music_player":
            try:
                bf.stop()
                chat_musicplayer.show_music_player(lcd)
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, custom_callback)
                bf.start()
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO))
            except Exception as e:
                logging.error("Failed to launch music player: %s", e)
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, custom_callback)
                bf.start()
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO))
        elif item["action"] == "settings":
            logging.info("Settings selected - Placeholder")
        elif item["action"] == "exit":
            raise SystemExit
    elif channel == 23:
        VOLUME_LEVEL = min(100, VOLUME_LEVEL + 10)
    elif channel == 24:
        VOLUME_LEVEL = max(0, VOLUME_LEVEL - 10)

    if channel in [4, 20, 23, 24]:
        img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
        update_display(img)

# Start main GUI
try:
    img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
    update_display(img)

    try:
        check_gpio_processes()
        global bf
        bf = setup_button_firmware(MENU_ITEMS, selected_index=SELECTED_INDEX, callback=custom_callback)
        bf.start()
        logging.debug("Button firmware initialized")
    except Exception as e:
        bf = None
        logging.error("Failed to initialize button firmware: %s", e)

    while True:
        current_time = time.time()
        if current_time - LAST_BATTERY_UPDATE >= 5:
            try:
                if battery_monitor:
                    BATTERY_INFO = battery_monitor.get_battery_info()
                    logging.debug("Updated battery info: %.0f%%, %s", BATTERY_INFO['capacity'], BATTERY_INFO['icon'])
                else:
                    BATTERY_INFO = {"capacity": 0, "icon": "battery_unknown.png"}
            except Exception as e:
                logging.warning("Battery info error: %s", e)
                BATTERY_INFO = {"capacity": 0, "icon": "battery_unknown.png"}
            LAST_BATTERY_UPDATE = current_time
            img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
            update_display(img)
        time.sleep(0.1)
except KeyboardInterrupt:
    logging.info("Exiting via KeyboardInterrupt")
except SystemExit:
    logging.info("Exiting via menu selection")
finally:
    if bf:
        try:
            bf.cleanup()
            logging.info("Button firmware cleaned up")
        except Exception as e:
            logging.warning("Button firmware cleanup failed: %s", e)
    if battery_monitor:
        battery_monitor.cleanup()
    try:
        lcd.clear()
        lcd.module_exit()
        logging.debug("Cleaned up LCD")
    except Exception as e:
        logging.error("LCD cleanup failed: %s", e)