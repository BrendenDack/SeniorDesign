import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer
import json
import yt_dlp as youtube_dl
import vlc
import os
import time
#didnt workout import pyautogui  # For controlling brightness
#didnt workout import screen_brightness_control as sbc  # For adjusting screen brightness
#didnt workout import pycaw  # For controlling system volume

# Audio Parameters
RATE = 48000 #44100 replace #16000 original rate used 
CHANNELS = 1
CHUNK = 1024 #512 #8000 original chunk size
WIDTH = 2

# Initialize Vosk model
model = Model('/home/brendendack/SeniorDesignCode/github_code/SeniorDesign/vosk-model-small-en-us-0.15')
rec = KaldiRecognizer(model, RATE)

input_device_index = 1  # Input device index (USB mic)
#input_device_index = 2
# Initialize PyAudio
audio = pyaudio.PyAudio()

# Open input stream with error handling, throwing exceptions 

#try audio jack first (nested try and except)
try:
    stream = audio.open(format=audio.get_format_from_width(WIDTH),
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=input_device_index,
                        frames_per_buffer=CHUNK)
except OSError as e:
    print(f"Error opening audio stream: {e}")
    exit()


# Initialize VLC player
player = vlc.MediaPlayer()

#Function to get YouTube URL
def get_youtube_url(song_name):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{song_name}", download=False)['entries'][0]
            return info['url']
        except Exception as e:
            print(f"Error finding YouTube URL: {e}")
            return None

#Function to detect wake word "Hey Music"
def detect_wake_word(audio_chunk):
    if rec.AcceptWaveform(audio_chunk):
        result = json.loads(rec.Result())
        if 'text' in result and "hey music" in result['text'].lower():
            return True
    return False

#Function to recognize command
def recognize_command(audio_chunk):
    if rec.AcceptWaveform(audio_chunk):
        result = json.loads(rec.Result())
        return result.get('text', '').lower()
    return ''

#Play/chose song function
def play_song(song_name):
    youtube_url = get_youtube_url(song_name)
    if youtube_url:
        player.set_mrl(youtube_url)
        player.play()
        print(f"Now playing: {song_name}")
    else:
        print("Could not find a playable source for the song")

#pause function
def pause_song():
    player.pause()
    print("Song paused.")

#resume function
def resume_song():
    player.play()
    print("Song resumed.")

#next song function
def next_song():
    player.stop() #recheck this function 
    print("Playing next song...")
    #wait to see where music is coming from 


print("Listening for 'Hey Music' command... Press Ctrl+C to stop.")

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
            print("'Hey Music' command detected! Listening for next command...")

            while True:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)  # Prevent overflow crash
                except IOError as e:
                    print(f"Overflow error: {e}. Restarting stream...")
                    stream.stop_stream()
                    stream.start_stream()
                    continue

                command = recognize_command(data)
                if command:
                    print(f"Recognized command: {command}")
                    if "play" in command:
                        song_name = command.replace("play", "").strip()
                        play_song(song_name)
                    elif "pause" in command:
                        pause_song()
                    elif "resume" in command:
                        resume_song()
                    elif "next" in command:
                        next_song()
                    else:
                        print("Command not recognized.")
                    break
            print("Listening for 'Hey Music' command...")
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