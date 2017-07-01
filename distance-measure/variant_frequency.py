import time
import numpy
import pyaudio
import math

CHUNK = 4096*2
RATE = 44100

myb = False
lch = 0
ph = (0, 1)
last_phase = 0

def sine(current_time, frame_count, frequency=440):
    frequency = int((math.sin(5*time.time())+1)*100+400)
    #frequency = 440
    length = frame_count*2
    factor = float(frequency) * (math.pi * 2) / RATE

    global last_phase
    indices = numpy.arange(length)

    phase_array = indices * factor + last_phase

    last_phase = phase_array[-1] % (math.pi*2)

    wave = numpy.sin(phase_array)
    return wave

def square(frequency=440):
    return numpy.tile(numpy.hstack([-numpy.zeros(8), numpy.ones(8)]), 256)

def get_chunk(frame_count):
    data = sine(time.time(), frame_count)
    #data = square()
    return data * 0.1

def callback(in_data, frame_count, time_info, status):
    chunk = get_chunk(frame_count) * 0.25
    data = chunk.astype(numpy.float32).tostring()
    return (data, pyaudio.paContinue)

p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paFloat32,
                channels = 2,
                rate = RATE,
                output = True,
                stream_callback = callback)

stream.start_stream()

while stream.is_active():
    time.sleep(0.1)

stream.stop_stream()
stream.close()
