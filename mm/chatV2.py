import sys
import time
import logging
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
    from lib.LCD_2inch4 import LCD_2inch4
    from library import chat_libraryV2
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
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/files")

# Menu items
MENU_ITEMS = [
    {"text": "Library", "x": 20, "y": 60, "action": "library"},
    {"text": "Music Player", "x": 20, "y": 100, "action": "music_player"},
    {"text": "Settings", "x": 20, "y": 140, "action": "settings"},
    {"text": "Exit", "x": 20, "y": 180, "action": "exit"},
]
SELECTED_INDEX = 0
VOLUME_LEVEL = 50  # Initial volume (0-100)

def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(ASSETS_PATH / filename).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: %s", e)

def draw_gui(selected_index, volume_level):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)

    # Static elements
    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")
    paste_image(img, "image_1 copy.png", (275, 5), resize=(36, 26))

    # Volume indicator
    draw.text((220, 20), f"Vol: {volume_level}%", font=font_menu, fill="BLACK")

    # Menu items with highlight
    for i, item in enumerate(MENU_ITEMS):
        x, y = item["x"], item["y"]
        text = item["text"]
        if i == selected_index:
            draw.rectangle([x - 5, y - 5, x + 100, y + 20], fill="GRAY")
            draw.text((x, y), text, font=font_menu, fill="WHITE")
        else:
            draw.text((x, y), text, font=font_menu, fill="BLACK")

    logging.debug("Drew GUI with selected index: %d, volume: %d%%", selected_index, volume_level)
    return img.rotate(90, expand=True)

def update_display(img):
    try:
        lcd.ShowImage(img)
        time.sleep(0.01)  # Delay for LCD refresh
        logging.debug("Updated display")
    except Exception as e:
        logging.error("Failed to update display: %s", e)

def custom_callback(index, channel):
    global SELECTED_INDEX, VOLUME_LEVEL
    prev_index = SELECTED_INDEX
    SELECTED_INDEX = index

    if channel == 13:  # SELECT_BUTTON
        item = MENU_ITEMS[SELECTED_INDEX]
        logging.info("Selected: %s", item["text"])
        if item["action"] == "library":
            try:
                chat_libraryV2.show_library(lcd, FILESYSTEM_PATH)
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL))  # Redraw main menu
            except Exception as e:
                logging.error("Failed to launch library: %s", e)
        elif item["action"] == "music_player":
            try:
                chat_musicplayer.show_music_player(lcd)
                update_display(draw_gui(SELECTED_INDEX, VOLUME_LEVEL))  # Redraw main menu
            except Exception as e:
                logging.error("Failed to launch music player: %s", e)
        elif item["action"] == "settings":
            logging.info("Settings selected - Placeholder")
        elif item["action"] == "exit":
            logging.info("Exiting...")
            raise SystemExit
    elif channel == 6:  # BACK_BUTTON
        logging.debug("Back Button (GPIO %d) pressed - No mapping", channel)
    elif channel == 23:  # VOLUME_UP
        logging.debug("Volume Up Button (GPIO %d) pressed", channel)
        VOLUME_LEVEL = min(100, VOLUME_LEVEL + 10)
    elif channel == 24:  # VOLUME_DOWN
        logging.debug("Volume Down Button (GPIO %d) pressed", channel)
        VOLUME_LEVEL = max(0, VOLUME_LEVEL - 10)
    elif channel in [22, 21]:  # RIGHT_BUTTON, LEFT_BUTTON
        logging.debug("Button (GPIO %d) pressed - No mapping", channel)

    if prev_index != SELECTED_INDEX or channel in [23, 24]:
        img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL)
        update_display(img)

# Initialize
logging.debug("Starting main menu")
try:
    img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL)
    update_display(img)

    # Setup button firmware
    try:
        bf = setup_button_firmware(MENU_ITEMS, selected_index=SELECTED_INDEX, callback=custom_callback)
        logging.debug("Button firmware initialized")
        bf.start()
    except Exception as e:
        logging.error("Failed to initialize button firmware: %s", e)
        sys.exit(1)

    # Main loop
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Exiting via KeyboardInterrupt")
    except SystemExit:
        logging.info("Exiting via menu selection")
    finally:
        bf.cleanup()
        try:
            lcd.clear()
            lcd.module_exit()
            logging.debug("Cleaned up LCD")
        except Exception as e:
            logging.error("Failed to clean up LCD: %s", e)
except Exception as e:
    logging.error("Main execution failed: %s", e)
    sys.exit(1)