import gpiozero as gpio # Main GPIO Module to control buttons
from gpiozero.pins.mock import MockFactory
from gpiozero.exc import GPIOZeroError
import time
import os
import curses as screen # Allow us to draw in the terminal for a more UI-like look
import threading # Threading for Voice recognition - Make new thread to not stop current code
from stt import start_voice_recognition # Runs voice recognition when called

# GLOBAL VARIABLES
recognition_thread = None
recognition_running = False

menus = {
    "main" : {
        "title" : "Main Menu",
        "options" : ["Library", "Settings", "Player"]
    },
    "library" : {
        "title" : "Library",
        "options" : ["Songs"]
    },
    "settings" : {
        "title" : "Settings",
        "options" : ["Change Time", "Change Profile", "Storage Space: "]
    },
    "player" : {
        "title" : "Music Player",
        "options" : ["Current Track:", "Time remaining: ", "Actions"]
    }
}
menu_stack = ["main"]
current_index = 0

up_pressed = down_pressed = select_pressed = back_pressed = False

# Mock pins for testing - Remove if you have real buttons to test with
gpio.Device.pin_factory = MockFactory()

# GPIO Pin Definitions
# GPIO 26: Select
# GPIO 16: Back
# GPIO 4: Up
# GPIO 22: Right
# GPIO 20: Down
# GPIO 21: Left
# GPIO 23: Volume Up
# GPIO 24: Volume Down

# HELPER FUNCTIONS
try:
    # Claim all button GPIOs
    SELECT_BUTTON =  gpio.Button(26, pull_up=True, bounce_time=0.1)
    BACK_BUTTON =  gpio.Button(16, pull_up=True, bounce_time=0.1)
    UP_BUTTON =  gpio.Button(4, pull_up=True, bounce_time=0.1)
    RIGHT_BUTTON =  gpio.Button(22, pull_up=True, bounce_time=0.1)
    DOWN_BUTTON =  gpio.Button(20, pull_up=True, bounce_time=0.1)
    LEFT_BUTTON =  gpio.Button(21, pull_up=True, bounce_time=0.1)
    VOLUME_UP =  gpio.Button(23, pull_up=True, bounce_time=0.1)
    VOLUME_DOWN =  gpio.Button(24, pull_up=True, bounce_time=0.1)
except GPIOZeroError:
    SELECT_BUTTON = BACK_BUTTON = UP_BUTTON = RIGHT_BUTTON = DOWN_BUTTON = LEFT_BUTTON = VOLUME_DOWN = VOLUME_UP = None
    print(f"Buttons init Failed. Could not claim Buttons.")
    time.sleep(3)


def start_voice():
    global recognition_running, recognition_thread

    if recognition_running:
        print("this button is working upon press, ignoring presses")
        return
    
    def recognition_wrapper():
        global recognition_running
        recognition_running = True
        try:
            start_voice_recognition()
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

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def handle_selection(stdscr, selected_option, h, w):
    global current_index

    if selected_option == "Back":
        if len(menu_stack) > 1:
            menu_stack.pop()
            current_index = 0
    elif selected_option in menus:
        menu_stack.append(selected_option)
        current_index = 0
    else:
        stdscr.clear()
        stdscr.addstr(h // 2, w // 2 - len("You selected: " + selected_option) // 2, f"You selected: {selected_option}")
        stdscr.refresh()
        time.sleep(1)

def draw_menu(stdscr):
    global current_index, up_pressed, down_pressed, select_pressed, back_pressed
    
    screen.curs_set(0)
    stdscr.nodelay(True)

    stdscr.keypad(True) # Read keyboard input for debug without a setup
    last_key_time = time.time()

    screen.start_color()
    screen.init_pair(1, screen.COLOR_BLACK, screen.COLOR_CYAN)

    
    while True:
        stdscr.clear() # Clear Screen
        h, w = stdscr.getmaxyx() # Get screen dimensions

        current_menu_key = menu_stack[-1]
        current_menu = menus[current_menu_key]
        title = current_menu["title"]
        options = current_menu["options"]

        stdscr.addstr(1, w // 2 - len(title) // 2, title, screen.A_BOLD)

       # Draw options
        for idx, item in enumerate(options):
            x = w // 2 - len(item) // 2
            y = h // 2 - len(options) // 2 + idx
            if idx == current_index:
                stdscr.attron(screen.color_pair(1))
                stdscr.addstr(y, x, item)
                stdscr.attroff(screen.color_pair(1))
            else:
                stdscr.addstr(y, x, item)
        
        stdscr.refresh()
        
        # Keyboard input (If GPIOZero isn't working)
        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == screen.KEY_UP:
            current_index = (current_index - 1) % len(options)
        elif key == screen.KEY_DOWN:
            current_index = (current_index + 1) % len(options)
        elif key in [screen.KEY_ENTER, ord('\n'), ord('\r')]:
            handle_selection(stdscr, options[current_index], h, w)
        elif key == screen.KEY_BACKSPACE or key == 127:
            handle_selection(stdscr, "Back", h, w)

        # Button input (if GPIOZero is working)
        if UP_BUTTON.is_pressed and not up_pressed:
            current_index = (current_index + 1) % len(options)
            up_pressed = True
        elif up_pressed and not UP_BUTTON.is_pressed:
            up_pressed = False
        
        if DOWN_BUTTON.is_pressed and not down_pressed:
            current_index = (current_index - 1) % len(options)
            down_pressed = True
        elif down_pressed and not DOWN_BUTTON.is_pressed:
            down_pressed = False

        if SELECT_BUTTON.is_pressed and not select_pressed:
            handle_selection(stdscr, options[current_index], h, w)
            select_pressed = True
        elif not SELECT_BUTTON.is_pressed and select_pressed:
            select_pressed = False
        
        if BACK_BUTTON.is_pressed and not back_pressed:
            handle_selection(stdscr, "Back", h, w)
            back_pressed = True
        elif back_pressed and not BACK_BUTTON.is_pressed:
            back_pressed = False

        time.sleep(0.05)


def main():
    # Boot Display
    clear_console()
    print("Welcome to the Immersive Audio Player!")
    time.sleep(3)
    clear_console()
    screen.wrapper(run_menu)

def run_menu(stdscr):
    screen.start_color()
    screen.init_pair(1, screen.COLOR_BLACK, screen.COLOR_CYAN)
    try:
        draw_menu(stdscr)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()