import RPi.GPIO as GPIO
import time
import signal
import sys

GPIO.setmode(GPIO.BCM)

TRIG = 23 
ECHO = 24

TIME_BETWEEN_MEASURE = 0.10 # in seconds


class Stats(object):
  min_d = 10000.0
  max_d = 0.0


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


signal.signal(signal.SIGINT, signal_handler) # catch SIGINT


GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)

GPIO.output(TRIG, False)
print("Waiting For Sensor To Settle")
time.sleep(2)

while True:
  distance = measure()
  if distance < Stats.min_d: Stats.min_d = distance
  if distance > Stats.max_d: Stats.max_d = distance
  print("Distance:", distance * 100.0, "cm")
  time.sleep(TIME_BETWEEN_MEASURE)

