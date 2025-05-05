#now with gpio zero !!

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
    from firmware.button_firmwareV3 import setup_button_firmware, Buttons, NavAction
    from firmware.battery_firmwareV2 import setup_battery_monitor
    from lib.LCD_2inch4 import LCD_2inch4
    from library import chat_libraryV5 as chat_library
    from mp import chat_musicplayerV3 as chat_musicplayer
except ImportError as e:
    logging.error("Failed to import module: %s", e)
    sys.exit(1)

# Global LCD instance
lcd = None

def get_lcd_instance():
    global lcd
    if lcd is None:
        try:
            lcd = LCD_2inch4()
            lcd.Init()
            lcd.clear()
            logging.debug("Initialized LCD")
        except Exception as e:
            logging.error("Failed to initialize LCD: %s", e)
            sys.exit(1)
    return lcd

# Initialize battery monitor
try:
    battery_monitor = setup_battery_monitor(use_gpio=True)
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
ASSETS_PATH = Path("/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/mm/assets")
FILESYSTEM_PATH = Path("/home/brendendack/SeniorDesignCode/mp3_files")

# Menu items
MENU_ITEMS = [
    {"text": "Library", "x": 20, "y": 60, "action": "library"},
    {"text": "Music Player", "x": 20, "y": 100, "action": "music_player"},
    {"text": "Settings", "x": 20, "y": 140, "action": "settings"},
    {"text": "Exit", "x": 20, "y": 180, "action": "exit"},
]

# Application state
SELECTED_INDEX = 0
VOLUME_LEVEL = 50
BATTERY_INFO = {"capacity": 100.0, "icon": "battery_full.png"}
LAST_BATTERY_UPDATE = 0
current_module = None
in_submodule = False

# Utility functions
def paste_image(img, filename, pos, resize=None):
    try:
        im = Image.open(ASSETS_PATH / filename).convert("RGBA")
        if resize:
            im = im.resize(resize)
        img.paste(im, pos, im)
        logging.debug(f"Pasted image: {filename}")
    except Exception as e:
        logging.warning(f"Could not load {filename}: %s", e)

def draw_gui(selected_index, volume_level, battery_info):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)
    
    draw.text((140, 5), "12:00", font=font_large, fill="BLACK")
    draw.rectangle([0, 40, SCREEN_WIDTH, 42], fill="BLACK")
    draw.rectangle([0, 100, SCREEN_WIDTH, 102], fill="BLACK")
    draw.rectangle([0, 180, SCREEN_WIDTH, 182], fill="BLACK")
    draw.rectangle([65, 15, 85, 35], fill="WHITE")
    
    # Battery
    cap = battery_info.get("capacity", 0)
    icon = battery_info.get("icon", "battery_unknown.png")
    draw.text((240, 5), f"{cap:.0f}%", font=font_menu, fill="BLACK")
    paste_image(img, icon, (275, 5), resize=(36, 26))
    
    # Volume
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
    lcd = get_lcd_instance()
    try:
        lcd.ShowImage(img)
        time.sleep(0.01)
        logging.debug("Updated display")
    except Exception as e:
        logging.error("Failed to update display: %s", e)

def main_menu_callback(index, channel, bf):
    global SELECTED_INDEX, VOLUME_LEVEL, current_module, in_submodule
    
    prev_index = SELECTED_INDEX
    SELECTED_INDEX = index
    
    action = NavAction.from_pin(channel)
    if action == NavAction.SELECT:
        item = MENU_ITEMS[SELECTED_INDEX]
        logging.info("Selected: %s", item["text"])
        
        if item["action"] == "library":
            try:
                in_submodule = True
                current_module = "library"
                chat_library.show_library(get_lcd_instance(), FILESYSTEM_PATH, bf, battery_monitor, ASSETS_PATH)
                logging.debug("Returned from library GUI")
            except Exception as e:
                logging.error("Failed to launch library: %s", e)
            finally:
                current_module = None
                in_submodule = False
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, main_menu_callback)
                if not bf.is_active:
                    bf.start()
                img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
                update_display(img)
                
        elif item["action"] == "music_player":
            try:
                in_submodule = True
                current_module = "music_player"
                chat_musicplayer.show_music_player(get_lcd_instance(), bf, battery_monitor)
                logging.debug("Returned from music player GUI")
            except Exception as e:
                logging.error("Failed to launch music player: %s", e)
            finally:
                current_module = None
                in_submodule = False
                bf.update_menu(MENU_ITEMS, SELECTED_INDEX, main_menu_callback)
                if not bf.is_active:
                    bf.start()
                img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
                update_display(img)
                
        elif item["action"] == "settings":
            logging.info("Settings selected - Placeholder")
            
        elif item["action"] == "exit":
            raise SystemExit
            
    elif action == NavAction.VOLUME_UP:
        VOLUME_LEVEL = min(100, VOLUME_LEVEL + 10)
        
    elif action == NavAction.VOLUME_DOWN:
        VOLUME_LEVEL = max(0, VOLUME_LEVEL - 10)
    
    if prev_index != SELECTED_INDEX or action in [NavAction.VOLUME_UP, NavAction.VOLUME_DOWN]:
        img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
        update_display(img)

def main():
    global SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO, LAST_BATTERY_UPDATE, in_submodule
    
    lcd = get_lcd_instance()
    img = draw_gui(SELECTED_INDEX, VOLUME_LEVEL, BATTERY_INFO)
    update_display(img)
    
    try:
        bf = setup_button_firmware(MENU_ITEMS, selected_index=SELECTED_INDEX, callback=main_menu_callback)
        bf.start()
        logging.debug("Button firmware initialized")
    except Exception as e:
        bf = None
        logging.error("Failed to initialize button firmware: %s", e)
    
    try:
        while True:
            if not in_submodule:
                current_time = time.time()
                if current_time - LAST_BATTERY_UPDATE >= 5:
                    try:
                        if battery_monitor:
                            BATTERY_INFO = battery_monitor.get_battery_info()
                            logging.debug("Updated battery info: %.0f%%, %s",
                                         BATTERY_INFO['capacity'], BATTERY_INFO['icon'])
                        else:
                            BATTERY_INFO = {"capacity": 0, "icon": "battery_unknown.png"}
                    except Exception as e:
                        logging.warning("Battery info error: %s", e)
                        BATTERY_INFO = {"capacity": 0, "icon": "battery_critical.png"}
                    
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
            try:
                battery_monitor.cleanup()
                logging.info("Battery monitor cleaned up")
            except Exception as e:
                logging.warning("Battery monitor cleanup failed: %s", e)
        
        try:
            lcd.clear()
            lcd.module_exit()
            logging.debug("Cleaned up LCD")
        except Exception as e:
            logging.error("LCD cleanup failed: %s", e)

if __name__ == "__main__":
    main()