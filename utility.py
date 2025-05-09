import numpy as np
from scipy.io import loadmat, wavfile
from scipy.signal import lfilter, resample
import torch
from openunmix import predict
from IPython.display import Audio, display # type: ignore
from battery_monitor import get_battery_info, is_charging
from calibrateUserProfile import apply_hrtf
from pydub import AudioSegment
import os
import pickle
import h5py
import json
from pathlib import Path
import h5py

PROFILES_DIR = Path("user_profiles")
global volume
volume = 1

# Read WAV file and return data and sampling rate
def read_wav_file(filename, fs=16000):
    fs, data = wavfile.read(filename)
    return fs, data

def convert_to_wav(input_file_path):
    file_name, ext = os.path.splitext(input_file_path)
    ext = ext.lower()

    # Load audio with pydub
    try:
        audio = AudioSegment.from_file(input_file_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load audio file: {e}")

    wav_file_path = f"{file_name}.wav"

    # Export to WAV format if not already a WAV
    if ext != ".wav":
        audio.export(wav_file_path, format="wav")
    else:
        wav_file_path = input_file_path  # already WAV

    return wav_file_path

# Set Volume
def set_volume(vol):
    global volume
    volume = vol

# Get Volume
def get_volume():
    global volume
    return volume

# Apply HRTF Function to input signal n, with azimuth(angle) az
def Apply_HRTF(az, n):
    data = loadmat(f'HRIRs/Subject_003_{az}_0.mat')
    hrir_left = data['hrir_left'].flatten()
    hrir_right = data['hrir_right'].flatten()
    
    # Resample HRIRs from 44.1 kHz to 16 kHz
    #hrir_left_resampled = resample(hrir_left, int(len(hrir_left) * fs / original_fs))
    #hrir_right_resampled = resample(hrir_right, int(len(hrir_right) * fs / original_fs))
    
    # Generate white noise
    #n = generate_white_noise(duration, fs)
    
    y_left = lfilter(hrir_left, 1, n) # Left
    y_right = lfilter(hrir_right, 1, n) # Right
    y = np.column_stack((y_left, y_right)).astype(np.float32)
    return y

# Take Stereo input signal and convert to mono signal
def Stereo_to_mono(signal):
    # x = np.linalg.norm(np.abs(signal)) # get magnitude of absolute value of signal
    left = signal[:,0]
    right = signal[:, 1]
    x = left + right
    peak = np.max(np.abs(x))
    return 0.5 * (x/peak) # return mono signal

# Separate sources from input signal given file name (Will add more options later)
def separate_sources(file_name):
    # Set up Torch
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    # Load the audio file with pydub (supports most formats)
    audio = AudioSegment.from_file(file_name)
    audio = audio.normalize()

    # Ensure it's stereo
    if audio.channels != 2:
        audio = audio.set_channels(2)

    # Convert to 44100Hz and 16-bit samples
    audio = audio.set_frame_rate(16000).set_sample_width(2)

    # Get raw data as NumPy array
    samples = np.array(audio.get_array_of_samples()).reshape((-1, 2))
    samples = samples.astype(np.float32) / 32768.0  # normalize 16-bit PCM

    # Separate sources
    estimates = predict.separate(
        torch.as_tensor(samples).float(),
        rate=16000,
        device=device
    )

    for target, estimate in estimates.items():
        print(target)
        audio_out = estimate.detach().cpu().numpy()[0]
        display(Audio(audio_out, rate=16000))

    # Convert to dictionary of NumPy arrays
    estimates_numpy = {}
    for target, estimate in estimates.items():
        estimates_numpy[target] = torch.squeeze(estimate).detach().cpu().numpy().T

    return estimates_numpy

# Sum the signals of the modified stems
def summed_signal(modified_vocals, modified_bass, modified_other, modified_drums):
    global volume
    if (volume == 0):
        volume = 1e-10
    summed_song = (modified_vocals + modified_bass + modified_other + modified_drums)/(1/volume)
    return summed_song

# Apply HRTF to the separated sources
def spacial_stems(estimates_numpy):
    azim = [-80, -65, -55, -45, -40, -35, -30, -25, -20, -15, -10, -5]
    azim = azim + [0] + [-a for a in reversed(azim)]
    modified_bass = Apply_HRTF(azim[0], Stereo_to_mono(estimates_numpy['bass']))
    modified_drums = Apply_HRTF(azim[24], Stereo_to_mono(estimates_numpy['drums']))
    modified_other = Apply_HRTF(azim[6], Stereo_to_mono(estimates_numpy['other']))
    modified_vocals = Apply_HRTF(azim[18], Stereo_to_mono(estimates_numpy['vocals']))

    return modified_bass, modified_drums, modified_other, modified_vocals

# Perform Full Suite of Spacial Audio Separation
def Spacial_Audio_Separation(file_name):
    estimates_numpy = separate_sources(file_name)
    modified_bass, modified_drums, modified_other, modified_vocals = spacial_stems(estimates_numpy)
    summed_song = summed_signal(modified_vocals, modified_bass, modified_other, modified_drums)
    return summed_song

def run_spatial_audio_old(file_name):
    print("Starting process")
    only_file_name = os.path.relpath(file_name, "Music")
    print(file_name)
    name_only, ext = os.path.splitext(only_file_name)
    print(name_only)
    output_filepath = "Spatial/" + name_only + ".h5"
    print(output_filepath)
    if os.path.exists(output_filepath):
        print("Separated HDF5 file found. Skipping processing.")
       
    else:
        print("No HDF5 file: Starting Seperation")
        
        estimates_numpy = separate_sources(file_name)

        print("Trying to save HDF5 file")
        # Save stems to pickle file
        with h5py.File(output_filepath, "w") as f:
            f.create_dataset("vocals", data=estimates_numpy['vocals'], compression="gzip")
            f.create_dataset("drums", data=estimates_numpy['drums'], compression="gzip")
            f.create_dataset("bass", data=estimates_numpy['bass'], compression="gzip")
            f.create_dataset("other", data=estimates_numpy['other'], compression="gzip")

    return "Song successfully converted."

def apply_bulk_hrtf_old(stems_directory, Loaded_Profile):
    
    try:
        with open(f"{PROFILES_DIR}/{Loaded_Profile}", 'r') as f:
            profile_data = json.load(f)
        if not all(k in profile_data for k in ['hrtf_subject', 'effective_radius']):
            print(f"Invalid profile: {Loaded_Profile} Missing required fields.")
            profile_data = {
                "hrtf_subject": "003",
                "effective_radius": 8.5,
                "head_width": 15.2,
                "head_length": 19.0,
                "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
            }
        print(f"\nSelected profile: {Loaded_Profile}")
        print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
        print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
        print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
        print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
    except json.JSONDecodeError:
        print(f"Error: {Loaded_Profile} is not a valid JSON file.")
        profile_data = {
            "hrtf_subject": "003",
            "effective_radius": 8.5,
            "head_width": 15.2,
            "head_length": 19.0,
            "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
        }

    if "stem_directions" not in profile_data:
        profile_data["stem_directions"] = {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
    
    print("Apply HRTFs")
    angles = profile_data["stem_directions"]
    test_subject = profile_data['hrtf_subject']
    print("Create Stems dict")
    spacial_stems = {'vocals' : 0, 'drums' : 0, 'bass' : 0, 'other' : 0}


    with h5py.File(stems_directory, "r") as f:
        for stem_name in ["vocals", "drums", "bass", "other"]:
            print(f"Processing {stem_name}")
            stem = f[stem_name][:]
            angle = angles[stem_name]
            processed = apply_hrtf(stem, angle, test_subject)
            spacial_stems[stem_name] = processed
            del stem


    print("Finished HRTFS")
    
    return spacial_stems


def save_stems_to_pkl_v1(estimates_numpy, song_name, metadata_file="Spatial/metadata.pkl", data_file=None):
    """Save audio stems (numpy arrays) into a pickle file with metadata indexing for efficient retrieval."""
    data_file = data_file or f"Spatial/{song_name}.pkl"
    metadata = {}  # Dictionary to store offset indexes for quick lookup

    with open(data_file, "wb") as f:
        for stem_name, stem_data in estimates_numpy.items():
            offset = f.tell()  # Store byte position before writing
            
            pickle.dump(stem_data, f)  # Write stem data
            
            metadata[stem_name] = {
                "offset": offset,  # Store byte position
                "shape": stem_data.shape,  # Store array shape (dimensions)
                "dtype": str(stem_data.dtype),  # Store data type
                "song": song_name  # Track which song this belongs to
            }

    # Save metadata separately for lookup optimization
    with open(metadata_file, "wb") as meta_f:
        pickle.dump(metadata, meta_f)

    print(f"✅ Saved stems for {song_name} with metadata indexing.")

    # Example: Store processed stems (NumPy arrays)
    estimates_numpy = {
        "vocals": np.random.rand(44100, 2),  # Stereo vocals
        "drums": np.random.rand(44100, 2),   # Stereo drums
        "bass": np.random.rand(44100, 1),    # Mono bass
        "other": np.random.rand(44100, 2)    # Stereo other sounds
    }

    save_stems_to_pkl(estimates_numpy, "example_song")


def save_stems_to_pkl_v2(estimates_numpy, song_name):
    """Save audio stems (numpy arrays) into a pickle file with metadata indexing in the correct directory."""
    
    song_dir = f"Spatial/{song_name}/"
    os.makedirs(song_dir, exist_ok=True)  # Ensure the directory exists
    
    metadata_file = f"{song_dir}metadata.pkl"
    data_file = f"{song_dir}stems.pkl"
    metadata = {}  # Dictionary to store offset indexes for quick lookup

    with open(data_file, "wb") as f:
        for stem_name, stem_data in estimates_numpy.items():
            offset = f.tell()  # Store byte position before writing
            
            pickle.dump(stem_data, f)  # Write stem data
            
            metadata[stem_name] = {
                "offset": offset,  # Byte position in file
                "shape": stem_data.shape,  # Array dimensions
                "dtype": str(stem_data.dtype),  # Data type
                "song": song_name  # Track song name
            }

    # Save metadata separately in the same folder
    with open(metadata_file, "wb") as meta_f:
        pickle.dump(metadata, meta_f)

    print(f"✅ Saved stems and metadata for {song_name} in {song_dir}")

def load_specific_stem(stem_name, song_name, metadata_file="Spatial/metadata.pkl", data_file=None):
    """Load only a specific stem using metadata indexing to avoid unnecessary memory usage."""
    data_file = data_file or f"Spatial/{song_name}.pkl"

    # Load metadata first
    with open(metadata_file, "rb") as meta_f:
        metadata = pickle.load(meta_f)

    if stem_name not in metadata:
        raise ValueError(f"❌ Stem '{stem_name}' not found for {song_name}.")

    offset = metadata[stem_name]["offset"]  # Retrieve byte position of the requested stem

    # Open the main data file and seek to correct position
    with open(data_file, "rb") as f:
        f.seek(offset)  # Jump directly to stored byte position
        stem_data = pickle.load(f)  # Deserialize only this portion

    return stem_data

    # Example: Load "drums" from the pickle file without full deserialization
    drums_data = load_specific_stem("drums", "example_song")
    print("✅ Loaded Drums Shape:", drums_data.shape)


def apply_bulk_hrtf_new(song_name, Loaded_Profile, metadata_file="Spatial/metadata.pkl"):
    """Apply HRTF processing to individual stems, loading dynamically from PKL files."""
    
    try:
        with open(f"{PROFILES_DIR}/{Loaded_Profile}", "r") as f:
            profile_data = json.load(f)

        if not all(k in profile_data for k in ["hrtf_subject", "effective_radius"]):
            print(f"❌ Invalid profile: {Loaded_Profile}. Missing required fields.")
            return None

        print(f"\n✅ Selected profile: {Loaded_Profile}")
        print(f"   🎧 HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
        print(f"   📏 Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
        print(f"   📏 Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
        print(f"   🎯 Effective Radius: {profile_data['effective_radius']:.2f} cm")

    except json.JSONDecodeError:
        print(f"❌ Error: {Loaded_Profile} is not a valid JSON file.")
        return None

    # Stem directions (angles for spatial audio)
    angles = profile_data.get("stem_directions", {"bass": 0, "vocals": 0, "drums": 0, "other": 0})
    test_subject = profile_data["hrtf_subject"]

    print("\n🚀 Applying HRTF processing for each stem...")

    spacial_stems = {}
    for stem in ["vocals", "drums", "bass", "other"]:
        print(f"🔄 Processing {stem}...")
        audio_data = load_specific_stem(stem, song_name)  # Load only this stem
        spacial_stems[stem] = apply_hrtf(audio_data, angles[stem], test_subject)

    print("✅ Finished HRTF processing!")

    return spacial_stems

def run_spatial_audio_new(file_name):
    """Process audio file, separate sources, and store stems with metadata indexing."""
    
    print("Starting process")
    only_file_name = os.path.relpath(file_name, "Music")
    name_only, _ = os.path.splitext(only_file_name)
    
    metadata_file = f"Spatial/{name_only}_metadata.pkl"
    data_file = f"Spatial/{name_only}.pkl"

    # If the pickle file exists, load indexed metadata instead of the full file
    if os.path.exists(metadata_file):
        print("✅ Metadata found, attempting to load individual stems when needed.")
        with open(metadata_file, 'rb') as f:
            metadata = pickle.load(f)
    else:
        print("🆕 No pickle metadata file found: Starting Separation")

        estimates_numpy = separate_sources(file_name)  # Extract stems

        print("🔄 Saving stems with metadata indexing...")
        save_stems_to_pkl(estimates_numpy, name_only, metadata_file, data_file)

    return f"🎵 Song '{name_only}' successfully converted."



def run_spatial_audio(file_name):
    print("Starting process")
    only_file_name = os.path.relpath(file_name, "Music")
    print(file_name)
    name_only, ext = os.path.splitext(only_file_name)
    print(name_only)
    output_filepath = "Spatial/" + name_only + ".h5"
    print(output_filepath)
    if os.path.exists(output_filepath):
        print("Separated HDF5 file found. Skipping processing.")
       
    else:
        print("No HDF5 file: Starting Seperation")
        
        estimates_numpy = separate_sources(file_name)

        print("Trying to save HDF5 file")
        # Save stems to pickle file
        with h5py.File(output_filepath, "w") as f:
            f.create_dataset("vocals", data=estimates_numpy['vocals'], compression="gzip")
            f.create_dataset("drums", data=estimates_numpy['drums'], compression="gzip")
            f.create_dataset("bass", data=estimates_numpy['bass'], compression="gzip")
            f.create_dataset("other", data=estimates_numpy['other'], compression="gzip")

    return "Song successfully converted."

def apply_bulk_hrtf(stems_directory, Loaded_Profile):
    
    try:
        with open(f"{PROFILES_DIR}/{Loaded_Profile}", 'r') as f:
            profile_data = json.load(f)
        if not all(k in profile_data for k in ['hrtf_subject', 'effective_radius']):
            print(f"Invalid profile: {Loaded_Profile} Missing required fields.")
            profile_data = {
                "hrtf_subject": "003",
                "effective_radius": 8.5,
                "head_width": 15.2,
                "head_length": 19.0,
                "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
            }
        print(f"\nSelected profile: {Loaded_Profile}")
        print(f"  HRTF Subject: {profile_data['hrtf_subject']} ({'Female' if profile_data['hrtf_subject'] == '019' else 'Male'})")
        print(f"  Head Width: {profile_data.get('head_width', 15.2):.2f} cm")
        print(f"  Head Length: {profile_data.get('head_length', 19.0):.2f} cm")
        print(f"  Effective Radius: {profile_data['effective_radius']:.2f} cm")
    except json.JSONDecodeError:
        print(f"Error: {Loaded_Profile} is not a valid JSON file.")
        profile_data = {
            "hrtf_subject": "003",
            "effective_radius": 8.5,
            "head_width": 15.2,
            "head_length": 19.0,
            "stem_directions": {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
        }

    if "stem_directions" not in profile_data:
        profile_data["stem_directions"] = {"bass": 0, "vocals": 0, "drums": 0, "other": 0}
    
    print("Apply HRTFs")
    angles = profile_data["stem_directions"]
    test_subject = profile_data['hrtf_subject']
    print("Create Stems dict")
    spacial_stems = {'vocals' : 0, 'drums' : 0, 'bass' : 0, 'other' : 0}


    with h5py.File(stems_directory, "r") as f:
        for stem_name in ["vocals", "drums", "bass", "other"]:
            print(f"Processing {stem_name}")
            stem = f[stem_name][:]
            angle = angles[stem_name]
            processed = apply_hrtf(stem, angle, test_subject)
            spacial_stems[stem_name] = processed
            del stem


    print("Finished HRTFS")
    
    return spacial_stems