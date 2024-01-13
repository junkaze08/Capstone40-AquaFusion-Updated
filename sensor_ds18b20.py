import glob
import time
import pyrebase
import board
import busio
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_DS18B20

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
realtime_db = db.reference(FIREBASE_DS18B20['sensorCollection'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_lower = db.reference(FIREBASE_DS18B20['sensorLower'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper = db.reference(FIREBASE_DS18B20['sensorUpper'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_normal = db.reference(FIREBASE_DS18B20['sensorNormal'], app=firebase_admin.get_app(name='realtime'))

temperature_normal = realtime_db_threshold_normal.get()

temperature_limits_lower = realtime_db_threshold_lower.get()

temperature_limits_upper = realtime_db_threshold_upper.get()

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

unique_Id = WORKGROUP_ID['uniqueId']

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

def on_threshold_change_lower(event):
    global temperature_limits_lower
    if event.data is not None:
        temperature_limits_lower = str(event.data)
        print("Threshold lower levels updated:", temperature_limits_lower)
    else:
        print("Threshold levels data not available in the database.")
    
def on_threshold_change_upper(event):
    global temperature_limits_upper
    if event.data is not None:
        temperature_limits_upper = str(event.data)
        print("Threshold upper levels updated:", temperature_limits_upper)
    else:
        print("Threshold levels data not available in the database.")

threshold_listener_lower = realtime_db_threshold_lower.listen(on_threshold_change_lower)
threshold_listener_upper = realtime_db_threshold_upper.listen(on_threshold_change_upper)

prev_temp_status = None
prev_sensor_status = None
notif_title = "Water Temperature Alert"
notif_type = "alert"

try:
    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        time_period = time.strftime("%Y:%m:%d", curr_time)
        date_time = time.strftime("%m/%d/%Y", curr_time)
        
        temperature = round(read_temp(), 1)

        # Get the current time
        current_time = time.time()
        
        if temperature is not None:
            print(f"Temperature: {temperature}°C")
            print(form_time)
            
            if temperature >= 0:
                checkStatus = True
                sensor_status = "On"
        
                if sensor_status != prev_sensor_status:
                        prev_sensor_status = sensor_status

                        data_firestore_status = {
                            "notificationDate": date_time,
                            "notificationDescription": prev_sensor_status,
                            "notificationTitle": notif_title,
                            "notificationTimestamp": form_time,
                            "notificationType": notif_type,
                            "workgroupId": unique_Id
                        }
                        
                        doc_ref_alert_status = db.collection('notifications').add(data_firestore_status)

            lower_key = FIREBASE_DS18B20['sensorConditionalLower']
            upper_key = FIREBASE_DS18B20['sensorConditionalUpper']

            if temperature_normal and lower_key in temperature_normal and upper_key in temperature_normal:
                lower_limit = temperature_normal[lower_key]
                upper_limit = temperature_normal[upper_key]
                
                if temperature < lower_limit:
                    temperature_status = "Warning: Cold Temperature"
                elif lower_limit <= temperature <= upper_limit:
                    temperature_status = "Optimal Temperature"
                else:
                    temperature_status = "Warning: Hot Temperature"
                
                if temperature_status != prev_temp_status:
                # Update the previous pH status
                    prev_temp_status = temperature_status

                    data_firestore_alert = {
                        "notificationDate": date_time,
                        "notificationDescription": prev_temp_status,
                        "notificationTitle": notif_title,
                        "notificationTimestamp": form_time,
                        "notificationType": notif_type,
                        "workgroupId": unique_Id
                    }
                
                    doc_ref_alert = db.collection('notifications').add(data_firestore_alert)
                    
            print(temperature_status)
            
            if (current_time - last_realtime_upload_time) >= 1:  # Upload to Realtime Database every 5 seconds
                
                data_realtime_db = {
                    "Status": checkStatus,
                    "temperature": temperature,
                    "status_notif": temperature_status
                }
                
                realtime_db.update(data_realtime_db)
                last_realtime_upload_time = current_time

            if (current_time - last_firestore_upload_time) >= 5:  # Upload to Firestore every 60 seconds
                data_firestore = {
                    "temperature": temperature,
                    "timestamp": form_time,
                    "timeperiod": time_period,
                    "workgroupId": unique_Id
                }
                
                doc_ref = db.collection('DS18B20_water_temperature').add(data_firestore)
                last_firestore_upload_time = current_time

        else:
            print("Error reading temperature data")

        time.sleep(5)

except KeyboardInterrupt:
    threshold_listener_lower.close()
    threshold_listener_upper.close()
    checkStatus = False
    sensor_off = "Water Temperature Sensor is Off"

    data_realtime_db = {
        "Status": checkStatus,    
    }
    realtime_db.update(data_realtime_db)
    data_firestore_off = {
        "notificationDate": date_time,
        "notificationDescription": sensor_off,
        "notificationTitle": notif_title,
        "notificationTimestamp": form_time,
        "notificationType": notif_type,
        "workgroupId": unique_Id
    }
        
    doc_ref_alert_off = db.collection('notifications').add(data_firestore_off)
    print("\nMeasurement stopped.")
