# menu_config.py
# Menu definitions with labels, targets, and actions
MENUS  = {
    "main": {
        "title": "Main Menu",
        "options": [
            {"label": "Library", "target": "submenu_Library"},
            {"label": "Settings", "target": "submenu_Settings"},
            {"label": "Player", "target": "submenu_Music_Player"},
        ]
    },
    "submenu_Library": {
        "title": "Library",
        "options": [
            {"label": "Song List", "target": "submenu_songs", "action_type" : "dynamic"},
            # {"label": "Apply Spatial Audio", "target": "submenu_songs_spatial", "action_type" : "dynamic"},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_songs": {
        "title": "Songs",
        "options": [
            {"label": "Songs", "target": None},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_song_options": {
    "title": "Song Options",
    "options": [  # These will be updated dynamically when entering the menu
        {"label": "Play Song", "target": None, "action_type": "python", "action": "play_song"},
        {"label": "Apply Spatial Audio", "target": None, "action": "apply_spatial_audio", "action_type": "python"},
        {"label": "Back", "target": "back"}
    ]
    },
    "submenu_Settings": {
        "title": "Settings",
        "options": [
            {"label": "Change Time", "target": None, "action" : "date", "action_type" : "shell"},
            {"label": "Change Profile", "target": None, "action" : ""},
            {"label": "Run Calibration", "target": None, "action" : "run_calibration", "action_type" : "python"},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_Music_Player": {
        "title": "Music Player",
        "options": [
            {"label": "Current Track", "target": None},
            {"label": "Time Remaining", "target": None},
            {"label": "Back", "target": "back"}
        ]
    }
}
