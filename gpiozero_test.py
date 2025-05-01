import gpiozero as gpio
import time
import threading
from stt import start_voice_recognition

def button_callback():
    print("I'm alive!")

def start_voice():
    #Run the voice recognition in a seperate thread
    recognition_thread = threading.Thread(target=start_voice_recognition)
    recognition_thread.daemon=True # Daemonize the thread to allow it to exit with the main program
    recognition_thread.start() # Start the recognition process

SELECT_BUTTON = gpio.Button(26)
BACK_BUTTON = gpio.Button(16)
SELECT_BUTTON.when_activated = button_callback
BACK_BUTTON.when_activated = start_voice

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Closing")