import time
import numpy
import pyaudio
import math
import RPi.GPIO as GPIO
import signal
import sys


TRIG = 23
ECHO = 24
RATE = 44100
TIME_BETWEEN_MEASURE = 0.001 # in seconds
IGNORE_DISTANCE_THRESHOLD = 9.00 # in meters


last_phase = 0
distance = 1.0

GPIO.setmode(GPIO.BCM)

class Stats(object):
  min_d = 10000.0
  max_d = 0.0

class Trigger(object):
  LO_THRESHOLD = 0.80 # in m
  HI_THRESHOLD = 1.00 # in m
  MAX_IN_TRIGGER = 7.0 # in seconds
  COOLOFF = 0.5 # in seconds

  def __init__(self):
    self.active = False
    self.last_deactivation_timestamp = 0.0
    self.activation_timestamp = 0.0

trigger = Trigger()

def signal_handler(signal, frame):
  print("You probably pressed Ctrl+C.")
  print("Stats: minimum distance:", Stats.min_d, "m, maximum distance:", Stats.max_d, "m")
  print("Quitting quickly and gracefully.")
  GPIO.cleanup()

  sys.exit(0)

def sine(frame_count, frequency=440):
    #frequency = int((math.sin(5*time.time())+1)*100+400)
    #frequency = quick_f(distance)
    frequency = quick_f()
    length = frame_count*1
    factor = float(frequency) * (math.pi * 2) / RATE

    indices = numpy.arange(length)

    global last_phase
    phase_array = indices * factor + last_phase

    last_phase = phase_array[-1] % (math.pi*2)

    wave = numpy.sin(phase_array)
    return wave

def square(frequency=440):
    return numpy.tile(numpy.hstack([numpy.zeros(8), numpy.ones(8)]), 256)

def get_chunk(frame_count):
    data = sine(frame_count)
    #data = square()
    return data * 0.1

def callback(in_data, frame_count, time_info, status):
    global trigger
    if not trigger.active:
      return (None, pyaudio.paContinue)
    chunk = get_chunk(frame_count) * 0.75
    data = chunk.astype(numpy.float32).tostring()
    return (data, pyaudio.paContinue)

p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paFloat32,
                channels = 1,
                rate = RATE,
                output = True,
                stream_callback = callback)

def measure(round_figures=6):
  GPIO.output(TRIG, True)
  time.sleep(0.00001) # 10 microseconds
  GPIO.output(TRIG, False)
  
  while GPIO.input(ECHO)==0: # before echo is sent
    pulse_start = time.time()
    #time.sleep(0.00001)
  
  while GPIO.input(ECHO)==1: # now we wait 
    pulse_end = time.time()
    time.sleep(0.00001)
  
  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 171.5 # (343 m divided by two)
  distance = round(distance, round_figures)
  
  return distance

def quick_f(d=None):
  if d is None:
    global distance
    d = distance
  #f = (d * 100.) * 10 + 200
  f = (d * 50.) ** 2.0 + 200
  if f < 50: f = 50.
  if f > 10000: f = 10000.0
  return f

signal.signal(signal.SIGINT, signal_handler) # catch SIGINT
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
GPIO.output(TRIG, False)
print("Waiting For Sensor To Settle")
time.sleep(2)
print("Now doing stuff")

while True:
  distance = measure()
  if distance > IGNORE_DISTANCE_THRESHOLD:
    continue
  if distance < Stats.min_d:
    Stats.min_d = distance
  if distance > Stats.max_d:
    Stats.max_d = distance

  #print("Distance:", distance * 100.0, "cm")

  if distance < trigger.LO_THRESHOLD and not trigger.active:
    trigger.activation_timestamp = time.time()
    stream.start_stream()
    trigger.active = True
    print("TRIGGERED NOW - distance (m):", distance)
  elif distance > trigger.HI_THRESHOLD and trigger.active:
    t = time.time()
    if t - trigger.last_deactivation_timestamp > trigger.COOLOFF:
      trigger.last_deactivation_timestamp = t
      stream.stop_stream()
      trigger.active = False
      print("END OF TRIGGER - distance (m):", distance)
  elif trigger.active and time.time() - trigger.activation_timestamp > trigger.MAX_IN_TRIGGER:
    trigger.last_deactivation_timestamp = time.time()
    stream.stop_stream()
    trigger.active = False
    print("Forcing trigger to stop - distance (m):", distance)
      
  time.sleep(TIME_BETWEEN_MEASURE)


