import sys
import serial
import time
import sounddevice as sd
import numpy as np
from pydub import AudioSegment

# Parameters
serial_port = "COM45"  # Replace with your Arduino serial port
sample_rate = 208300  # sample rate
chunk_size = 32  # Size of audio chunks to send

def send_audio_to_arduino(serial_port, audio_data):
    zero_sample_count = 0  # Counter for 'Sending sample: 0'
    max_zero_samples = 1000  # Threshold for stopping

    with serial.Serial(serial_port, 115200, timeout=1) as ser:
        for i in range(0, len(audio_data), chunk_size):  # Send in chunks
            chunk = audio_data[i:i + chunk_size].tobytes()
            ser.write(chunk)
            time.sleep(0.01)  # Adjust sleep time as needed
            response = ser.readline().decode('utf-8').strip()
            print(response)
            
            # Check for 'Sending sample: 0'
            if response == 'Sending sample: 0':
                zero_sample_count += 1
            else:
                zero_sample_count = 0
            
            # Stop if 'Sending sample: 0' is received 10 times in a row
            if zero_sample_count >= max_zero_samples:
                print("Received 'Sending sample: 0' 10 times in a row. Stopping...")
                break

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    send_audio_to_arduino(serial_port, indata)

def send_mp3_to_arduino(mp3_file):
    # Load MP3 file
    audio = AudioSegment.from_mp3(mp3_file)
    # Convert to the appropriate sample rate and mono channel
    audio = audio.set_frame_rate(sample_rate).set_channels(1)
    # Extract raw audio data
    audio_data = np.array(audio.get_array_of_samples(), dtype=np.int16)
    # Send audio data to Arduino
    send_audio_to_arduino(serial_port, audio_data)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".mp3"):
        mp3_file = sys.argv[1]
        print(f"Sending MP3 file {mp3_file} to Arduino...")
        send_mp3_to_arduino(mp3_file)
    else:
        # Capture audio from microphone
        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, callback=audio_callback):
                print("Press Ctrl+C to stop the recording...")
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("Recording stopped.")
