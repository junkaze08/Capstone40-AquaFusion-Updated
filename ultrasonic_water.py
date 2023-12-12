# AquaFusion - BSIT 4A - CPSTONE
import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_WATER

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
realtime_db = db.reference(FIREBASE_WATER['sensorCollection'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_lower = db.reference(FIREBASE_WATER['sensorLower'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper = db.reference(FIREBASE_WATER['sensorUpper'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_normal = db.reference(FIREBASE_WATER['sensorNormal'], app=firebase_admin.get_app(name='realtime'))

water_normal = realtime_db_threshold_normal.get()

water_limits_lower = realtime_db_threshold_lower.get()

water_limits_upper = realtime_db_threshold_upper.get()

unique_Id = WORKGROUP_ID['uniqueId']

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

last_firestore_upload_time = time.time()

def on_threshold_change_lower(event):
    global water_limits_lower
    if event.data is not None:
        water_limits_lower = str(event.data)
        print("Threshold lower levels updated:", water_limits_lower)
    else:
        print("Threshold levels data not available in the database.")
    
def on_threshold_change_upper(event):
    global water_limits_upper
    if event.data is not None:
        water_limits_upper = str(event.data)
        print("Threshold upper levels updated:", water_limits_upper)
    else:
        print("Threshold levels data not available in the database.")

threshold_listener_lower = realtime_db_threshold_lower.listen(on_threshold_change_lower)
threshold_listener_upper = realtime_db_threshold_upper.listen(on_threshold_change_upper)

try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        time_period = time.strftime("%Y:%m:%d", curr_time)
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

            if distance >= 0:
                checkStatus = True

            lower_key = FIREBASE_WATER['sensorConditionalLower']
            upper_key = FIREBASE_WATER['sensorConditionalUpper']

            if water_normal and lower_key in water_normal and upper_key in water_normal:
                lower_limit = water_normal[lower_key]
                upper_limit = water_normal[upper_key]

                if distance <= 0:
                    water_status = "Error: Distance is not valid."
                elif distance < lower_limit:
                    water_status = "Warning: Low water level! Please refill."
                elif lower_limit <= distance <= upper_limit:
                    water_status = "Water level is within the optimal range."
                else:
                    water_status = f"Warning: High water level! {distance} Check for potential issues."
                
            print("Distance:", distance, "cm")
            print(form_time)
            print(water_status)

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
            
            firestore_upload_interval = 60 #60 seconds = 1 minute
            
            if (current_time - last_firestore_upload_time >= firestore_upload_interval): 
                last_firestore_upload_time = current_time

                data_firestore = {
                    "distance": distance,
                    "timestamp": form_time,
                    "timeperiod": time_period,
                    "workgroupId": unique_Id       
                }
                
                doc_ref = db.collection('ultrasonic_water').add(data_firestore)
        except KeyboardInterrupt:
            threshold_listener_lower.close()
            threshold_listener_upper.close()
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