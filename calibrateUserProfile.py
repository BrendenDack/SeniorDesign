import numpy as np
from scipy.io import loadmat
from scipy.signal import lfilter
import pyaudio
import time
import json
import os
import matplotlib.pyplot as plt
from pathlib import Path

# Constants
FS = 16000  # Sampling rate (Hz)
DURATION = 0.5  # Duration of each test sound
HRTF_PATH = "HRIRs/"  # Path to HRTF files
PROFILES_DIR = Path("user_profiles")
PROFILES_DIR.mkdir(exist_ok=True)

def generate_white_noise(duration, fs):
    """Generate white noise signal."""
    return np.random.normal(0, 0.5, int(duration * fs))

def apply_hrtf(signal, azimuth, subject="003"):
    """Apply HRTF to a mono signal."""
    data = loadmat(f'{HRTF_PATH}Subject_{subject}_{azimuth}_0.mat')
    hrir_left = data['hrir_left'].flatten()
    hrir_right = data['hrir_right'].flatten()
    
    # Apply HRIRs
    y_left = lfilter(hrir_left, 1, signal)
    y_right = lfilter(hrir_right, 1, signal)
    
    return np.column_stack((y_left, y_right)).astype(np.float32)

def play_audio(audio_data, fs):
    """Play audio through device."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                   channels=2,
                   rate=fs,
                   output=True)
    stream.write(audio_data.tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()

def spherical_head_model(angle, a_e):
    """Calculate time delay using the Spherical Head Model."""
    c = 343  # Speed of sound (m/s)
    angle_rad = np.deg2rad(np.abs(angle))
    d = a_e * (1 + np.sin(angle_rad))  # Path length difference
    time_delay = d / c  # Time delay in seconds
    return time_delay

def estimate_head_parameters(perceived_angles, actual_angles):
    """Estimate head parameters based on perception differences."""
    # Try different head sizes and find the best match
    head_widths = np.linspace(13.0, 17.0, 20)  # cm
    head_lengths = np.linspace(15.0, 22.0, 20)  # cm
    
    best_error = float('inf')
    best_width = 0
    best_length = 0
    
    for width in head_widths:
        for length in head_lengths:
            # Calculate effective radius
            a_e = 0.51 * (width/2) + 0.18 * (length/2) + 3.2
            a_e /= 100  # Convert to meters
            
            # Calculate expected time delays
            actual_delays = [spherical_head_model(angle, a_e) for angle in actual_angles]
            perceived_delays = [spherical_head_model(angle, a_e) for angle in perceived_angles]
            
            # Calculate error
            error = np.sum((np.array(actual_delays) - np.array(perceived_delays))**2)
            
            if error < best_error:
                best_error = error
                best_width = width
                best_length = length
    
    return best_width, best_length, best_error

def run_calibration():
    """Run the HRTF calibration process."""
    print("=== HRTF Calibration Process ===")
    print("This will help determine the best spatial audio settings for your unique hearing.")
    
    username = input("\nEnter your name or profile identifier: ")
    profile_path = PROFILES_DIR / f"{username}.json"
    
    if profile_path.exists():
        load_existing = input("Profile exists. Load it? (y/n): ").lower() == 'y'
        if load_existing:
            with open(profile_path, 'r') as f:
                return json.load(f)
    
    # Get available HRTF subjects
    available_subjects = []
    for file in os.listdir(HRTF_PATH):
        if file.startswith("Subject_") and file.endswith("_0.mat"):
            subject = file.split("_")[1]
            if subject not in available_subjects:
                available_subjects.append(subject)
    
    print(f"\nFound {len(available_subjects)} HRTF subjects")
    
    # Test angles following a pattern similar to the exam
    test_angles = [-80, -65, -45, -25, -10, 0, 10, 25, 45, 65, 80]
    perceived_angles = []
    
    print("\nYou'll hear sounds from different directions.")
    print("For each sound, enter the angle where you perceive it coming from (-90 to +90 degrees).")
    print("0° is directly in front, -90° is left, and +90° is right.")
    
    input("\nPress Enter when ready to begin...")
    
    # Initial test with default subject
    test_subject = "003"
    for angle in test_angles:
        noise = generate_white_noise(DURATION, FS)
        spatial_noise = apply_hrtf(noise, angle, test_subject)
        
        print(f"\nPlaying sound from {angle}°...")
        play_audio(spatial_noise, FS)
        time.sleep(0.5)  # Short pause
        
        perceived = float(input("Where did you hear it? (angle in degrees): "))
        perceived_angles.append(perceived)
    
    # Estimate head parameters
    head_width, head_length, error = estimate_head_parameters(perceived_angles, test_angles)
    
    print(f"\nEstimated head width: {head_width:.1f} cm")
    print(f"Estimated head length: {head_length:.1f} cm")
    
    # Calculate effective radius
    a_e = 0.51 * (head_width/2) + 0.18 * (head_length/2) + 3.2
    print(f"Effective head radius: {a_e:.1f} cm")
    
    # Select best subject based on head size
    # Simple distance function for demonstration
    subject_data = {
        "003": {"width": 14.5, "length": 18.0},  # Average female
        "008": {"width": 15.5, "length": 19.6},  # Average male
        "021": {"width": 16.2, "length": 20.5}   # Large head
    }
    
    best_subject = test_subject
    best_distance = float('inf')
    
    for subject, measurements in subject_data.items():
        if subject in available_subjects:
            distance = ((measurements["width"] - head_width)**2 + 
                        (measurements["length"] - head_length)**2)**0.5
            if distance < best_distance:
                best_distance = distance
                best_subject = subject
    
    print(f"\nRecommended HRTF profile: Subject_{best_subject}")
    
    # Fine-tuning through A/B testing
    print("\nLet's verify this is the best match for you.")
    print("You'll hear the same sound with different HRTF profiles.")
    
    test_angle = 45  # Fixed test angle
    noise = generate_white_noise(DURATION, FS)
    
    candidates = [best_subject]
    for subject in available_subjects:
        if subject != best_subject:
            candidates.append(subject)
            if len(candidates) >= 3:  # Limit to 3 options
                break
    
    ratings = {}
    
    for subject in candidates:
        spatial_noise = apply_hrtf(noise, test_angle, subject)
        print(f"\nTesting Subject_{subject}...")
        play_audio(spatial_noise, FS)
        rating = int(input("Rate accuracy (1-10): "))
        ratings[subject] = rating
    
    # Find highest rated subject
    final_subject = max(ratings, key=ratings.get)
    
    # Create profile
    profile = {
        "username": username,
        "head_width": float(head_width),
        "head_length": float(head_length),
        "effective_radius": float(a_e),
        "hrtf_subject": final_subject,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_results": {
            "actual_angles": test_angles,
            "perceived_angles": perceived_angles,
            "subject_ratings": ratings
        }
    }
    
    # Save profile
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=4)
    
    print(f"\nProfile saved as {profile_path}")
    
    # Visualization
    plot_results(profile)
    
    return profile

def plot_results(profile):
    """Plot calibration results for visualization."""
    test_results = profile["test_results"]
    actual = test_results["actual_angles"]
    perceived = test_results["perceived_angles"]
    
    plt.figure(figsize=(12, 5))
    
    # Plot angle perception
    plt.subplot(1, 2, 1)
    plt.plot(actual, perceived, 'o-', label='Your perception')
    plt.plot(actual, actual, '--', label='Perfect perception')
    plt.xlabel('Actual angle (degrees)')
    plt.ylabel('Perceived angle (degrees)')
    plt.title('Spatial Perception Analysis')
    plt.grid(True)
    plt.legend()
    
    # Plot ratings
    plt.subplot(1, 2, 2)
    subjects = list(test_results["subject_ratings"].keys())
    ratings = list(test_results["subject_ratings"].values())
    plt.bar(subjects, ratings)
    plt.xlabel('HRTF Profile')
    plt.ylabel('Rating (1-10)')
    plt.title('Profile Comparison')
    
    plt.tight_layout()
    plt.savefig(PROFILES_DIR / f"{profile['username']}_results.png")
    print(f"Results visualization saved")

def main():
    profile = run_calibration()
    print("\nCalibration complete!")
    print(f"Your profile ID is: {profile['username']}")
    print("You can now run test.py with your calibrated profile.")

if __name__ == "__main__":
    main()
