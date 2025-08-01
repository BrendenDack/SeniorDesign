# Imports
import os
import curses
import subprocess
import time
import pickle
from gpiozero import Button
import gpiozero as gpio
from gpiozero.pins.mock import MockFactory
from gpiozero.exc import GPIOZeroError
import threading
import stt
from calibrateUserProfile import run_calibration
from utility import run_spatial_audio, apply_bulk_hrtf, summed_signal
from datetime import datetime
from menu_app_modular.battery_monitor import get_battery_info
import soundfile as sf
from CalibrateV3 import run_calibration_function
from editProfiles import edit_profile

import smbus2



# This is a module in gpiozero that lets us use "pretend" buttons so I can test without it crashing
# It allows you to also manually set pin values for buttons to test without real hardware
# Mock pins for testing - Remove if you have real buttons to test with
#gpio.Device.pin_factory = MockFactory()

# GPIO buttons (optional for testing on hardware)
try:
    # Claim all button GPIOs
    SELECT_BUTTON =  Button(26, pull_up=False, bounce_time=0.2)
    BACK_BUTTON =  Button(16, pull_up=False, bounce_time=0.2)
    UP_BUTTON =  Button(4, pull_up=False, bounce_time=0.2)
    RIGHT_BUTTON =  Button(22, pull_up=False, bounce_time=0.2)
    DOWN_BUTTON =  Button(20, pull_up=False, bounce_time=0.2)
    LEFT_BUTTON =  Button(21, pull_up=False, bounce_time=0.2)
    VOLUME_UP =  Button(23, pull_up=False, bounce_time=0.2)
    VOLUME_DOWN =  Button(24, pull_up=False, bounce_time=0.)
except GPIOZeroError:
    SELECT_BUTTON = BACK_BUTTON = UP_BUTTON = RIGHT_BUTTON = DOWN_BUTTON = LEFT_BUTTON = VOLUME_DOWN = VOLUME_UP = None # If buttons fail, set all to none and use fallback method (keyboard)
    print(f"Buttons init Failed. Could not claim Buttons.")
    time.sleep(3)

# Global Variables
menu_stack = ["main"]
GLOBAL_VOLUME = 0 
current_index = 0
up_pressed = down_pressed = select_pressed = back_pressed = False
vol_up_pressed = vol_down_pressed = False
selected_song = None
song_paused = False
Loaded_Profile = None
# For pages
current_page = 0
items_per_page = 5
all_music_files = []
directory = None
# For Speech to Text
recognition_thread = None
recognition_running = False

# Menu definitions with labels, targets, and actions
menus = {
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
            {"label": "Spatial Audio List", "target": "submenu_spatial_songs", "action_type" : "dynamic"},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_songs": {
        "title": "Songs",
        "options": [ # These will be updated dynamically when entering the menu
            {"label": "Songs", "target": None},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_spatial_songs": {
        "title": "Spatial Songs",
        "options": [ # These will be updated dynamically when entering the menu
            {"label": "Songs", "target": None},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_profiles": {
        "title": "Spatial Profiles",
        "options": [ # These will be updated dynamically when entering the menu
            {"label": "Songs", "target": None},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_profile_options": {
    "title": "Load This Profile?",
    "options": [  
        {"label": "Yes", "target": "submenu_settings", "action_type": "python", "action": "select_profile"},
        {"label": "No", "target": "back"},
    ]
    },
    "submenu_song_options": {
    "title": "Song Options",
    "options": [  # These will be updated dynamically when entering the menu
        {"label": "Play Song", "target": None, "action_type": "python", "action": "play_single_song"},
        {"label": "Apply Spatial Audio", "target": None, "action": "apply_spatial_audio", "action_type": "python"},
        {"label": "Back", "target": "back"}
    ]
    },
    "submenu_spatial_options": {
    "title": "Spatial Song Options",
    "options": [  # These will be updated dynamically when entering the menu
        {"label": "Play Spatial Song", "target": None, "action": "play_spatial_song", "action_type": "python"},
        {"label": "Play Stems", "target": None, "action": "play_spatial_song", "action_type": "python"},
        {"label": "Back", "target": "back"}
    ]
    },
    "submenu_Settings": {
        "title": "Settings",
        "options": [
            {"label": "Change Time", "target": None, "action" : "date", "action_type" : "shell"},
            {"label": "Change Profile", "target": "submenu_profiles", "action_type" : "static"},
            {"label": "Edit Profile", "target": None, "action" : "edit_profiles", "action_type" : "python"},
            {"label": "Run Calibration", "target": None, "action" : "run_calibration", "action_type" : "python"},
            {"label": "Back", "target": "back"}
        ]
    },
    "submenu_Music_Player": {
        "title": "Music Player",
        "options": [
            {"label": "Play Music", "target": None, "action_type" : "python", "action" : "play_song"},
            {"label": "Play/Pause Music", "target": None, "action_type" : "python", "action" : "play_pause_song"},
            {"label": "Skip Song", "target": None, "action_type" : "python", "action" : "skip_song"},
            {"label": "Previous Song", "target": None, "action_type" : "python", "action" : "unskip_song"},
            {"label": "Loop Music", "target": None, "action_type" : "python", "action" : "loop_song"},
            {"label": "Shuffle Music", "target": None, "action_type" : "python", "action" : "shuffle_song"},
            {"label": "Back", "target": "back"}
        ]
    }
}

def play_selected_song():
    if selected_song:
        subprocess.run(f'ffplay -nodisp -autoexit "Music/{selected_song}"', shell=True)
    else:
        print("No song selected")


def play_spatial_song():
    print("Check if pickle file exists")
    stems_directory = f"Spatial/{selected_song}"
    if selected_song and os.path.exists(stems_directory):
        print("Loaded Profile: ", Loaded_Profile)
        spatial_stems = apply_bulk_hrtf(stems_directory, Loaded_Profile=Loaded_Profile)
        print("Generate summed song")
        final_output = summed_signal(spatial_stems['vocals'], spatial_stems['bass'], spatial_stems['other'], spatial_stems['drums'])
        print("Write Stems to flac")
        sf.write('Spatial/output.flac', final_output, 44100)
        print("Play stems with ffmpeg")
        subprocess.run(f'ffplay -nodisp -autoexit "Spatial/output.flac"', shell=True)
        try:
            os.remove('Spatial/output.flac')   
            print("File removed.")
        except FileNotFoundError:
            print("File not found.")
        except PermissionError:
            print("No permission to delete the file.")
    else:
        return "File not found"

def play_spatial_song_old():
    print("Check if pickle file exists")
    stems_directory = f"Spatial/{selected_song}"
    if selected_song and os.path.exists(stems_directory):
        print("Loaded Profile: ", Loaded_Profile)
        spatial_stems = apply_bulk_hrtf(stems_directory, Loaded_Profile=Loaded_Profile)
        print("Generate summed song")
        final_output = summed_signal(spatial_stems['vocals'], spatial_stems['bass'], spatial_stems['other'], spatial_stems['drums'])
        print("Write Stems to flac")
        sf.write('Spatial/output.flac', final_output, 44100)
        print("Play stems with ffmpeg")
        subprocess.run(f'ffplay -nodisp -autoexit "Spatial/output.flac"', shell=True)
        try:
            os.remove('Spatial/output.flac')   
            print("File removed.")
        except FileNotFoundError:
            print("File not found.")
        except PermissionError:
            print("No permission to delete the file.")
    else:
        return "File not found"

# Function for loading music files dynamically into pages
def load_profile_files(directory="user_profiles"):
    # Global Variables
    global all_music_files, current_page
    page = 0

    profile_folder = directory # Path to music folder
    try:
        files = os.listdir(profile_folder) # Load folder
        profiles = sorted([f for f in files if f.lower().endswith(".json")])
        current_page = page # Select starting page from parameter variable

        # Determine how many songs to put per page. Adjustable from global variable "items_per_page"
        start = page * items_per_page
        end = start + items_per_page
        current_files = profiles[start:end]

        # Dynamically load songs into options so they are displayed on the screen
        options = [{"label": f, "target": None, "action": "select_profile", "action_type": "python"} for f in current_files]

        # Determine if Previous Page button is shown
        if page > 0:
            options.append({"label": "Previous Page", "target": "prev_page"})
        
        # Determine if Next Page button is shown
        if end < len(all_music_files):
            options.append({"label": "Next Page", "target": "next_page"})

        # Back button to leave library added to end
        options.append({"label": "Back", "target": "back"})
        menus["submenu_profiles"]["options"] = options
    except Exception as e:
        menus["submenu_profiles"]["options"] = [
            {"label": f"Error loading files: {e}", "target": "back"},
            {"label": "Back", "target": "back"}
        ]

# Function for loading music files dynamically into pages
def load_music_files(directory="Music", page=0):
    # Global Variables
    global all_music_files, current_page

    music_folder = directory # Path to music folder
    try:
        files = os.listdir(music_folder) # Load folder
        if directory == "Music":
            mp3s = sorted([f for f in files if f.lower().endswith(".mp3")]) # Sort for .mp3
            flac = sorted([f for f in files if f.lower().endswith(".flac")]) # Sort for .flac
            wav = sorted([f for f in files if f.lower().endswith(".wav")]) # Sort for .wav
            all_music_files = sorted(mp3s + flac + wav)
        elif directory == "Spatial":
            pkl = sorted([f for f in files if f.lower().endswith(".pkl")]) # Sort for .pkl
            h5 = sorted([f for f in files if f.lower().endswith(".h5")]) # Sort for .h5
            all_music_files = sorted(pkl + h5)
        current_page = page # Select starting page from parameter variable

        # Determine how many songs to put per page. Adjustable from global variable "items_per_page"
        start = page * items_per_page
        end = start + items_per_page
        current_files = all_music_files[start:end]

        # Dynamically load songs into options so they are displayed on the screen
        options = [{"label": f, "target": None, "action": f"echo Playing {f}", "action_type": "shell"} for f in current_files]

        # Determine if Previous Page button is shown
        if page > 0:
            options.append({"label": "Previous Page", "target": "prev_page"})
        
        # Determine if Next Page button is shown
        if end < len(all_music_files):
            options.append({"label": "Next Page", "target": "next_page"})

        # Back button to leave library added to end
        options.append({"label": "Back", "target": "back"})
        if directory == "Music":
            menus["submenu_songs"]["options"] = options
        elif directory == "Spatial":
            menus["submenu_spatial_songs"]["options"] = options
    except Exception as e:
        if directory == "Music":
            menus["submenu_songs"]["options"] = [
                {"label": f"Error loading files: {e}", "target": "back"},
                {"label": "Back", "target": "back"}
            ]
        elif directory == "Spatial":
            menus["submenu_spatial_songs"]["options"] = [
            {"label": f"Error loading files: {e}", "target": "back"},
            {"label": "Back", "target": "back"}
        ]


# function for starting the Speech to Text thread
def start_voice():
    global recognition_running, recognition_thread

    if recognition_running:
        print("this button is working upon press, ignoring presses")
        return
    
    def recognition_wrapper():
        global recognition_running
        recognition_running = True
        try:
            stt.start_voice_recognition()
        except Exception as e:
            print(f"voice recognition crash {e}")
        finally: 
            recognition_running = False
            print("voice recognition ended")
    #start_voice_recognition()
    #Run the voice recognition in a seperate thread
    recognition_thread = threading.Thread(target=recognition_wrapper)
    recognition_thread.daemon=True # Daemonize the thread to allow it to exit with the main program
    recognition_thread.start() # Start the recognition process

def clear_console(): # For manually clearing the console
    os.system('cls' if os.name == 'nt' else 'clear')

def run_spatial_audio_helper():
    run_spatial_audio(f"Music/{selected_song}")

def change_profile_wrapper():
    global current_index, Loaded_Profile
    Loaded_Profile = selected_song
    temp_str = Loaded_Profile.removesuffix(".json")
    current_index = 0
    
    while len(menu_stack) > 2:
            menu_stack.pop()

    return f"Profile {temp_str} loaded Successfully"

def play_pause():
    if song_paused == True:
        stt.resume_song()
    elif song_paused == False:
        stt.pause_song()

    
def run_calibration_wrapper():
    """Wrapper to call run_calibration_function with GPIO buttons."""
    try:
        output = run_calibration_function(
            up=UP_BUTTON,
            down=DOWN_BUTTON,
            left=LEFT_BUTTON,
            right=RIGHT_BUTTON,
            enter=SELECT_BUTTON
        )
    except Exception as e:
        output = f"Calibration error: {str(e)}"
    return output

def run_edit_profiles_wrapper():
    """Wrapper to call run_calibration_function with GPIO buttons."""
    try:
        output = edit_profile(
            up=UP_BUTTON,
            down=DOWN_BUTTON,
            left=LEFT_BUTTON,
            right=RIGHT_BUTTON,
            enter=SELECT_BUTTON
        )
    except Exception as e:
        output = f"Calibration error: {str(e)}"
    return output

def play_button_wrapper():
    stt.play_button(selected_song)
    #this is the new function for threading to be able to track when a song ended and go on to the next
    def monitor_song():
        while True:
            stt.checkFinish()
            time.sleep(0.5)
            
    thread = threading.Thread(target=monitor_song, daemon=True)
    thread.start()

# This function dictionary is for storing functions as actions. In the form { "Action_Name" : function_name }
function_dictionary = {
    # Default setup for function dictionary. Just add your name and function to use it in the submenus
    "default_function" : clear_console, 
    "start_voice" : start_voice,
    "play_song" : stt.play_buttons,
    "play_single_song" : play_button_wrapper,
    "run_calibration" : run_calibration_wrapper,
    "apply_spatial_audio" : run_spatial_audio_helper,
    "play_spatial_song" : play_spatial_song,
    "edit_profiles" : run_edit_profiles_wrapper,
    "select_profile" : change_profile_wrapper,
    "play_pause_song" : play_pause,
    "skip_song" : stt.next_song,
    "unskip_song" : stt.previous_song,
    "loop_song" : stt.toggle_loop,
    "shuffle_song" : stt.toggle_shuffle
}

def handle_selection(stdscr, selected_option, h, w, current_menu_key):
    # Global variable
    global current_index, directory
    # Load labels, targets, and actions
    label = selected_option["label"] # Labels are just the name of the option, it's what shows on the screen
    target = selected_option.get("target") # Targets decide where the selection goes next, can be None
    action = selected_option.get("action") # Action is what action will be performed when selected
    action_type = selected_option.get("action_type", "shell") # Action_type lets us use different types of actions like python functions and shell commands

    # If back is sent, and we're not on main menu, go back a page
    if target == "back":
        if len(menu_stack) > 1:
            menu_stack.pop()
            current_index = 0
    # Next_page and prev_page are specifically for menus where it dynamically loads content into "pages"
    elif target == "next_page": # Move forward a page
        load_music_files(directory, current_page + 1)
        current_index = 0
    elif target == "prev_page": # Move back a page
        load_music_files(directory, current_page - 1)
        current_index = 0
    elif target and target in menus: # If there are no pages, check the target and go there
    # Check if we need to generate the submenu dynamically
        if selected_option.get("action_type") == "dynamic" and target == "submenu_songs":
            directory = "Music"
            load_music_files(directory, page=0)
        if selected_option.get("action_type") == "dynamic" and target == "submenu_spatial_songs":
            directory = "Spatial"
            load_music_files(directory, page=0)
        if selected_option.get("action_type") == "static":
            directory = "user_profiles"
            load_profile_files(directory=directory)
        menu_stack.append(target)
        current_index = 0
    elif current_menu_key == "submenu_songs" and label.lower() not in ["next page", "previous page", "back"]:
        # User selected a song
        global selected_song
        selected_song = label  # Save it for later
        menu_stack.append("submenu_song_options")
        current_index = 0
    elif current_menu_key == "submenu_spatial_songs" and label.lower() not in ["next page", "previous page", "back"]:
        # User selected a song
        selected_song = label  # Save it for later
        menu_stack.append("submenu_spatial_options")
        current_index = 0
    elif current_menu_key == "submenu_profiles" and label.lower() not in ["next page", "previous page", "back"]:
        # User selected a song
        selected_song = label  # Save it for later
        menu_stack.append("submenu_profile_options")
        current_index = 0
    elif action: # Load the action and run it
        if action_type == "shell":# If the loaded action is of type shell, run the shell command using a subprocess. This is done because curses is running in our current shell, so we need a different one
            try:
                result = subprocess.run(action, shell=True, text=True, capture_output=True)
                output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            except Exception as e:
                output = f"Shell Error: {e}"
        elif action_type == "python": # If the action is of type python function, load it and call it
            func = function_dictionary.get(action)
            if func:
                try:
                    curses.endwin()
                    output = func()
                except Exception as e:
                    output = f"Python Error: {e}"
                finally:
                    stdscr = curses.initscr()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.clear()
                    curses.doupdate()
            else:
                output = f"Function '{action}' not found"
        else:
            output = f"Unknown action type: {action_type}"

        stdscr.clear()
        if output == None:
            output = "Finished Task"
        lines = str(output).split("\n")
        for i, line in enumerate(lines):
            y = max(0, min(h - 1, h // 2 - len(lines) // 2 + i))
            x = max(0, min(w - 1, w // 2 - len(line) // 2))
            try:
                stdscr.addstr(y, x, line[:w - x])
            except curses.error:
                pass
        stdscr.refresh()
        time.sleep(5)
    else: # Target has no action attached
        stdscr.clear() 
        message = f"You selected: {label}"
        y = max(0, min(h - 1, h // 2))
        x = max(0, min(w - 1, w // 2 - len(message) // 2))
        try:
            stdscr.addstr(y, x, message[:w - x])
        except curses.error:
            pass
        stdscr.refresh()
        time.sleep(1)



def draw_menu(stdscr):
    # Global variables
    global current_index, up_pressed, down_pressed, select_pressed, back_pressed, vol_down_pressed, vol_up_pressed, GLOBAL_VOLUME

    curses.curs_set(0) # Set curser to origin
    stdscr.nodelay(True)
    stdscr.keypad(True) # Enable keyboard for debug
    curses.start_color() # Enable colors
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN) # Default colors

    while True:
        # Clear screen and double check height and width. This allows for real-time resizing
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # --- Time Display ---
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")  # e.g., 04:15:22 PM
        stdscr.addstr(0, w - len(time_str) - 1, time_str)
        
        # Battery stuff but I don't have the PSU so I'll touch it later 
        # will return Int or truncated calculated battery percentage
        battery = get_battery_info()
        stdscr.addstr(1, w - len(battery) - 1, str(int(battery[1])) + "%") # Battery percentage
        stdscr.addstr(2, w - len(str(GLOBAL_VOLUME)) - 1, str(GLOBAL_VOLUME) + "%") # Volume Battery percentage
        

        # Menu variables
        current_menu_key = menu_stack[-1] # Get current menu
        current_menu = menus[current_menu_key] # ^^^
        options = current_menu["options"] # Get options section for the page
        title = current_menu["title"] # Get Title for the page

        stdscr.addstr(1, w // 2 - len(title) // 2, title, curses.A_BOLD) # Write title to middle of screen

        # Iterate through all options and print their labels to the middle of the screen
        for idx, option in enumerate(options):
            label = option["label"]
            x = w // 2 - len(label) // 2
            y = h // 2 - len(options) // 2 + idx
            if idx == current_index: # Decides which option is selected and colors it
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(y, x, label) # Write colored option to the screen
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(y, x, label) # write non-colored options to screen

        stdscr.refresh() # Refresh to push changes to screen

        # Keyboard Navigation for when there are no hardware buttons
        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        # Exactly the same logic as the hardware buttons, but using keyboard for testing
        if key == curses.KEY_UP:
            current_index = (current_index - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_index = (current_index + 1) % len(options)
        elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
            selected_option = options[current_index]
            handle_selection(stdscr, selected_option, h, w, current_menu_key)
        elif key in [curses.KEY_BACKSPACE, 127]:
            start_voice()

        # GPIO button input
        # Move up through options
        if UP_BUTTON and UP_BUTTON.is_pressed and not up_pressed:
            current_index = (current_index - 1) % len(options)
            up_pressed = True
        elif UP_BUTTON and not UP_BUTTON.is_pressed:
            up_pressed = False

        # move down through options
        if DOWN_BUTTON and DOWN_BUTTON.is_pressed and not down_pressed:
            current_index = (current_index + 1) % len(options)
            down_pressed = True
        elif DOWN_BUTTON and not DOWN_BUTTON.is_pressed:
            down_pressed = False

        # If select button is pressed, select the current index and use handle_selection to load next screen
        if SELECT_BUTTON and SELECT_BUTTON.is_pressed and not select_pressed:
            selected_option = options[current_index]
            handle_selection(stdscr, selected_option, h, w, current_menu_key)
            select_pressed = True
        elif SELECT_BUTTON and not SELECT_BUTTON.is_pressed:
            select_pressed = False

        # If the hardware back button is pressed, start Speech to Text program
        if BACK_BUTTON.is_pressed and not back_pressed:
            start_voice()
            back_pressed = True
        elif back_pressed and not BACK_BUTTON.is_pressed:
            back_pressed = False
            
        # If the hardware Volume is pressed, change volume
        if VOLUME_UP.is_pressed and not vol_up_pressed:
            volume_button_wrapper(10,GLOBAL_VOLUME)
            GLOBAL_VOLUME=GLOBAL_VOLUME + 10
            if GLOBAL_VOLUME > 100: 
                GLOBAL_VOLUME = 100
            vol_up_pressed = True
        elif vol_up_pressed and not VOLUME_UP.is_pressed:
            vol_up_pressed = False    
        
        # If the hardware Volume is pressed, change volume
        if VOLUME_DOWN.is_pressed and not vol_down_pressed:
            volume_button_wrapper(-10,GLOBAL_VOLUME)
            GLOBAL_VOLUME=GLOBAL_VOLUME -10
            if GLOBAL_VOLUME < 0: 
                GLOBAL_VOLUME = 0
            vol_down_pressed = True
        elif vol_down_pressed and not VOLUME_DOWN.is_pressed:
            vol_down_pressed = False      
       
        # Sleep so the screen doesn't freak out from too fast refreshing
        time.sleep(0.05)

 
   
def volume_button_wrapper(increment, GLOBAL_VOLUME):
    """Wrapper to call volume  with GPIO buttons."""
    try:
        output = stt.update_volume(increment, GLOBAL_VOLUME)
    except Exception as e:
        output = f"volume button error: {str(e)}"
    return output


def main():
    try:
        curses.wrapper(draw_menu) # draw_menu contains the main loop for this file
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
