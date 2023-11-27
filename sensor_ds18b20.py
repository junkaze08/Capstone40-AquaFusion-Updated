import glob
import time
import pyrebase
import board
import busio
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID

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
realtime_db = db.reference('/DS18B20_water_temperature', app=firebase_admin.get_app(name='realtime'))

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

unique_Id = WORKGROUP_ID['uniqueId']

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()
last_realtime_upload_time = time.time()

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

utc_offset = 8

curr_time = time.gmtime(time.time() + utc_offset * 3600)
form_time = time.strftime("%H:%M:%S", curr_time)

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
        print(form_time)

        if temperature < 18:
            temperature_status = "Warning: Cold Temperature"
        elif 18 <= temperature <= 26:
            temperature_status = "Optimal Temperature"
        else:
            temperature_status = "Warning: Hot Temperature"
        
        if (current_time - last_realtime_upload_time) >= 1:  # Upload to Realtime Database every 5 seconds
            
            data_realtime_db = {
                "temperature": temperature,
                "status_notif": temperature_status
            }
            
            realtime_db.update(data_realtime_db)
            last_realtime_upload_time = current_time

        if (current_time - last_firestore_upload_time) >= 5:  # Upload to Firestore every 60 seconds
            data_firestore = {
                "temperature": temperature,
                "timestamp": form_time,
                "workgroupId": unique_Id
            }
            
            doc_ref = db.collection('DS18B20_water_temperature').add(data_firestore)
            last_firestore_upload_time = current_time

    else:
        print("Error reading temperature data")

    time.sleep(1)
