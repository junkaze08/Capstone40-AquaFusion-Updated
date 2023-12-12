# AquaFusion - BSIT 4A - CPSTONE
import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_PLANT

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
realtime_db = db.reference(FIREBASE_PLANT['sensorCollection'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_lower = db.reference(FIREBASE_PLANT['sensorLower'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper = db.reference(FIREBASE_PLANT['sensorUpper'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_normal = db.reference(FIREBASE_PLANT['sensorNormal'], app=firebase_admin.get_app(name='realtime'))

plant_normal = realtime_db_threshold_normal.get()

plant_limits_lower = realtime_db_threshold_lower.get()

plant_limits_upper = realtime_db_threshold_upper.get()

unique_Id = WORKGROUP_ID['uniqueId']

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

last_firestore_upload_time = time.time()

def on_threshold_change_lower(event):
    global plant_limits_lower
    if event.data is not None:
        plant_limits_lower = str(event.data)
        print("Threshold lower levels updated:", plant_limits_lower)
    else:
        print("Threshold levels data not available in the database.")
    
def on_threshold_change_upper(event):
    global plant_limits_upper
    if event.data is not None:
        plant_limits_upper = str(event.data)
        print("Threshold upper levels updated:", plant_limits_upper)
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

            lower_key = FIREBASE_PLANT['sensorConditionalLower']
            upper_key = FIREBASE_PLANT['sensorConditionalUpper']

            # Conditional statements based on distance
            if plant_normal and lower_key in plant_normal and upper_key in plant_normal:
                lower_limit = plant_normal[lower_key]
                upper_limit = plant_normal[upper_key]
            
                if distance <= 0:
                    plant_status = "Error: Distance is not valid."
                elif distance < upper_limit:
                    plant_status = "The plant is growing."
                elif lower_limit <= distance <= upper_limit:
                    plant_status = "The plant has reached maximum growth."
                else:
                    plant_status = f"Warning: Unexpected distance value of {distance}. Check sensor or system."
                            
            print("Distance:", distance, "cm")
            print(form_time)
            print(plant_status)

            # Dictionary with the data to send to Firebase Realtime Database
            data_realtime_db = {
                "Status": checkStatus,
                "distance": distance,          
                "status_notif": plant_status
            }

            # Send the data to Firebase Realtime Database
            realtime_db.update(data_realtime_db)

            # Get the current time
            current_time = time.time()
            
            if (current_time - last_firestore_upload_time) >= 60:  #60 seconds = 1 minute
                last_firestore_upload_time = current_time

                data_firestore = {
                    "distance": distance,
                    "timestamp": form_time,
                    "timeperiod": time_period,       
                    "workgroupId": unique_Id       
                }
                
                doc_ref = db.collection('ultrasonic_plant').add(data_firestore)
        except KeyboardInterrupt:
            threshold_listener_lower.close()
            threshold_listener_upper.close()
            checkStatus = False
            data_realtime_db = {
                "Status": checkStatus,    
            }
            realtime_db.update(data_realtime_db)
            print("Measurement stopped by the user.")
            break
                
finally:
    GPIO.cleanup()
    time.sleep(1)
