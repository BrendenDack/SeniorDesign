import os
import time
import subprocess
import sys
import threading
import select

# Add parent directory to sys.path for external modules
sys.path.append("../")

# Global variables for voice recognition
recognition_running = False
recognition_thread = None

try:
    from stt import start_voice_recognition
except (ModuleNotFoundError, Exception) as e:
    def start_voice_recognition():
        print(f"Voice recognition unavailable: {str(e)}. Check if 'vosk-model-small-en-us-0.15' is in ~/SeniorDesignCode/github_code/SeniorDesign/")
    print(f"Warning: Failed to load 'stt' module or Vosk model: {str(e)}. Voice recognition disabled. Ensure 'vosk-model-small-en-us-0.15' is in ../")

try:
    from CalibrateV3 import run_calibration_function
except (ModuleNotFoundError, Exception) as e:
    def run_calibration_function(button_manager=None):
        print(f"Calibration unavailable: 'CalibrateV3' module not found: {str(e)}")
        return "Calibration failed: Module not found"
    print(f"Warning: 'CalibrateV3' module not found. Calibration disabled.")

try:
    from utility import run_spatial_audio
except ModuleNotFoundError:
    def run_spatial_audio(*args, **kwargs):
        print("Spatial audio unavailable: 'utility' module not found")
    print("Warning: 'utility' module not found. Spatial audio disabled.")

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def start_voice():
    global recognition_running, recognition_thread
    if recognition_running:
        print("Voice recognition already running, ignoring press")
        return
    def recognition_wrapper():
        global recognition_running
        recognition_running = True
        try:
            start_voice_recognition()
        except Exception as e:
            print(f"Voice recognition error: {e}")
        finally:
            recognition_running = False
            print("Voice recognition ended")
    recognition_thread = threading.Thread(target=recognition_wrapper)
    recognition_thread.daemon = True
    recognition_thread.start()

def run_calibration_wrapper(button_manager=None):
    """Run CalibrateV3.py as a subprocess, mapping button inputs to keyboard."""
    calibrate_path = "/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/CalibrateV3.py"
    if not os.path.exists(calibrate_path):
        print(f"Calibration unavailable: {calibrate_path} not found")
        return "Calibration failed: File not found"

    try:
        # Start subprocess with piped stdin/stdout
        process = subprocess.Popen(
            ["python3", calibrate_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        output = []
        error = []

        # Thread to capture output
        def capture_output():
            for line in process.stdout:
                output.append(line)
                print(line, end='', flush=True)
            for line in process.stderr:
                error.append(line)
                print(line, end='', flush=True)

        output_thread = threading.Thread(target=capture_output)
        output_thread.daemon = True
        output_thread.start()

        # Poll buttons and keyboard
        while process.poll() is None:
            if button_manager:
                # Map button states to keyboard inputs
                if hasattr(button_manager, 'up') and button_manager.up.is_pressed:
                    process.stdin.write('w\n')
                    process.stdin.flush()
                elif hasattr(button_manager, 'down') and button_manager.down.is_pressed:
                    process.stdin.write('s\n')
                    process.stdin.flush()
                elif hasattr(button_manager, 'right') and button_manager.right.is_pressed:
                    process.stdin.write('d\n')
                    process.stdin.flush()
                elif hasattr(button_manager, 'left') and button_manager.left.is_pressed:
                    process.stdin.write('a\n')
                    process.stdin.flush()
                elif hasattr(button_manager, 'select') and button_manager.select.is_pressed:
                    process.stdin.write('\n')
                    process.stdin.flush()
                elif hasattr(button_manager, 'back') and button_manager.back.is_pressed:
                    process.stdin.write('r\n')
                    process.stdin.flush()

            # Check keyboard input non-blocking
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                char = sys.stdin.read(1)
                process.stdin.write(char)
                process.stdin.flush()

            time.sleep(0.1)

        output_thread.join()
        process.wait()

        if process.returncode == 0:
            return ''.join(output) or "Calibration completed"
        else:
            return f"Calibration failed: {''.join(error)}"
    except Exception as e:
        print(f"Calibration error: {str(e)}")
        return f"Calibration failed: {str(e)}"

FUNCTION_DICTIONARY = {
    "default_function": clear_console,
    "start_voice": start_voice,
    "play_song": lambda: subprocess.run(f'ffplay -nodisp -autoexit "Music/{selected_song}"', shell=True) if selected_song else print("No song selected"),
    "run_calibration": run_calibration_wrapper,
    "apply_spatial_audio": lambda: run_spatial_audio(f"Music/{selected_song}") if selected_song else print("No song selected"),
}