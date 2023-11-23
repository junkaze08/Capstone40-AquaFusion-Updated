# AquaFusion - BSIT 4A - CPSTONE
import subprocess
import signal
import time

y = 0.1

python3_path = '/usr/bin/python3'

process1 = subprocess.Popen([python3_path, 'ultra_plant.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'ultra_water.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'sensor_analogTDS.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'sensor_DHT22.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'sensor_ds18b20.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'sensor_PH_Level.py'])

time.sleep(y)

process2 = subprocess.Popen([python3_path, 'sensor_checker.py'])

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Ctrl+C detected. Stopping processes...")
    process1.send_signal(signal.SIGINT)
    process2.send_signal(signal.SIGINT)

#Eradicating __pycache__    
#find . | grep -E "__pycache__" | xargs rm -rf