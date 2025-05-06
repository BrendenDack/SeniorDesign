import gpiozero as gpio
import time
import threading
from stt import start_voice_recognition

recognition_thread = None
recognition_running = False

def button_callback():
    print("I'm alive!")

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

SELECT_BUTTON =  gpio.Button(12, pull_up=True, bounce_time=0.1)
BACK_BUTTON = gpio.Button(26, pull_up=True, bounce_time=0.1)
SELECT_BUTTON.when_activated = button_callback
BACK_BUTTON.when_activated = start_voice

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Closing")
