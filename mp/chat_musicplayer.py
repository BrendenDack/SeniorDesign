import sys
import time
import logging
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Add parent directory to import Waveshare's LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))
try:
    from lib.LCD_2inch4 import LCD_2inch4
except ImportError as e:
    logging.error("Failed to import LCD_2inch4: %s", e)
    sys.exit(1)

# Define screen dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Asset paths
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"
MAIN_MENU_SCRIPT = "/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/mm/chatV2.py"

# Fonts
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

# GPIO Pin Definitions
SELECT_BUTTON = 5    # GPIO 5: Select
BACK_BUTTON = 6      # GPIO 6: Back
UP_BUTTON = 4        # GPIO 4: Up
RIGHT_BUTTON = 22    # GPIO 22: Right
DOWN_BUTTON = 20     # GPIO 20: Down
LEFT_BUTTON = 21     # GPIO 21: Left
VOLUME_UP = 23       # GPIO 23: Volume Up
VOLUME_DOWN = 24     # GPIO 24: Volume Down

# Selectable elements
SELECTABLE_ITEMS = [
    {"name": "Main Menu", "x": 10, "y": 10, "w": 30, "h": 30, "action": "main_menu"},
    {"name": "Previous", "x": 60, "y": 210, "w": 24, "h": 24, "action": "placeholder"},
    {"name": "Play/Pause", "x": 160, "y": 210, "w": 24, "h": 24, "action": "placeholder"},
    {"name": "Next", "x": 210, "y": 210, "w": 24, "h": 24, "action": "placeholder"},
]
SELECTED_INDEX = 0

def setup_gpio():
    logging.debug("Setting up GPIO pins")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        logging.error("Failed to setup GPIO: %s", e)
        sys.exit(1)

def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(ASSETS_PATH / filename).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: %s", e)

def draw_gui(lcd, selected_index):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)

    # Static elements
    draw.text((130, 10), "12:00", font=font_large, fill="BLACK")
    draw.text((100, 120), "mona lisa", font=font_large, fill="BLACK")
    draw.text((140, 160), "PRYVT", font=font_medium, fill="BLACK")
    draw.text((30, 200), "1:00", font=font_small, fill="BLACK")
    draw.text((260, 200), "2:53", font=font_small, fill="BLACK")
    draw.rectangle([0, 50, 320, 52], fill="BLACK")
    draw.rectangle([40, 180, 280, 185], fill="BLACK")
    draw.rectangle([10, 10, 40, 40], fill="WHITE")

    # Images
    paste_image(img, "image_1.png", (15, 15), resize=(24, 24))
    paste_image(img, "image_2.png", (144, 80), resize=(48, 48))
    paste_image(img, "image_3.png", (140, 190), resize=(40, 5))
    paste_image(img, "image_4.png", (280, 10), resize=(32, 32))
    paste_image(img, "image_5.png", (110, 210), resize=(24, 24))
    paste_image(img, "image_6.png", (60, 210), resize=(24, 24))
    paste_image(img, "image_7.png", (210, 210), resize=(24, 24))
    paste_image(img, "image_8.png", (260, 210), resize=(24, 24))
    paste_image(img, "image_9.png", (160, 210), resize=(24, 24))

    # Highlight selected item
    item = SELECTABLE_ITEMS[selected_index]
    draw.rectangle([item["x"] - 5, item["y"] - 5, item["x"] + item["w"] + 5, item["y"] + item["h"] + 5], outline="GRAY", width=2)

    logging.debug("Drew GUI with selected index: %d (%s)", selected_index, item["name"])
    return img.rotate(90, expand=True)

def update_display(lcd, img):
    try:
        lcd.ShowImage(img)
        time.sleep(0.01)  # Delay for LCD refresh
        logging.debug("Updated display")
    except Exception as e:
        logging.error("Failed to update display: %s", e)

def button_callback(channel):
    global SELECTED_INDEX
    prev_index = SELECTED_INDEX

    if channel == UP_BUTTON:
        logging.debug("Up Button pressed")
        SELECTED_INDEX = 0 if SELECTED_INDEX > 0 else SELECTED_INDEX  # Jump to top-left
    elif channel == DOWN_BUTTON:
        logging.debug("Down Button pressed")
        SELECTED_INDEX = 1 if SELECTED_INDEX == 0 else SELECTED_INDEX  # Jump to first control
    elif channel == LEFT_BUTTON:
        logging.debug("Left Button pressed")
        if SELECTED_INDEX > 1:
            SELECTED_INDEX -= 1  # Move left among controls
    elif channel == RIGHT_BUTTON:
        logging.debug("Right Button pressed")
        if SELECTED_INDEX < len(SELECTABLE_ITEMS) - 1 and SELECTED_INDEX > 0:
            SELECTED_INDEX += 1  # Move right among controls
    elif channel == SELECT_BUTTON:
        logging.debug("Select Button pressed")
        item = SELECTABLE_ITEMS[SELECTED_INDEX]
        logging.info("Selected: %s", item["name"])
        if item["action"] == "main_menu":
            logging.debug("Returning to main menu")
            try:
                subprocess.run(["python", MAIN_MENU_SCRIPT])
                sys.exit(0)
            except Exception as e:
                logging.error("Failed to run main menu: %s", e)
        else:
            logging.info("Placeholder action for %s", item["name"])
    elif channel == BACK_BUTTON:
        logging.debug("Back Button pressed")
        try:
            subprocess.run(["python", MAIN_MENU_SCRIPT])
            sys.exit(0)
        except Exception as e:
            logging.error("Failed to run main menu: %s", e)
    elif channel in [VOLUME_UP, VOLUME_DOWN]:
        logging.debug("Button %d pressed: No mapping", channel)

    if prev_index != SELECTED_INDEX:
        img = draw_gui(lcd, SELECTED_INDEX)
        update_display(lcd, img)

def show_music_player(lcd):
    logging.debug("Entering show_music_player")

    # Initialize LCD
    try:
        lcd.Init()
        lcd.clear()
        logging.debug("Initialized LCD")
    except Exception as e:
        logging.error("Failed to initialize LCD: %s", e)
        sys.exit(1)

    # Setup GPIO
    setup_gpio()
    for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
        try:
            GPIO.add_event_detect(pin, GPIO.RISING, callback=button_callback, bouncetime=200)
            logging.debug("Added event detection for pin %d", pin)
        except Exception as e:
            logging.error("Failed to add event detection for pin %d: %s", pin, e)
            sys.exit(1)

    # Initial display
    try:
        img = draw_gui(lcd, SELECTED_INDEX)
        update_display(lcd, img)
    except Exception as e:
        logging.error("Failed to show initial GUI: %s", e)
        sys.exit(1)

    # Navigation loop
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Exiting via KeyboardInterrupt")
    finally:
        logging.debug("Cleaning up GPIO and LCD")
        for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, RIGHT_BUTTON, DOWN_BUTTON, LEFT_BUTTON, VOLUME_UP, VOLUME_DOWN]:
            try:
                GPIO.remove_event_detect(pin)
            except:
                pass
        try:
            lcd.clear()
            lcd.module_exit()
            logging.debug("Cleaned up LCD")
        except Exception as e:
            logging.error("Failed to clean up LCD: %s", e)

if __name__ == "__main__":
    try:
        lcd = LCD_2inch4()
        show_music_player(lcd)
    except Exception as e:
        logging.error("Main execution failed: %s", e)
        sys.exit(1)