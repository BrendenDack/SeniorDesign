# now with GPIO zero !!
import sys
import time
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from lib.LCD_2inch4 import LCD_2inch4
    from firmware.button_firmwareV3 import Buttons, NavAction, setup_button_firmware
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets"
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/mp3_files")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

def paste_image(img, filename, pos, resize=None, assets_path=None):
    try:
        asset_dir = assets_path or ASSETS_PATH
        im = Image.open(asset_dir / filename).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: {e}")

def draw_library_gui(lcd, files, selected_index, scroll_offset, battery_info, assets_path=None):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)
    
    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")
    
    cap = battery_info.get("capacity", 0)
    icon = battery_info.get("icon", "battery_unknown.png")
    draw.text((240, 5), f"{cap:.0f}%", font=font_small, fill="BLACK")
    paste_image(img, icon, (275, 5), resize=(36, 26), assets_path=assets_path)
    
    max_display = 4
    for i, file in enumerate(files[scroll_offset:scroll_offset + max_display]):
        y = 60 + i * 30
        text = file.name if hasattr(file, "suffix") and file.suffix == ".mp3" else str(file)
        
        if i + scroll_offset == selected_index:
            draw.rectangle([25, y - 5, 200, y + 20], fill="GRAY")
            draw.text((30, y), text[:20], font=font_small, fill="WHITE")
        else:
            draw.text((30, y), text[:20], font=font_small, fill="BLACK")
    
    if len(files) > max_display:
        total_pages = (len(files) + max_display - 1) // max_display
        current_page = scroll_offset // max_display + 1
        draw.text((160, 220), f"Page {current_page}/{total_pages}", font=font_small, fill="BLACK")
    
    logging.debug("Drew library GUI with %d files, selected: %d, offset: %d, battery: %.0f%%",
                 len(files), selected_index, scroll_offset, cap)
    
    return img.rotate(90, expand=True)

def show_library(lcd, directory: Path, bf, battery_monitor, assets_path=None):
    logging.debug("Entering show_library with directory: %s", directory)
    
    state = {
        "selected_index": 0,
        "scroll_offset": 0,
        "should_exit": False,
        "max_display": 4,
        "selected_file": None
    }
    
    try:
        files = [f for f in directory.iterdir() if f.is_file() and f.suffix == ".mp3"]
        if not files:
            files = [Path("No files found")]
        logging.debug("Found %d .mp3 files", len(files))
    except Exception as e:
        logging.error("Failed to access directory %s: %s", directory, e)
        files = [Path("Directory error")]
    
    files = [Path("Back")] + files
    library_menu_items = [{"text": str(f.name), "x": 30, "y": 60 + i * 30} for i, f in enumerate(files)]
    
    def library_callback(index, channel, bf):
        try:
            logging.debug(f"Library callback: index={index}, channel={channel}")
            
            prev_index = state["selected_index"]
            state["selected_index"] = index
            
            action = NavAction.from_pin(channel)
            if action in [NavAction.UP, NavAction.DOWN]:
                if state["selected_index"] < state["scroll_offset"]:
                    state["scroll_offset"] = state["selected_index"]
                elif state["selected_index"] >= state["scroll_offset"] + state["max_display"]:
                    state["scroll_offset"] = state["selected_index"] - state["max_display"] + 1
            elif action == NavAction.SELECT:
                if state["selected_index"] == 0:
                    logging.debug("Back option selected")
                    state["should_exit"] = True
                else:
                    state["selected_file"] = files[state["selected_index"]]
                    logging.info("Selected file: %s", state["selected_file"])
                    state["should_exit"] = True
            elif action == NavAction.BACK:
                logging.debug("Back button pressed")
                state["should_exit"] = True
            
            if prev_index != state["selected_index"] or action in [NavAction.UP, NavAction.DOWN, NavAction.BACK, NavAction.SELECT]:
                battery_info = battery_monitor.get_battery_info() if battery_monitor else {"capacity": 0, "icon": "battery_unknown.png"}
                img = draw_library_gui(lcd, files, state["selected_index"], state["scroll_offset"], battery_info, assets_path)
                lcd.ShowImage(img)
                logging.debug("Updated library display")
        except Exception as e:
            logging.error("Error in library_callback: %s", e)
            state["should_exit"] = True
    
    # Update button firmware using singleton methods
    try:
        bf = setup_button_firmware(library_menu_items, state["selected_index"], library_callback)
        if not bf.is_active:
            bf.start()
        logging.debug("Updated button firmware for library")
    except Exception as e:
        logging.error("Failed to update button firmware: %s", e)
        return None
    
    try:
        battery_info = battery_monitor.get_battery_info() if battery_monitor else {"capacity": 0, "icon": "battery_unknown.png"}
        img = draw_library_gui(lcd, files, state["selected_index"], state["scroll_offset"], battery_info, assets_path)
        lcd.ShowImage(img)
        logging.debug("Displayed initial library GUI")
    except Exception as e:
        logging.error("Failed to show initial library GUI: %s", e)
    
    try:
        start_time = time.time()
        last_check = start_time
        timeout = 60
        
        while not state["should_exit"]:
            time.sleep(0.1)
            
            if bf.selected_index != state["selected_index"]:
                state["selected_index"] = bf.selected_index
                if state["selected_index"] < state["scroll_offset"]:
                    state["scroll_offset"] = state["selected_index"]
                elif state["selected_index"] >= state["scroll_offset"] + state["max_display"]:
                    state["scroll_offset"] = state["selected_index"] - state["max_display"] + 1
                battery_info = battery_monitor.get_battery_info() if battery_monitor else {"capacity": 0, "icon": "battery_unknown.png"}
                img = draw_library_gui(lcd, files, state["selected_index"], state["scroll_offset"], battery_info, assets_path)
                lcd.ShowImage(img)
                logging.debug("Updated library display after index change")
            
            now = time.time()
            if now - last_check > 5:
                logging.debug("Library active, selected_index=%d, should_exit=%s",
                             state["selected_index"], state["should_exit"])
                last_check = now
            
            if now - start_time > timeout:
                logging.warning("Library timeout after %d seconds", timeout)
                break
    except KeyboardInterrupt:
        logging.info("Exiting library via KeyboardInterrupt")
    except Exception as e:
        logging.error("Error in library main loop: %s", e)
    
    return state["selected_file"]