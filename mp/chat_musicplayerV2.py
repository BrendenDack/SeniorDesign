import sys
import time
import logging
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
DEMO_SONG_PATH = "/home/brendendack/SeniorDesignCode/mp3_files/custom_combined.wav"

# Fonts
try:
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
except Exception as e:
    logging.error("Failed to load fonts: %s", e)
    sys.exit(1)

# Menu items
MENU_ITEMS = [
    {"text": "Main Menu", "x": 10, "y": 10, "action": "main_menu"},
    {"text": "Play/Pause", "x": 120, "y": 180, "action": "play_pause"},
    {"text": "Exit", "x": 220, "y": 10, "action": "exit"}
]

SELECTED_INDEX = 0
is_playing = False
ffplay_process = None

def draw_gui(lcd, selected_index, playing):
    img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
    draw = ImageDraw.Draw(img)
    draw.text((120, 20), "Music Player", font=font_large, fill="BLACK")
    draw.text((70, 90), "Demo Song:", font=font_medium, fill="BLACK")
    draw.text((70, 120), "custom_combined.wav", font=font_small, fill="BLACK")
    draw.text((120, 150), "Status: " + ("Playing" if playing else "Paused"), font=font_medium, fill="RED" if playing else "BLACK")
    for i, item in enumerate(MENU_ITEMS):
        x, y = item["x"], item["y"]
        color = "GRAY" if i == selected_index else "BLACK"
        draw.rectangle([x-5, y-5, x+120, y+25], fill=color if i == selected_index else None, outline="GRAY")
        draw.text((x, y), item["text"], font=font_medium, fill="WHITE" if i == selected_index else "BLACK")
    return img.rotate(90, expand=True)

def update_display(lcd, img):
    try:
        lcd.ShowImage(img)
        time.sleep(0.01)
    except Exception as e:
        logging.error("Failed to update display: %s", e)

def stop_ffplay():
    global ffplay_process, is_playing
    if ffplay_process and ffplay_process.poll() is None:
        ffplay_process.terminate()
        ffplay_process = None
    is_playing = False

def music_player_callback(index, channel, bf):
    global SELECTED_INDEX, is_playing, ffplay_process
    from firmware.button_firmwareV2 import Buttons, NavAction

    prev_index = SELECTED_INDEX
    SELECTED_INDEX = index

    action = NavAction.from_pin(channel)
    item = MENU_ITEMS[SELECTED_INDEX]

    lcd = bf.lcd

    if action == NavAction.SELECT:
        if item["action"] == "main_menu":
            stop_ffplay()
            return
        elif item["action"] == "play_pause":
            if not is_playing:
                stop_ffplay()
                try:
                    ffplay_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", DEMO_SONG_PATH],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    is_playing = True
                except Exception as e:
                    logging.error("Failed to play demo song: %s", e)
            else:
                stop_ffplay()
        elif item["action"] == "exit":
            stop_ffplay()
            sys.exit(0)
    elif action == NavAction.BACK:
        stop_ffplay()
        return

    if prev_index != SELECTED_INDEX or action in [NavAction.SELECT, NavAction.BACK]:
        img = draw_gui(lcd, SELECTED_INDEX, is_playing)
        update_display(lcd, img)

def show_music_player(lcd, bf, battery_monitor=None):
    global SELECTED_INDEX, is_playing, ffplay_process
    SELECTED_INDEX = 0
    is_playing = False
    ffplay_process = None

    bf.lcd = lcd
    bf.update_menu(MENU_ITEMS, selected_index=SELECTED_INDEX, callback=music_player_callback)
    if not bf.is_active:
        bf.start()

    img = draw_gui(lcd, SELECTED_INDEX, is_playing)
    update_display(lcd, img)

    try:
        while True:
            if is_playing and ffplay_process and ffplay_process.poll() is not None:
                is_playing = False
                img = draw_gui(lcd, SELECTED_INDEX, is_playing)
                update_display(lcd, img)
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_ffplay()
    finally:
        stop_ffplay()