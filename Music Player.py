import random

# Global variable to track the song playlist and current song index
song_playlist = []
current_song_index = 0

# Shuffle song playlist
def shuffle_audio():
    global song_playlist
    random.shuffle(song_playlist)

# Play a song 
def play_song(index):
    global song_playlist
    if 0 <= index < len(song_playlist):
        fs, data = read_wav_file(song_playlist[index])
        display(Audio(data, rate=fs))
    else:
        print("Invalid index")

# Play the next song in the shuffled list
def play_next_song_shuffled():
    global current_song_index, song_playlist
    current_song_index = (current_song_index + 1) % len(song_playlist)  
    play_song(current_song_index)

# Play the previous song in the shuffled list
def play_previous_song_shuffled():
    global current_song_index, song_playlist
    current_song_index = (current_song_index - 1) % len(song_playlist) 
    play_song(current_song_index)

# Play the next song in the original list (not shuffled)
# Loop around to the first song if at the end
def play_next_song():
    global current_song_index, song_playlist
    current_song_index = (current_song_index + 1) % len(song_playlist)  
    play_song(current_song_index)

# Play the previous song in the original list (not shuffled)
# Loop around to the last song if at the beginning
def play_previous_song():
    global current_song_index, song_playlist
    current_song_index = (current_song_index - 1) % len(song_playlist)  
    play_song(current_song_index)


# Repeat the current song
def repeat_song():
    global current_song_index, num_repeats
    repeated_song = current_song_index * num_repeats 
    play_song(repeated_song)
