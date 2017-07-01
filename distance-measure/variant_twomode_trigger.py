import time
import numpy
import pyaudio
import math
import RPi.GPIO as GPIO
import signal
import sys
import os
import random
import pygame
from pygame import mixer


TRIG = 23
ECHO = 24
RATE = 44100
TIME_BETWEEN_MEASURE = 0.001 # in seconds
IGNORE_DISTANCE_THRESHOLD = 2.50 # in meters
LOOP_ESCAPE_TIME = 3.0 # seconds until forced loop escape in measurement
MODE_FILE = "/home/pi/Desktop/distance-measure/mode.txt"
MUSIC_DIR = "/home/pi/Desktop/file-upload/sounds"
SIMULTANEOUS_MUSIC = False
SEC_BEFORE_START = 2.0


last_phase = 0
distance = 1.0
mode = 1 # default mode = music playing mode
last_file = None

avg_distance = 1.0
last_distances = [1.0]

mixer.init(channels=4)
music_files = [f for f in os.listdir(MUSIC_DIR) if os.path.isfile(os.path.join(MUSIC_DIR, f))]
print("Music files which we'll be choosing from:", music_files)

print("Waiting %d seconds before touching GPIO (assuming system is starting)..." % SEC_BEFORE_START)
time.sleep(SEC_BEFORE_START)

GPIO.setmode(GPIO.BCM)

class Stats(object):
  def __init__(self):
    self.min_d = 10000.0
    self.max_d = 0.0

stats = Stats()

class Trigger(object):
  LO_THRESHOLD = 0.80 # in m
  HI_THRESHOLD = 0.88 # in m
  MAX_IN_TRIGGER = 7.0 # in seconds
  COOLOFF = 0.5 # in seconds

  def __init__(self):
    self.active = False
    self.last_deactivation_timestamp = 0.0
    self.activation_timestamp = 0.0

trigger = Trigger()

def signal_handler(signal, frame):
  global stats
  print("You probably pressed Ctrl+C.")
  print("Stats: minimum distance:", stats.min_d, "m, maximum distance:", stats.max_d, "m")
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
    if not trigger.active or not mode == 2:
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
  
  init_start = pulse_start = time.time()
  while GPIO.input(ECHO)==0: # before echo is sent
    pulse_start = time.time()
    if pulse_start - init_start > LOOP_ESCAPE_TIME:
      print("Breaking out of measurement loop (wait before signal sent phase)")
      return 0.031415 # return something reasonable
    #time.sleep(0.00001)
  
  init_start = pulse_end = time.time()
  while GPIO.input(ECHO)==1: # now we wait 
    pulse_end = time.time()
    if pulse_end - init_start > LOOP_ESCAPE_TIME:
      print("Breaking out of measurement loop (wait for signal return phase)")
      return 0.031415
    time.sleep(0.00001)
  
  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 171.5 # (343 m divided by two)
  distance = round(distance, round_figures)
  
  return distance

def quick_f(d=None):
  if d is None:
    global avg_distance
    d = avg_distance
  #f = (d * 50.) * 1 + 200
  f = (d * 50.) ** 2.0 + 300
  #f = (d * 100.) * 2.0 + 300
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

n = 1
while True:
  distance = measure()
  if distance > IGNORE_DISTANCE_THRESHOLD:
    continue
  if distance < stats.min_d:
    stats.min_d = distance
  if distance > stats.max_d:
    stats.max_d = distance

  last_distances.append(distance)
  last_distances = last_distances[-5:]
  avg_distance = sum(last_distances)/len(last_distances)

  #print("Distance:", distance * 100.0, "cm")

  if distance < trigger.LO_THRESHOLD and not trigger.active:
    trigger.activation_timestamp = time.time()
    trigger.active = True
    print("(mode=%d, n=%d)" % (mode, n), "TRIGGERED NOW - distance (m):", distance)
    if mode == 2: # variant frequency from distance mode
      stream.start_stream()
    elif mode == 1: # music mode
      try:
        last_lastfile = last_file
        while True:
          mfile = random.choice(music_files)
          if mfile != last_file:
            break
          print("Chose to play same file as before - continuing to search for file")
        last_file = mfile
        if not SIMULTANEOUS_MUSIC:
          if mixer.music.get_busy():
            print("(Still playing last file)")
            last_file = last_lastfile # reset last_file from before
          else:
            print("Playing", mfile)
            mixer.music.load(os.path.join(MUSIC_DIR, mfile))
            mixer.music.play()
        else:
          while True: # can only play one .mp3 at once (but multiple .wav's)
            if not (mfile.endswith(".mp3") and mixer.music.get_busy()):
              break
            else:
              print("Re-choosing file, or waiting for last .mp3 to finish")
            mfile = random.choice(music_files)
          print("Playing", mfile)
          if mfile.endswith(".mp3"):
            mixer.music.load(os.path.join(MUSIC_DIR, mfile))
            if not mixer.music.get_busy():
              mixer.music.play()
          else:
            sound = mixer.Sound(os.path.join(MUSIC_DIR, mfile))
            chan = mixer.find_channel()
            if chan:
              chan.queue(sound)
            else:
              print("(Still playing last file and all sound channels busy)")
      except pygame.error as e:
        print("Exception while attempting to play " + mfile + " - pygame error:", e)
      except:
        print("Exception while attempting to play " + mfile + ":", sys.exc_info()[0])
          
    else: # silent mode
      pass
      
  elif distance > trigger.HI_THRESHOLD and trigger.active:
    t = time.time()
    if t - trigger.last_deactivation_timestamp > trigger.COOLOFF:
      trigger.last_deactivation_timestamp = t
      stream.stop_stream()
      trigger.active = False
      print("(mode=%d, n=%d)" % (mode, n), "END OF TRIGGER - distance (m):", distance)
  elif trigger.active and time.time() - trigger.activation_timestamp > trigger.MAX_IN_TRIGGER:
    trigger.last_deactivation_timestamp = time.time()
    stream.stop_stream()
    trigger.active = False
    print("Forcing trigger to stop - distance (m):", distance)
      
  if n % 50 == 0:
    try:
      with open(MODE_FILE) as f:
        mode_int = int(f.readline().split()[0])
        if mode_int in (0, 1, 2):
          mode = mode_int
    except:
      print("Exception while reading mode file:", sys.exc_info()[0])
  if n % 1000 == 0:
    try:
      music_files = [f for f in os.listdir(MUSIC_DIR) if os.path.isfile(os.path.join(MUSIC_DIR, f))]
      print("(mode=%d, n=%d)" % (mode, n), "Reloaded music file list (number of files: %d)" % len(music_files))
    except:
      pass

  n += 1
  time.sleep(TIME_BETWEEN_MEASURE)

