# AquaFusion - BSIT 4A - CPSTONE
import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG

TRIG = 27
ECHO = 22

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
realtime_db = db.reference('/ultrasonic_plant', app=firebase_admin.get_app(name='realtime'))

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

last_firestore_upload_time = time.time()

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

    while True:
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

            print("Distance:", distance, "cm")

            # Dictionary with the data to send to Firebase Realtime Database
            data_realtime_db = {
                "distance": distance            
            }

            # Send the data to Firebase Realtime Database
            realtime_db.update(data_realtime_db)

            # Get the current time
            current_time = time.time()
            
            if (current_time - last_firestore_upload_time) >= 60:  #60 seconds = 1 minute
                last_firestore_upload_time = current_time

                data_firestore = {
                    "distance": distance              
                }
                
                doc_ref = db.collection('ultrasonic_plant').add(data_firestore)
        except KeyboardInterrupt:
            print("Measurement stopped by the user.")
            break
                
finally:
    GPIO.cleanup()
    time.sleep(2)
