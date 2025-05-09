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

# Configuration
DURATION = 1.5
HRTF_PATH = Path("HRIRs/")
PROFILES_DIR = Path("user_profiles")
FS = 48000  # Force modern sample rate
SUPPRESS_ERRORS = True  # Set to False to debug audio errors
NORMALIZED_ANGLES = [-180, -90, 0, 90]  # Base angles for snapping

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

def get_angle_input(current_angle: float, preset_angle: float, stimulus: np.ndarray, spatial_audio: np.ndarray, fs: int, up=None, down=None, left=None, right=None, enter=None) -> float:
    """
    Interactively adjust the perceived angle with deviation feedback.
    Use:
      • w/up: +10°
      • s/down: -10°
      • d/right: +1°
      • a/left: -1°
      • r: Replay sound (for rear angles)
    Press enter button to confirm the current angle.
    """
    print("\nAdjust the perceived angle (WASD/buttons for adjustments, r to replay):")
    print("  w/up: +10°, s/down: -10°, d/right: +1°, a/left: -1°, r: replay")
    print("Press enter button to confirm the current angle.")
    angle = current_angle
    while True:
        deviation = abs(angle - preset_angle)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        print(f"Current angle: {angle:.1f}° (Deviation: {deviation:.1f}°)", end="", flush=True)
        ch = get_input(up, down, left, right, enter)
        if not ch:
            time.sleep(0.2)  # Prevent flooding
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

def calibration_routine(hrtf_subjects: list, normalized_angles: list, num_trials: int = 4, up=None, down=None, left=None, right=None, enter=None) -> dict:
    """
    Calibration routine for multiple HRTF subjects.
    Randomly selects 4 angles per subject, snapped to available HRIR angles, prioritizing negative angles.
    """
    calibration_data = {subject: {'preset_angles': [], 'responses': []} for subject in hrtf_subjects}
    for subject in hrtf_subjects:
        print(f"\nCalibrating for Subject_{subject}...")
        available_angles = get_available_angles(HRTF_PATH, subject)
        if not available_angles:
            print(f"No HRIR files found for Subject_{subject} in {HRTF_PATH}")
            continue

        # Snap normalized angles to available angles
        snapped_angles = [snap_to_nearest_angle(angle, available_angles) for angle in normalized_angles]
        # Ensure at least 2 negative angles
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

        stimulus = generate_swept_sine(DURATION, FS)
        for trial, preset_angle in enumerate(trial_angles):
            print(f"\nTrial {trial + 1} for Subject_{subject}: Preset angle = {preset_angle}°")
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
                print(f"HRTF Processing Error for file {hrtf_file.name}: {str(e)}")
                continue
            if play_audio(spatial_audio, FS):
                print("Playing test sound...")
                response = get_angle_input(preset_angle, preset_angle, stimulus, spatial_audio, FS, up, down, left, right, enter)
                time.sleep(0.1)
                calibration_data[subject]['preset_angles'].append(preset_angle)
                calibration_data[subject]['responses'].append(response)
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


# def select_profile(up=None, down=None, enter=None) -> str:
#     #os.system('cls' if os.name == 'nt' else 'clear')

#     """Select a profile using up/down buttons, confirm with enter."""
#     profile_files = sorted([f for f in PROFILES_DIR.glob("*.json") if f.is_file()])
    
#     if not profile_files:
#         print("No profiles found in user_profiles/")
#         return None
#     if len(profile_files) > 5:
#         profile_files = profile_files[:5]

#     selected_idx = 0
#     has_navigated = False
#     print("Select a profile (up/w, down/s, enter to confirm):")
#     for i, profile in enumerate(profile_files):
#         cursor = "> " if i == selected_idx else "  "
#         print(f"{cursor}{i + 1}) {profile.stem}")
#     sys.stdout.flush()

#     num_lines = len(profile_files) + 1
#     while True:

#         ch = get_input(up, down, None, None, enter)
#         if not ch:
#             time.sleep(0.1)  # Prevent CPU overload
#             continue
#         if ch == '\n' and has_navigated:
#             sys.stdout.write(f"\033[{num_lines}A")
#             sys.stdout.flush()
#             for _ in range(num_lines):
#                 sys.stdout.write("\033[K\n")
#             sys.stdout.flush()
#             sys.stdout.write(f"\033[{num_lines}A")
#             sys.stdout.flush()
#             return profile_files[selected_idx].stem
#         elif ch.lower() == 'w':
#             if selected_idx >= 0:
#                 sys.stdout.write(f"\033[{selected_idx + 2}A\r  ")
#                 sys.stdout.flush()
#                 selected_idx -= 1
#                 sys.stdout.write(f"\033[{selected_idx + 2}A\r> ")
#                 sys.stdout.flush()
#                 sys.stdout.write(f"\033[{num_lines - selected_idx - 1}B")
#                 sys.stdout.flush()
#                 has_navigated = True
#         elif ch.lower() == 's':
#             if selected_idx < len(profile_files) - 1:
#                 sys.stdout.write(f"\033[{selected_idx + 2}A\r  ")
#                 sys.stdout.flush()
#                 selected_idx += 1
#                 sys.stdout.write(f"\033[{selected_idx + 2}A\r> ")
#                 sys.stdout.flush()
#                 sys.stdout.write(f"\033[{num_lines - selected_idx - 1}B")
#                 sys.stdout.flush()
#                 has_navigated = True
#         else:
#             print("\rUse up/w, down/s, or enter to select.")



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


def select_profile(up=None, down=None, enter=None) -> str:
    """Prompt user to select a profile from user_profiles using WASD."""
    profiles_dir = PROFILES_DIR
    profiles = sorted(profiles_dir.glob("*.json"))
    if not profiles:
        print("No profiles found in user_profiles/. Creating default profile.")
        return "default_profile"
    
    
    selected_idx = 0
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nSelect a profile (Up/Down to navigate, Enter to select):")
        for i, profile in enumerate(profiles):
            marker = ">" if i == selected_idx else " "
            print(f"{marker} {profile.name}")
        sys.stdout.flush()

        ch = get_input(up=up, down=down, enter=enter)
        if ch in ('\r', '\n'):
            try:
                
                print(f"\nSelected profile: {profiles[selected_idx].name}")
            
                """
                print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
                print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
                print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
                print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
                """
                
                return profiles[selected_idx].name
            except json.JSONDecodeError:
                print(f"Error: {profiles[selected_idx].name} is not a valid JSON file.")
                return profiles[selected_idx].name
        elif ch.lower() == 'w' and selected_idx > 0:
            selected_idx -= 1
        elif ch.lower() == 's' and selected_idx < len(profiles) - 1:
            selected_idx += 1



def run_calibration_function(up=None, down=None, left=None, right=None, enter=None) -> str:
    """Main calibration workflow."""
    print("=== HRTF Calibration ===")
    user_id = select_profile(up=up, down=down, enter=enter)
    
    if not user_id:
        print("Calibration failed: No profiles available")
        return "Calibration failed: No profiles available"
    print(f"{user_id}")
    profile_path = PROFILES_DIR / f"{user_id}"
    os.makedirs(PROFILES_DIR, exist_ok=True)
    
    hrtf_subjects = ['003', '019']
    calibration_results = calibration_routine(hrtf_subjects, NORMALIZED_ANGLES, up=up, down=down, left=left, right=right, enter=enter)
    
    head_params, hrtf_subject = estimate_head_params(calibration_results)
    profile = {
        **head_params,
        'hrtf_subject': hrtf_subject,
        'calibration_data': calibration_results,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
        print(f"\nCalibration complete! Profile saved to {profile_path}")
        
        print("\nYour Head Measurements:")
        print(f"  Head Width: {head_params['head_width']:.2f} cm")
        print(f"  Head Length: {head_params['head_length']:.2f} cm")
        print(f"  Effective Radius: {head_params['effective_radius']:.2f} cm")
        print(f"Selected HRTF Subject: {hrtf_subject} ({'Female' if hrtf_subject == '019' else 'Male'})")
        
        print("This profile can be used in test.py for personalized spatial audio.")
        return f"Success! Profile saved as {user_id}"
    except Exception as e:
        print(f"Error saving profile: {str(e)}")
        return f"Calibration failed: {str(e)}"

if __name__ == "__main__":
    run_calibration_function()