from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import logging
import time
import sys
import traceback
from firmware.button_firmware import setup_button_firmware

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Asset path setup
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/mp3_files")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Load scaled fonts
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

# Display dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(relative_to_assets(filename)).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: {e}")

def draw_library_gui(files, selected_index, scroll_offset):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)

    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")
    paste_image(img, "image_1.png", (275, 5), resize=(36, 26))
    paste_image(img, "image_2.png", (5, 5), resize=(32, 32))

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

def show_library(lcd, filesystem_path):
    try:
        logging.debug("Entering show_library with directory: %s", filesystem_path)

        try:
            if not filesystem_path.exists():
                logging.error("Directory %s does not exist", filesystem_path)
                files = [Path("Directory not found")]
            else:
                files = [f for f in filesystem_path.iterdir() if f.is_file() and f.suffix == ".mp3"]
                if not files:
                    files = [Path("No files found")]
                logging.debug("Found %d .mp3 files", len(files))
        except Exception as e:
            logging.error("Failed to access directory %s: %s", filesystem_path, e)
            files = [Path("Directory error")]

        scroll_offset = 0
        max_display = 4

        LIBRARY_ITEMS = [{"text": file.name, "x": 30, "y": 60 + i * 30} for i, file in enumerate(files)]

        def library_callback(index, channel):
            nonlocal scroll_offset
            selected_index = index
            try:
                if channel == 13:
                    logging.info(f"Selected file: {files[selected_index].name}")
                    # Placeholder for playback logic
                elif channel == 6:
                    logging.info("Exiting library")
                    raise SystemExit
                if selected_index < scroll_offset:
                    scroll_offset = selected_index
                elif selected_index >= scroll_offset + max_display:
                    scroll_offset = selected_index - max_display + 1
                lcd.ShowImage(draw_library_gui(files, selected_index, scroll_offset))
            except Exception as e:
                logging.error("Library callback failed: %s\n%s", e, traceback.format_exc())
                raise

        try:
            bf = setup_button_firmware(LIBRARY_ITEMS, selected_index=0, callback=library_callback)
            bf.start()
            logging.debug("Library button firmware initialized")
        except Exception as e:
            logging.error("Failed to initialize library button firmware: %s\n%s", e, traceback.format_exc())
            return

        lcd.ShowImage(draw_library_gui(files, bf.selected_index, scroll_offset))

        try:
            while True:
                time.sleep(0.1)
        except SystemExit:
            bf.stop()
            logging.debug("Library button firmware stopped")
        except Exception as e:
            logging.error("Library GUI loop failed: %s\n%s", e, traceback.format_exc())
        finally:
            bf.stop()
            logging.debug("Library button firmware cleaned up")

    except Exception as e:
        logging.error("Failed to display library: %s\n%s", e, traceback.format_exc())