# music_loader.py
import os
import time
from menu_config import MENUS  # Import menus for updating

ALL_MUSIC_FILES = []
CURRENT_PAGE = 0
ITEMS_PER_PAGE = 5

def load_music_files(page=0):
    global ALL_MUSIC_FILES, CURRENT_PAGE
    music_folder = "Music"
    try:
        files = os.listdir(music_folder)
        mp3s = sorted([f for f in files if f.lower().endswith(".mp3")])
        flac = sorted([f for f in files if f.lower().endswith(".flac")])
        wav = sorted([f for f in files if f.lower().endswith(".wav")])
        ALL_MUSIC_FILES = sorted(mp3s + flac + wav)
        CURRENT_PAGE = page

        start = page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        current_files = ALL_MUSIC_FILES[start:end]

        options = [
            {"label": f, "target": None, "action": f"echo Playing {f}", "action_type": "shell"}
            for f in current_files
        ]
        if page > 0:
            options.append({"label": "Previous Page", "target": "prev_page"})
        if end < len(ALL_MUSIC_FILES):
            options.append({"label": "Next Page", "target": "next_page"})
        options.append({"label": "Back", "target": "back"})

        MENUS["submenu_songs"]["options"] = options
    except Exception as e:
        MENUS["submenu_songs"]["options"] = [
            {"label": f"Error loading files: {e}", "target": "back"},
            {"label": "Back", "target": "back"}
        ]