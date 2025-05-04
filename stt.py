import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import random
import vlc
import os
import time
import tempfile 
import sys
from gtts import gTTS  # SPEECH TO TEXT

# Audio Parameters
RATE = 16000  # 48000 #44100 replace #16000 original rate used 
CHANNELS = 1
CHUNK = 8000  # 512 #8000 original chunk size
WIDTH = 2

# Path for music folder (REPLACE WITH YOUR PATH BRENDEN, ensure you use / not \)
MUSIC_FOLDER = 'RPI-Sara/code/Music'

# Initialize Vosk model
model = Model('vosk-model-small-en-us-0.15')
rec = KaldiRecognizer(model, RATE)



# Initialize PyAudio
audio = pyaudio.PyAudio()
try:
    stream = audio.open(format=audio.get_format_from_width(WIDTH),
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        # input_device_index=input_device_index,
                        frames_per_buffer=CHUNK)
except OSError as e:
    print(f"Error opening audio stream: {e}")
    exit()

# Initialize VLC player for playback
instance = vlc.Instance()
player = instance.media_player_new()
tts_player = instance.media_player_new()  # Global player for text-to-speech

# Define specific paths to avoid overlap
NORMAL_MUSIC_PATH = os.path.join(MUSIC_FOLDER, "normal music").lower()
NOT_SO_NORMAL_MUSIC_PATH = os.path.join(MUSIC_FOLDER, "not so normal music").lower()

# Load songs into separate playlists
song_files = []
normal_music_files = []
not_so_normal_music_files = []

for root, dirs, files in os.walk(MUSIC_FOLDER):
    for file in files:
        if file.lower().endswith(('.mp3', '.wav', '.flac')):
            full_path = os.path.join(root, file)
            path_lower = full_path.lower()

            if path_lower.startswith(NORMAL_MUSIC_PATH):
                normal_music_files.append(full_path)
            elif path_lower.startswith(NOT_SO_NORMAL_MUSIC_PATH):
                not_so_normal_music_files.append(full_path)
            elif "\\music\\" not in path_lower:  # Exclude anything under Music folder
                song_files.append(full_path)

# Playlist and state
playlist = []
current_index = 0
loop = False
shuffle = False
shuffle_history = []

# Text-to-speech function with overlap protection
def speak(text):
    tts = gTTS(text=text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        media = instance.media_new(fp.name)
        tts_player.set_media(media)
        tts_player.play()
        while tts_player.is_playing():
            time.sleep(0.1)  # Prevent overlap

# Function to detect wake word "Hey Music"
def detect_wake_word(audio_chunk):
    if rec.AcceptWaveform(audio_chunk):
        result = json.loads(rec.Result())
        if 'text' in result and "hey music" in result['text'].lower():
            return True
    return False

# Function to recognize command
def recognize_command(audio_chunk):
    if rec.AcceptWaveform(audio_chunk):
        result = json.loads(rec.Result())
        return result.get('text', '').lower()
    return ''

# Play/choose song function
def play_song(song_name):
    global playlist, current_index, shuffle_history

    song_name = song_name.strip().lower()

    # Reset playlist based on category
    if "normal music" in song_name:
        playlist[:] = normal_music_files
    elif "not so normal music" in song_name:
        playlist[:] = not_so_normal_music_files
    elif song_name in ["", "music", "downloaded music", "playlist", "all songs"]:
        playlist[:] = song_files

    if not playlist:
        print("No songs found in playlist.")
        speak("Sorry, your playlist is empty.")
        return

    shuffle_history = []

    song_file = None
    if song_name and song_name not in ["music", "downloaded music", "playlist", "all songs", "normal music", "not so normal music"]:
        for i, song in enumerate(playlist):
            if song_name in os.path.basename(song).lower():
                song_file = song
                current_index = i
                break
    else:
        current_index = random.randint(0, len(playlist) - 1) if shuffle else 0
        song_file = playlist[current_index]

    if song_file:
        media = instance.media_new(song_file)
        player.set_media(media)
        player.play()
        print(f"Now playing: {os.path.basename(song_file)}")
        speak(f"Now playing {os.path.splitext(os.path.basename(song_file))[0]}")
    else:
        print("Could not find the song.")
        speak("Sorry, I could not find that song.")

# Pause function
def pause_song():
    player.pause()
    speak("Song paused.")

# Resume function
def resume_song():
    player.play()
    speak("Song resumed.")

# Next song function
def next_song():
    global current_index, shuffle_history
    if not playlist:
        speak("Playlist is empty.")
        return

    if shuffle:
        shuffle_history.append(current_index)
        next_index = random.randint(0, len(playlist) - 1)
        while next_index == current_index and len(playlist) > 1:
            next_index = random.randint(0, len(playlist) - 1)
        current_index = next_index
    else:
        current_index = (current_index + 1) % len(playlist)

    song_path = playlist[current_index]
    media = instance.media_new(song_path)
    player.set_media(media)
    player.play()
    print(f"Playing next song: {os.path.basename(song_path)}")
    speak("Playing next song.")

# Previous song function
def previous_song():
    global current_index, shuffle_history
    if not playlist:
        speak("Playlist is empty.")
        return

    if shuffle and shuffle_history:
        current_index = shuffle_history.pop()
    else:
        current_index = (current_index - 1) % len(playlist)

    song_path = playlist[current_index]
    media = instance.media_new(song_path)
    player.set_media(media)
    player.play()
    print(f"Playing previous song: {os.path.basename(song_path)}")
    speak("Playing previous song.")

# Toggle loop mode
def toggle_loop():
    global loop
    loop = not loop
    speak("Loop mode on." if loop else "Loop mode off.")

# Toggle shuffle mode
def toggle_shuffle():
    global shuffle, shuffle_history
    shuffle = not shuffle
    shuffle_history = []
    speak("Shuffle mode on." if shuffle else "Shuffle mode off.")

# Volume control functions (new functionality, for the purpose of being able to hear during music)
NORMAL_VOLUME = 80
LOW_VOLUME = 40

def lower_volume():
    player.audio_set_volume(LOW_VOLUME)
    print("Volume lowered to", LOW_VOLUME)

def restore_volume():
    player.audio_set_volume(NORMAL_VOLUME)
    print("Volume restored to", NORMAL_VOLUME)

def start_voice_recognition():
    global player, playlist
    # Initialize PyAudio
    audio = pyaudio.PyAudio()
    try:
        stream = audio.open(format=audio.get_format_from_width(WIDTH),
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        # input_device_index=input_device_index,
                        frames_per_buffer=CHUNK)
    except OSError as e:
        print(f"Error opening audio stream: {e}")
        return
    print("Listening for 'Hey Music' command... Press Ctrl+C to stop.")
    speak("Hello! Say Hey Music to continue!")

    try:
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)  # Prevent overflow crash
            except IOError as e:
                print(f"Overflow error: {e}. Restarting stream...")
                stream.stop_stream()
                stream.start_stream()
                continue

            if detect_wake_word(data):
                print("'Hey Music' detected. Listening for command...")
                speak("Yes?")
                lower_volume()  # Lower volume when wake word detected

                while True:
                    try:
                        data = stream.read(CHUNK, exception_on_overflow=False)
                    except IOError as e:
                        print(f"Overflow error: {e}. Restarting stream...")
                        stream.stop_stream()
                        stream.start_stream()
                        continue

                    command = recognize_command(data)
                    if command:
                        if "play" in command:
                            song_name = command.replace("play", "").strip()
                            play_song(song_name)
                        elif "pause" in command:
                            pause_song()
                        elif "resume" in command:
                            resume_song()
                        elif "next" in command:
                            next_song()
                        elif "previous" in command:
                            previous_song()
                        elif "loop" in command:
                            toggle_loop()
                        elif "shuffle" in command:
                            toggle_shuffle()
                        elif "stop" in command:
                            print("Stopping")
                            sys.exit()
                        else:
                            speak("Sorry, I didn't understand that.")
                        break
                restore_volume()  # Restore volume after command processing
                # stream.stop_stream()
                # stream.close()
                # audio.terminate()
                #return
                #print("Listening for 'Hey Music' command...")

            if player.get_state() == vlc.State.Ended and playlist:
                if loop:
                    song_path = playlist[current_index]
                    media = instance.media_new(song_path)
                    player.set_media(media)
                    player.play()
                else:
                    next_song()

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Stopped by user")
    except OSError as e:
        print(f"Stream error: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except OSError:
            print("Stream was already closed or not properly opened")
        audio.terminate()
        player.stop()

#start_voice_recognition()
