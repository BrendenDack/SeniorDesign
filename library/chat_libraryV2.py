import sys
import time
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO

# Configure logging early
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Add parent directory to import Waveshare's LCD driver
sys.path.append(str(Path(__file__).resolve().parent.parent))
try:
    from lib.LCD_2inch4 import LCD_2inch4
except ImportError as e:
    logging.error("Failed to import LCD_2inch4: %s", e)
    sys.exit(1)

# Define screen dimensions for landscape layout
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Asset path setup
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/files")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Load scaled fonts
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

# GPIO Pin Definitions
SELECT_BUTTON = 5    # GPIO 5: Select
BACK_BUTTON = 6      # GPIO 6: Back
UP_BUTTON = 4        # GPIO 4: Up
DOWN_BUTTON = 20     # GPIO 20: Down

def setup_gpio():
    logging.debug("Setting up GPIO pins")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, DOWN_BUTTON]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    except Exception as e:
        logging.error("Failed to setup GPIO: %s", e)
        sys.exit(1)

def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: {e}")

def draw_library_gui(lcd, files, selected_index, scroll_offset):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)

    # Static elements (from initial script)
    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")
    paste_image(img, "image_1.png", (275, 5), resize=(36, 26))
    paste_image(img, "image_2.png", (5, 5), resize=(32, 32))

    # File list
    max_display = 4
    for i, file in enumerate(files[scroll_offset:scroll_offset + max_display]):
        y = 60 + i * 30
        text = file.name if file.suffix == ".mp3" else str(file)
        if i + scroll_offset == selected_index:
            draw.rectangle([25, y - 5, 200, y + 20], fill="GRAY")
            draw.text((30, y), text[:20], font=font_small, fill="WHITE")
        else:
            draw.text((30, y), text[:20], font=font_small, fill="BLACK")

    logging.debug("Drew GUI with %d files, selected: %d, offset: %d", len(files), selected_index, scroll_offset)
    return img.rotate(90, expand=True)

def show_library(lcd, directory: Path):
    logging.debug("Entering show_library with directory: %s", directory)

    # Initialize LCD (matching initial script)
    try:
        lcd.Init()
        lcd.clear()
        logging.debug("Initialized LCD")
    except Exception as e:
        logging.error("Failed to initialize LCD: %s", e)
        sys.exit(1)

    # List files (e.g., .mp3)
    try:
        files = [f for f in directory.iterdir() if f.is_file() and f.suffix == ".mp3"]
        if not files:
            files = [Path("No files found")]
        logging.debug("Found %d .mp3 files", len(files))
    except Exception as e:
        logging.error("Failed to access directory %s: %s", directory, e)
        files = [Path("Directory error")]

    # Menu state
    selected_index = 0
    scroll_offset = 0
    max_display = 4
    should_exit = False

    def button_callback(channel):
        nonlocal selected_index, scroll_offset, should_exit
        prev_index = selected_index

        if channel == UP_BUTTON:
            logging.debug("Up Button pressed")
            selected_index = max(0, selected_index - 1)
            if selected_index < scroll_offset:
                scroll_offset = selected_index
        elif channel == DOWN_BUTTON:
            logging.debug("Down Button pressed")
            selected_index = min(len(files) - 1, selected_index + 1)
            if selected_index >= scroll_offset + max_display:
                scroll_offset = selected_index - max_display + 1
        elif channel == SELECT_BUTTON:
            logging.debug("Select Button pressed")
            if files[selected_index].suffix == ".mp3":
                logging.info("Selected file: %s", files[selected_index].name)
                # Placeholder for playback logic
        elif channel == BACK_BUTTON:
            logging.debug("Back Button pressed")
            should_exit = True

        if prev_index != selected_index or scroll_offset != prev_index:
            try:
                img = draw_library_gui(lcd, files, selected_index, scroll_offset)
                lcd.ShowImage(img)
                time.sleep(0.01)  # Small delay for LCD refresh
                logging.debug("Updated display")
            except Exception as e:
                logging.error("Failed to update display: %s", e)

    # Setup GPIO
    setup_gpio()
    for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, DOWN_BUTTON]:
        try:
            GPIO.add_event_detect(pin, GPIO.RISING, callback=button_callback, bouncetime=200)
            logging.debug("Added event detection for pin %d", pin)
        except Exception as e:
            logging.error("Failed to add event detection for pin %d: %s", pin, e)
            sys.exit(1)

    # Initial display
    try:
        img = draw_library_gui(lcd, files, selected_index, scroll_offset)
        lcd.ShowImage(img)
        time.sleep(0.01)  # Small delay for LCD refresh
        logging.debug("Displayed initial GUI")
    except Exception as e:
        logging.error("Failed to show initial GUI: %s", e)
        sys.exit(1)

    # Navigation loop
    try:
        while not should_exit:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Exiting via KeyboardInterrupt")
    finally:
        logging.debug("Cleaning up GPIO and LCD")
        for pin in [SELECT_BUTTON, BACK_BUTTON, UP_BUTTON, DOWN_BUTTON]:
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
        show_library(lcd, FILESYSTEM_PATH)
    except Exception as e:
        logging.error("Main execution failed: %s", e)
        sys.exit(1)