from __future__ import division
import RPi.GPIO as GPIO
import time
import signal
import sys
import numpy as np
from scikits.audiolab import play


TRIG = 23
ECHO = 24

CHUNK = 4096*2
RATE = 44100

TIME_BETWEEN_MEASURE = 0.0001 # in seconds
IGNORE_DISTANCE_THRESHOLD = 5.00 # in meters

GPIO.setmode(GPIO.BCM)


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


def play_sin(f=440.0, duration=1.0, volume=0.5, sampling_rate=44100):
  # cycles per sample
  cps = f / sampling_rate
  # total samples
  ts = duration * sampling_rate
  samples = volume * np.sin(np.arange(0,ts*cps,cps) * (2*np.pi))
  play(samples)


signal.signal(signal.SIGINT, signal_handler) # catch SIGINT

GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)

GPIO.output(TRIG, False)
print("Waiting For Sensor To Settle")
time.sleep(2)
print("Now doing stuff")

def quick_f(distance):
  f = (distance * 100.) + 400
  if f < 50: f = 50.
  if f > 10000: f = 10000.0
  return f

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
    #play_sin(distance * 100 - 400)
    play_sin(quick_f(distance))
  elif distance > trigger.HI_THRESHOLD and trigger.active:
    t = time.time()
    if t - trigger.last_deactivation_timestamp > trigger.COOLOFF:
      trigger.last_deactivation_timestamp = t
      trigger.active = False
      print("END OF TRIGGER - distance (m):", distance)
  elif distance < trigger.HI_THRESHOLD and trigger.active:
    #play_sin(distance * 100 - 400)
    play_sin(quick_f(distance))

      
  #time.sleep(TIME_BETWEEN_MEASURE)

