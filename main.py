# AquaFusion - BSIT 4A - CPSTONE
import subprocess
import signal
import time
import os

y = 5

python3_path = '/usr/bin/python3'

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'ultrasonic_plant.py'])

time.sleep(y)

process3 = subprocess.Popen([python3_path, 'ultrasonic_water.py'])

time.sleep(y)

process4 = subprocess.Popen([python3_path, 'sensor_analogTDS.py'])

time.sleep(y)

process5 = subprocess.Popen([python3_path, 'sensor_DHT22.py'])

time.sleep(y)

process6 = subprocess.Popen([python3_path, 'sensor_ds18b20.py'])

time.sleep(y)

process7 = subprocess.Popen([python3_path, 'sensor_PH_Level.py'])

time.sleep(y)

try:
    while True:
        time.sleep(10)
        os.system('clear')
except KeyboardInterrupt:
    print("Ctrl+C detected. Stopping processes...")
    process2.send_signal(signal.SIGINT)
    process3.send_signal(signal.SIGINT)
    process4.send_signal(signal.SIGINT)
    process5.send_signal(signal.SIGINT)
    process6.send_signal(signal.SIGINT)
    process7.send_signal(signal.SIGINT)

#Eradicating __pycache__    
#find . | grep -E "__pycache__" | xargs rm -rf