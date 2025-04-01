import numpy as np
import threading
import queue
import PyAudio

# Set up PyAudio
audio = pyaudio.PyAudio()
audio_queue = queue.Queue()

# Create a buffer to hold the delayed samples
CHUNK = 2**12
buffer = np.zeros(CHUNK)

# Input data thread
def input_thread(audio, input_device_index, chunk, fs, channels, width):
    input_stream = audio.open(format=audio.get_format_from_width(width),
                                channels=channels,
                                rate=fs,
                                input=True,
                                input_device_index=input_device_index,
                                frames_per_buffer=chunk)
    try:
        while True:
            data = input_stream.read(chunk)
            # Convert data to a NumPy array with the appropriate dtype
            data = np.frombuffer(data, dtype=np.float32) # assuming 32-bit audio
            # Convert to float64
            data = data.astype(np.float64)

            # Convert back to bytes before putting it in the queue
            data = data.astype(np.float32).tobytes()
            audio_queue.put(data)
    except Exception as e:
        print(f"Input thread error: {e}")
    finally:
        input_stream.stop_stream()
        input_stream.close()

# Output data thread
def output_thread(audio, output_device_index, fs, channels, width):
    output_stream = audio.open(format=audio.get_format_from_width(width),
    channels=channels,
    rate=fs,
    output=True,
    output_device_index=output_device_index)
    try:
        while True:
            data = audio_queue.get()
            if data is None:
                break
            output_stream.write(data)
    except Exception as e:
        print(f"Output thread error: {e}")
    finally:
        output_stream.stop_stream()
        output_stream.close()

INPUT_DEVICE_INDEX = 0
OUTPUT_DEVICE_INDEX = 1
SAMPLE_RATE = 44100
CHANNELS = 2
WIDTH = 2

# Create and start the input and output threads
input_thread = threading.Thread(target=input_thread, args=(audio, INPUT_DEVICE_INDEX, CHUNK,
SAMPLE_RATE, CHANNELS, WIDTH))
output_thread = threading.Thread(target=output_thread, args=(audio, OUTPUT_DEVICE_INDEX, SAMPLE_RATE,
CHANNELS, WIDTH))
input_thread.start()
output_thread.start()
print("Recording and playing back audio...")
print("Original")
try:
    input_thread.join()
    output_thread.join()
except KeyboardInterrupt:
    print("Interrupted by user, stopping...")
    audio_queue.put(None)
    input_thread.join()
    output_thread.join()
    # Terminate the PyAudio object
    audio.terminate()