# menu_config.py
MENUS = {
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
            {"label": "Song List", "target": "submenu_songs", "action_type": "dynamic"},
            {"label": "Back", "target": "back"}
        ]
    },
    # ... other menu definitions
}