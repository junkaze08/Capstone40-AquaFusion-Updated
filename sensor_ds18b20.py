import glob
import time
import pyrebase
import board
import busio
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG

# Initialize Firebase Admin for Realtime Database
cred = credentials.Certificate(FIREBASE_CONFIG['serviceAccountKeyPath'])
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_CONFIG['databaseURL']
}, name='realtime')

# Initialize Firebase Admin for Firestore
cred_firestore = credentials.Certificate(FIREBASE_CONFIG['serviceAccountKeyPath'])
firebase_admin.initialize_app(cred_firestore, {
    'projectId': FIREBASE_CONFIG['projectId'],  # Add your Firebase project ID
}, name='firestore')

# Initialize Realtime Database
realtime_db = db.reference('/Temperature', app=firebase_admin.get_app(name='realtime'))

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()
last_realtime_upload_time = time.time()

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

while True:
    temperature = round(read_temp(), 1)

    # Get the current time
    current_time = time.time()

    if temperature is not None:
        print(f"Temperature: {temperature}°C")

        if (current_time - last_realtime_upload_time) >= 1:  # Upload to Realtime Database every 5 seconds
            data_realtime_db = {"temperature": temperature}
            realtime_db.set(data_realtime_db)
            last_realtime_upload_time = current_time

        if (current_time - last_firestore_upload_time) >= 60:  # Upload to Firestore every 60 seconds
            data_firestore = {"temperature": temperature}
            doc_ref = db.collection('Temperature').add(data_firestore)
            last_firestore_upload_time = current_time

    else:
        print("Error reading temperature data")

    time.sleep(1)
