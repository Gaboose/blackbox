import RPi.GPIO as GPIO
import time
import signal
import sys
import pyaudio
import numpy as np

GPIO.setmode(GPIO.BCM)

TRIG = 23 
ECHO = 24

TIME_BETWEEN_MEASURE = 0.005 # in seconds
IGNORE_DISTANCE_THRESHOLD = 5.00 # in meters


class Stats(object):
  min_d = 10000.0
  max_d = 0.0


class Trigger(object):
  LO_THRESHOLD = 1.00 # in m
  HI_THRESHOLD = 1.20 # in m
  COOLOFF = 0.5 # in seconds

  def __init__(self):
    self.active = False
    self.last_deactivation_timestamp = 0.0
trigger = Trigger()
    

def signal_handler(signal, frame):
  print("You probably pressed Ctrl+C.")
  print("Stats: minimum distance:", Stats.min_d, "m, maximum distance:", Stats.max_d, "m")
  print("Quitting quickly and gracefully.")
  GPIO.cleanup()

  sys.exit(0)


def measure(round_figures=6):
  GPIO.output(TRIG, True)
  time.sleep(0.00001) # 10 microseconds
  GPIO.output(TRIG, False)
  
  while GPIO.input(ECHO)==0: # before echo is sent
    pulse_start = time.time()
  
  while GPIO.input(ECHO)==1: # now we wait 
    pulse_end = time.time()
  
  pulse_duration = pulse_end - pulse_start
  distance = pulse_duration * 171.5 # (343 m divided by two)
  distance = round(distance, round_figures)
  
  return distance


def play_sin(f=495.0, duration=0.5, volume=0.5, sampling_rate=44100):
  global p, stream
  # generate samples, note conversion to float32 array
  #samples = (np.sin(2*np.pi*np.arange(sampling_rate*duration)*f/sampling_rate))\
  #  .astype(np.float32)
  samples = (np.sin(2*np.pi*np.arange(0, (sampling_rate*duration) * (f/sampling_rate), f/sampling_rate)))\
    .astype(np.float32)
  
  # play. May repeat with different volume values (if done interactively) 
  stream.write(volume*samples)

  #stream.stop_stream()
  #stream.close()
  #p.terminate()


signal.signal(signal.SIGINT, signal_handler) # catch SIGINT
p = pyaudio.PyAudio()
# for paFloat32 sample values must be in range [-1.0, 1.0]
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                output=True)


GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)

GPIO.output(TRIG, False)
print("Waiting For Sensor To Settle")
time.sleep(2)

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
    trigger.active = True
    print("TRIGGERED NOW - distance (m):", distance)
    # play. May repeat with different volume values (if done interactively) 
    play_sin()
  elif distance > trigger.HI_THRESHOLD and trigger.active:
    t = time.time()
    if t - trigger.last_deactivation_timestamp > trigger.COOLOFF:
      trigger.last_deactivation_timestamp = t
      trigger.active = False
      print("END OF TRIGGER - distance (m):", distance)
      
  time.sleep(TIME_BETWEEN_MEASURE)

