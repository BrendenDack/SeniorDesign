#!/usr/bin/env python3
import numpy as np
from scipy.io import loadmat
from scipy import signal
import pyaudio
import time
import json
import os
import sys
from pathlib import Path
import platform
import random
import termios
import tty

from PIL import Image, ImageDraw, ImageFont

# Configuration
DURATION = 1.5
HRTF_PATH = Path("HRIRs/")
PROFILES_DIR = Path("user_profiles")
FS = 48000  # Force modern sample rate
SUPPRESS_ERRORS = True  # Set to False to debug audio errors
NORMALIZED_ANGLES = [-180, -90, 0, 90]  # Base angles for snapping

font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
font_menu = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

def get_available_angles(hrtf_path: Path, subject: str) -> list:
    """Load available angles for a subject from HRIR files."""
    angles = []
    for file in hrtf_path.glob(f"Subject_{subject}_*_0.mat"):
        try:
            angle = int(file.stem.split('_')[-2])
            angles.append(angle)
        except ValueError:
            continue
    return sorted(angles)

def snap_to_nearest_angle(target: float, available_angles: list) -> float:
    """Snap target angle to the nearest available angle."""
    return available_angles[np.argmin(np.abs(np.array(available_angles) - target))]

def generate_swept_sine(duration: float, fs: int) -> np.ndarray:
    """Generate a linear chirp for better audibility."""
    t = np.linspace(0, duration, int(duration * fs))
    return 0.05 * signal.chirp(t, f0=500, f1=4000, t1=duration, method='linear')

def play_audio(audio_data: np.ndarray, fs: int) -> bool:
    """
    Robust audio playback with OS-level stderr suppression.
    Uses device index 0 (expected: TX USB Audio, hw:2,0).
    Set SUPPRESS_ERRORS=False for debugging.
    """
    print(f"Initializing audio playback (SUPPRESS_ERRORS={SUPPRESS_ERRORS})...")
    print(f"Python version: {platform.python_version()}, PyAudio version: {pyaudio.__version__}")
    sys.stdout.flush()

    p = None
    stream = None
    try:
        if SUPPRESS_ERRORS:
            stderr_fd = sys.stderr.fileno()
            stderr_save = os.dup(stderr_fd)
            devnull_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd, stderr_fd)
            os.close(devnull_fd)

            p = pyaudio.PyAudio()
            device_index = 0
            dev_info = p.get_device_info_by_index(device_index)
            if dev_info['maxOutputChannels'] < 2 or dev_info['hostApi'] != 0:
                raise RuntimeError(f"Device at index {device_index} does not support stereo ALSA output")
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=int(fs),
                output=True,
                output_device_index=device_index
            )
            stream.write(audio_data.astype(np.float32).tobytes())
            stream.stop_stream()
            stream.close()
            stream = None
            p.terminate()
            p = None

            os.dup2(stderr_save, stderr_fd)
            os.close(stderr_save)
        else:
            p = pyaudio.PyAudio()
            device_index = 0
            dev_info = p.get_device_info_by_index(device_index)
            if dev_info['maxOutputChannels'] < 2 or dev_info['hostApi'] != 0:
                raise RuntimeError(f"Device at index {device_index} does not support stereo ALSA output")
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=int(fs),
                output=True,
                output_device_index=device_index
            )
            stream.write(audio_data.astype(np.float32).tobytes())
            stream.stop_stream()
            stream.close()
            stream = None
            p.terminate()
            p = None

        print(f"Selected audio device: {dev_info['name']} (Index: {device_index})")
        sys.stdout.flush()
        return True
    except Exception as e:
        print(f"Audio Error: {str(e)}")
        sys.stderr.flush()
        return False
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        if p is not None:
            p.terminate()
        sys.stdout.flush()
        sys.stderr.flush()

def get_input(up=None, down=None, left=None, right=None, enter=None) -> str:
    """Read a single input from GPIO buttons."""
    time.sleep(0.2)
    if up and up.is_pressed:
        return 'w'
    if down and down.is_pressed:
        return 's'
    if right and right.is_pressed:
        return 'd'
    if left and left.is_pressed:
        return 'a'
    if enter and enter.is_pressed:
        return '\n'
    return ''

def get_angle_input(current_angle: float, preset_angle: float, stimulus: np.ndarray, spatial_audio: np.ndarray, fs: int, up=None, down=None, left=None, right=None, enter=None, lcd=None) -> float:
    # Refactor in Pillow for display
    global font_large, font_menu
    
    #lcd.clear()
    
    # Create a persistent image for the function execution
   
    y_offset = 17
    
    """
    Interactively adjust the perceived angle with deviation feedback.
    """
    print("\nAdjust the perceived angle (WASD/buttons for adjustments, r to replay):")
    #replay needs to be maped to back button to include feature. for simplicity it has been removed
    print("  w/up: +10°, s/down: -10°, d/right: +1°, a/left: -1°, r: replay")
    print("Press enter button to confirm the current angle.")
    
    angle = current_angle
    
    while True:
        
        # Create an image at the start so it persists across function execution
        img = Image.new("RGB", (320, 240), "WHITE")
        draw = ImageDraw.Draw(img)
        
        # !!!
        # Draw static UI elements 
        play_msg = "Playing test sound..."
        print(play_msg)
        play_x = (320 - draw.textlength(play_msg, font=font_menu)) // 2
        draw.text((play_x, 40), play_msg, font=font_menu, fill="BLACK")

        AnglePrompt1 = "Adjust the perceived angle "
        AP1_x = (320 - draw.textlength(AnglePrompt1, font=font_menu)) // 2
        draw.text((AP1_x, 40+y_offset), AnglePrompt1, font=font_menu, fill="BLACK")

        AnglePrompt2 = "  up/down: 10°, right/left: 1°"
        AP2_x = (320 - draw.textlength(AnglePrompt2, font=font_menu)) // 2
        draw.text((AP2_x, 40+2*y_offset), AnglePrompt2, font=font_menu, fill="BLACK")

        AnglePrompt3 = "enter to confirm angle."
        AP3_x = (320 - draw.textlength(AnglePrompt3, font=font_menu)) // 2
        draw.text((AP3_x, 40+3*y_offset), AnglePrompt3, font=font_menu, fill="BLACK")
        
        deviation = abs(angle - preset_angle)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        
        # Clear only the previous angle display before updating new values
        #draw.rectangle([(0, 160), (320, 220)], fill="WHITE")  # Erases previous angle text

        # Draw the updated angle information
        
        #AnglePrompt4 = f"Current angle: {angle:.1f}° (Deviation: {deviation:.1f}°)"
        AnglePrompt4 = f"Current angle: {angle:.1f}° "
        AP4_x = (320 - draw.textlength(AnglePrompt4, font=font_menu)) // 2  
        draw.text((AP4_x, 172+y_offset), AnglePrompt4, font=font_menu, fill="BLACK")

        img = img.rotate(90, expand=True)
        lcd.ShowImage(img)  # Refresh LCD with updated angle

        ch = get_input(up, down, left, right, enter)
        if not ch:
            continue
        if ch == '\n':
            print()
            return angle
        elif ch.lower() == 'w':
            angle += 10
        elif ch.lower() == 's':
            angle -= 10
        elif ch.lower() == 'd':
            angle += 1
        elif ch.lower() == 'a':
            angle -= 1
        elif ch.lower() == 'r' and abs(preset_angle) > 90:
            play_audio(spatial_audio, fs)
            print("Replayed test sound...")
        else:
            print(f"\nUnrecognized input: '{ch}'. Use WASD/buttons or r.")
            
            # Clear previous error message before displaying a new one
            #draw.rectangle([(0, 105), (320, 125)], fill="WHITE")

            error_msg = f"Unrecognized input: '{ch}'. Use WASD/buttons or r."
            err_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2  
            draw.text((err_x, 172+2*y_offset), error_msg, font=font_menu, fill="BLACK")

            lcd.ShowImage(img)

def calibration_routine(hrtf_subjects: list, normalized_angles: list, num_trials: int = 4, up=None, down=None, left=None, right=None, enter=None, lcd=None) -> dict:
    global font_menu, font_large

    """
    Calibration routine for multiple HRTF subjects.
    Randomly selects 4 angles per subject, snapped to available HRIR angles, prioritizing negative angles.
    """
    
    # Create an image at the start so it persists across function execution
    img = Image.new("RGB", (320, 240), "WHITE")
    draw = ImageDraw.Draw(img)
    

    # Ensure the first UI element is drawn before showing the image (avoid blank screen)
    draw.text((10, 10), "Starting Calibration...", font=font_menu, fill="BLACK")
    

    img = img.rotate(90, expand=True)
    lcd.ShowImage(img)  # Show initial display
    time.sleep(1)
    lcd.clear()

    calibration_data = {subject: {'preset_angles': [], 'responses': []} for subject in hrtf_subjects}
    
    for subject in hrtf_subjects:
        img = Image.new("RGB", (320, 240), "WHITE")
        draw = ImageDraw.Draw(img)

        available_angles = get_available_angles(HRTF_PATH, subject)
        if not available_angles:
            error_msg = f"No HRIR files found for Subject_{subject} in {HRTF_PATH}"
            print(error_msg)

            #draw.rectangle([(0, 40), (320, 70)], fill="WHITE")  # Clears error area before updating
            error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2
            draw.text((error_x, 50), error_msg, font=font_menu, fill="BLACK")

            lcd.ShowImage(img)  # Ensure error appears before skipping this subject
            time.sleep(1)
            continue
        
        print("snap to normalize")
        # Snap normalized angles to available angles
        snapped_angles = [snap_to_nearest_angle(angle, available_angles) for angle in normalized_angles]

        negative_angles = [a for a in snapped_angles if a < 0]
        positive_angles = [a for a in snapped_angles if a >= 0]
        if len(negative_angles) < 2:
            negative_angles = sorted([a for a in available_angles if a < 0])[:2]
            positive_angles = [a for a in snapped_angles if a >= 0] or sorted([a for a in available_angles if a >= 0])[:2]
        else:
            negative_angles = negative_angles[:2]
            positive_angles = positive_angles[:2]

        # Select 4 random angles
        trial_angles = negative_angles + random.choices(negative_angles + positive_angles, k=num_trials - len(negative_angles))
        random.shuffle(trial_angles)
        
        print("generate_swept_sine")
        stimulus = generate_swept_sine(DURATION, FS)
        
        for trial, preset_angle in enumerate(trial_angles):
            img = Image.new("RGB", (320, 240), "WHITE")
            draw = ImageDraw.Draw(img)
            
            msg = f"Calibrating for Subject_{subject}..."
            print(msg)
            msg_x = (320 - draw.textlength(msg, font=font_menu)) // 2  # Proper text centering
            draw.text((msg_x, 10), msg, font=font_menu, fill="BLACK")
            
            trial_msg = f"Trial {trial + 1} for Subject_{subject}"
            print(trial_msg)
            trial_x = (320 - draw.textlength(trial_msg, font=font_menu)) // 2
            
            trial_msg2 = f"Preset angle = {preset_angle}°"
            print(trial_msg2)
            trial_x2 = (320 - draw.textlength(trial_msg2, font=font_menu)) // 2
  
            draw.text((trial_x, 80), trial_msg, font=font_menu, fill="BLACK")
            draw.text((trial_x2, 80+17), trial_msg2, font=font_menu, fill="BLACK")

            hrtf_file = HRTF_PATH / f"Subject_{subject}_{int(preset_angle)}_0.mat"
            try:
                data = loadmat(str(hrtf_file))
                if 'hrir_left' not in data or 'hrir_right' not in data:
                    raise KeyError("Missing hrir_left or hrir_right in HRIR file")
                spatial_audio = np.column_stack([
                    signal.lfilter(data['hrir_left'].flatten(), 1, stimulus),
                    signal.lfilter(data['hrir_right'].flatten(), 1, stimulus)
                ])
            except Exception as e:
                error_msg = f"HRTF Processing Error for file {hrtf_file.name}: {str(e)}"
                print(error_msg)

                error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2
                draw.text((error_x, 100), error_msg, font=font_menu, fill="BLACK")

                continue
            
            print("play_audio")
            if play_audio(spatial_audio, FS):
                #play_msg = "Playing test sound..."
                #print(play_msg)
                #play_x = (320 - draw.textlength(play_msg, font=font_menu)) // 2
                #draw.text((play_x, 120), play_msg, font=font_menu, fill="BLACK")

                img = img.rotate(90, expand=True)
                lcd.ShowImage(img)
                # lcd.ShowImage(img)
                time.sleep(2.5)

                response = get_angle_input(preset_angle, preset_angle, stimulus, spatial_audio, FS, up, down, left, right, enter, lcd=lcd)
                time.sleep(0.1)

                calibration_data[subject]['preset_angles'].append(preset_angle)
                calibration_data[subject]['responses'].append(response)

    lcd.ShowImage(img)  # Final image update after calibration steps
    time.sleep(1)
    return calibration_data

def estimate_head_params(calibration_data: dict) -> tuple[dict, str]:
    """Estimate head parameters and classify as male (003) or female (019)."""
    male_norms = {'head_width': 15.2, 'head_length': 19.0, 'effective_radius': 8.6}
    female_norms = {'head_width': 14.5, 'head_length': 18.2, 'effective_radius': 8.2}

    params = {}
    for subject, data in calibration_data.items():
        if not data['responses']:
            continue
        mean_response = np.mean([abs(r - p) for r, p in zip(data['responses'], data['preset_angles'])])
        if mean_response > 20:
            print(f"Warning: High deviation ({mean_response:.1f}°) for Subject_{subject}. Rear angles may need iteration.")
        params[subject] = {
            'head_width': 0.45 * mean_response + 14.2,
            'head_length': 0.32 * mean_response + 17.8,
            'effective_radius': 0.51 * mean_response + 3.2
        }

    if not params:
        return male_norms, '003'

    min_dist = float('inf')
    selected_subject = '003'
    selected_params = params.get('003', male_norms)
    for subject, p in params.items():
        male_dist = sum((p[k] - male_norms[k])**2 for k in p) ** 0.5
        female_dist = sum((p[k] - female_norms[k])**2 for k in p) ** 0.5
        dist = min(male_dist, female_dist)
        if dist < min_dist:
            min_dist = dist
            selected_subject = subject
            selected_params = p
            if female_dist < male_dist:
                selected_subject = '019'

    return selected_params, selected_subject

def get_key() -> str:
    """Read a single key press without echoing."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def select_profile(up=None, down=None, enter=None, lcd=None) -> str:
    
    # Refactor for Pillow
    #lcd.clear()
    img = Image.new("RGB", (320, 240), "WHITE")
    draw = ImageDraw.Draw(img)

    """Prompt user to select a profile from user_profiles using WASD."""
    profiles_dir = PROFILES_DIR
    profiles = sorted(profiles_dir.glob("*.json"))

    if not profiles:
        error_msg = "No profiles found in user_profiles/. Creating default profile."
        print(error_msg)
        error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2  # Center text dynamically
        draw.text((error_x, 10), error_msg, font=font_menu, fill="BLACK")
        lcd.ShowImage(img)
        return "default_profile"

    selected_idx = 0
    while True:
        img = Image.new("RGB", (320, 240), "WHITE")
        draw = ImageDraw.Draw(img)
        os.system('cls' if os.name == 'nt' else 'clear')

        prompt_msg = "Select a profile"
        prompt_msg2 = "(Up/Down to navigate, Enter to select)"

        print("\n" + prompt_msg)

        # Compute individual text widths for correct centering
        prompt_x = (320 - draw.textlength(prompt_msg, font=font_menu)) // 2
        prompt_x2 = (320 - draw.textlength(prompt_msg2, font=font_menu)) // 2  # Center separately

        # Draw text with correct alignment
        draw.text((prompt_x, 30), prompt_msg, font=font_menu, fill="BLACK")
        draw.text((prompt_x2, 47), prompt_msg2, font=font_menu, fill="BLACK")


        y_offset = 70  # Adjusted for profile listing
        for i, profile in enumerate(profiles):
            marker = ">" if i == selected_idx else " "
            profile_text = f"{marker} {profile.name}"
            print(profile_text)
            profile_x = (320 - draw.textlength(profile_text, font=font_menu)) // 2
            draw.text((profile_x, y_offset), profile_text, font=font_menu, fill="BLACK")
            y_offset += 20  # Move down for each profile

        sys.stdout.flush()
        
        img = img.rotate(90, expand=True)
        lcd.ShowImage(img)

        ch = get_input(up=up, down=down, enter=enter)
        if ch in ('\r', '\n'):
            try:
                selected_profile = profiles[selected_idx].name
                print(f"\nSelected profile: {selected_profile}")
                
                selected_x = (320 - draw.textlength(selected_profile, font=font_menu)) // 2
                draw.text((selected_x, y_offset + 20), f"Selected profile: {selected_profile}", font=font_menu, fill="BLACK")

                return selected_profile
            
            except json.JSONDecodeError:
                error_msg = f"Error: {selected_profile} is not a valid JSON file."
                print(error_msg)
                error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2
                draw.text((error_x, y_offset + 40), error_msg, font=font_menu, fill="BLACK")
                return selected_profile
        
        elif ch.lower() == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch.lower() == 's' and selected_idx < len(profiles) - 1:
            selected_idx += 1

def run_calibration_function(up=None, down=None, left=None, right=None, enter=None, lcd=None) -> str:
    
    # Refactor in Pillow for display
    global font_large, font_menu
    
    # Clear screen and double-check height and width. This allows for real-time resizing
    img = Image.new("RGB", (320, 240), "WHITE")
    draw = ImageDraw.Draw(img)
    
    """Main calibration workflow."""
    print("=== HRTF Calibration ===")
    title_text = "=== HRTF Calibration ==="
    title_x = (320 - draw.textlength(title_text, font=font_menu)) // 2  # Center text horizontally
    draw.text((title_x, 5), title_text, font=font_menu, fill="BLACK")
    
    img = img.rotate(90, expand=True)
    lcd.ShowImage(img)
    time.sleep(1)
    user_id = select_profile(up=up, down=down, enter=enter, lcd=lcd)
    
    img = Image.new("RGB", (320, 240), "WHITE")
    draw = ImageDraw.Draw(img)
    if not user_id:
        error_msg = "Calibration failed: No profiles available"
        print(error_msg)
        error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2  # Center horizontally
        draw.text((error_x, 30), error_msg, font=font_menu, fill="BLACK")
        return error_msg

    print(f"{user_id}")
    user_x = (320 - draw.textlength(str(user_id), font=font_menu)) // 2
    draw.text((user_x, 50), str(user_id), font=font_menu, fill="BLACK")
    
    profile_path = PROFILES_DIR / f"{user_id}"
    os.makedirs(PROFILES_DIR, exist_ok=True)
    img = img.rotate(90, expand=True)
    lcd.ShowImage(img)
    time.sleep(1)

    hrtf_subjects = ['003', '019']
    calibration_results = calibration_routine(hrtf_subjects, NORMALIZED_ANGLES, up=up, down=down, left=left, right=right, enter=enter, lcd=lcd)
    
    head_params, hrtf_subject = estimate_head_params(calibration_results)
    profile = {
        **head_params,
        'hrtf_subject': hrtf_subject,
        'calibration_data': calibration_results,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    y_offset = 120  # Start lower to prevent overlap
    try:
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
        success_msg = f"Calibration complete! Profile saved to {profile_path}"
        print(success_msg)
        success_x = (320 - draw.textlength(success_msg, font=font_menu)) // 2
        draw.text((success_x, 80), success_msg, font=font_menu, fill="BLACK")

        print("\nYour Head Measurements:")
        head_measure_x = (320 - draw.textlength("Your Head Measurements:", font=font_menu)) // 2
        draw.text((head_measure_x, 100), "Your Head Measurements:", font=font_menu, fill="BLACK")

        # Display head parameters dynamically
        
        for key, value in head_params.items():
            display_text = f"{key.replace('_', ' ').title()}: {value:.2f} cm"
            text_x = (320 - draw.textlength(display_text, font=font_menu)) // 2
            print(display_text)
            draw.text((text_x, y_offset), display_text, font=font_menu, fill="BLACK")
            y_offset += 20  # Move down for next item

        hrtf_msg = f"Selected HRTF Subject: {hrtf_subject} ({'Female' if hrtf_subject == '019' else 'Male'})"
        print(hrtf_msg)
        hrtf_x = (320 - draw.textlength(hrtf_msg, font=font_menu)) // 2
        draw.text((hrtf_x, y_offset), hrtf_msg, font=font_menu, fill="BLACK")

        print("This profile can be used in test.py for personalized spatial audio.")
        usage_msg = "This profile can be used in test.py for personalized spatial audio."
        usage_x = (320 - draw.textlength(usage_msg, font=font_menu)) // 2
        draw.text((usage_x, y_offset + 20), usage_msg, font=font_menu, fill="BLACK")
        
        return f"Success! Profile saved as {user_id}"
    
    except Exception as e:
        error_msg = f"Error saving profile: {str(e)}"
        print(error_msg)
        error_x = (320 - draw.textlength(error_msg, font=font_menu)) // 2
        draw.text((error_x, y_offset + 40), error_msg, font=font_menu, fill="BLACK")
        return error_msg

if __name__ == "__main__":
    run_calibration_function()