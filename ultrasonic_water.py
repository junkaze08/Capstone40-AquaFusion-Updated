# AquaFusion - BSIT 4A - CPSTONE
import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID

TRIG = 23
ECHO = 24

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
realtime_db = db.reference('/ultrasonic_water', app=firebase_admin.get_app(name='realtime'))

unique_Id = WORKGROUP_ID['uniqueId']

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

last_firestore_upload_time = time.time()

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        try:
            GPIO.output(TRIG, False)
            time.sleep(2)

            GPIO.output(TRIG, True)
            time.sleep(0.00001)
            GPIO.output(TRIG, False)

            while GPIO.input(ECHO) == 0:
                pulse_start = time.time()

            while GPIO.input(ECHO) == 1:
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150
            distance = round(distance, 2)

            threshold_low = 5  # minimum distance for low water level
            threshold_high = 20  # maximum distance for high water level

            if distance >= 0:
                checkStatus = True

            if distance <= 0:
                water_status = "Error: Distance is not valid."
            elif distance < threshold_low:
                water_status = "Warning: Low water level! Please refill."
            elif threshold_low <= distance <= threshold_high:
                water_status = "Water level is within the optimal range."
            else:
                water_status = f"Warning: High water level! {distance} Check for potential issues."

            print("Distance:", distance, "cm")
            print(form_time)
            print(water_status)
            print(checkStatus)

            # Dictionary with the data to send to Firebase Realtime Database
            data_realtime_db = {
                "Status": checkStatus,
                "distance": distance,
                "status_notif": water_status            
            }

            # Send the data to Firebase Realtime Database
            realtime_db.update(data_realtime_db)

            # Get the current time
            current_time = time.time()
            
            firestore_upload_interval = 5
            
            if (current_time - last_firestore_upload_time >= firestore_upload_interval): 
                last_firestore_upload_time = current_time

                data_firestore = {
                    "distance": distance,
                    "timestamp": form_time,
                    "workgroupId": unique_Id       
                }
                
                doc_ref = db.collection('ultrasonic_water').add(data_firestore)
        except KeyboardInterrupt:
            print("Measurement stopped by the user.")
            checkStatus = False
            data_realtime_db = {
                "Status": checkStatus,    
            }
            realtime_db.update(data_realtime_db)
            break
                
finally:
    GPIO.cleanup()
    time.sleep(1)