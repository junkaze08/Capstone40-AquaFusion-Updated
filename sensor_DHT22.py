# AquaFusion - BSIT 4A - CPSTONE
import Adafruit_DHT
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 26

cred = credentials.Certificate(FIREBASE_CONFIG['serviceAccountKeyPath'])
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_CONFIG['databaseURL']
}, name='realtime')

cred_firestore = credentials.Certificate(FIREBASE_CONFIG['serviceAccountKeyPath'])
firebase_admin.initialize_app(cred_firestore, {
    'projectId': FIREBASE_CONFIG['projectId'],
}, name='firestore')

realtime_db_humidity = db.reference('/dht22_temperature_humidity', app=firebase_admin.get_app(name='realtime'))

realtime_db_temperature = db.reference('/dht22_temperature_temperature', app=firebase_admin.get_app(name='realtime'))

db = firestore.client(app=firebase_admin.get_app(name='firestore'))

unique_Id = WORKGROUP_ID['uniqueId']

# Reference to the Firestore collection for humidity
humidity_collection = db.collection('DHT22_Humidity')

# Reference to the Firestore collection for temperature
temperature_collection = db.collection('DHT22_Temperature')

# Time tracking variables
last_firestore_upload_time = 0

try:
    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        try:
            humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
            if humidity is not None and temperature is not None:
                temperature = round(temperature, 1)
                humidity = round(humidity, 1)

                print("Temperature: {:.1f}C, Humidity: {:.1f}%".format(temperature, humidity))

                if temperature >= 0:
                    checkStatus = True
                
                if temperature < 18:
                    temperature_status = "Warning: Cold Temperature"
                elif 18 <= temperature <= 24:
                    temperature_status = "Optimal Temperature"
                else:
                    temperature_status = "Warning: Hot Temperature"
                    
                if humidity < 60:
                    humidity_status = "Warning: Too Low Humidity"
                elif 60 <= humidity <= 70:
                    humidity_status = "Optimal Humidity"
                else:
                    humidity_status = "Warning: Too High Humidity"

                print(temperature_status)
                print(humidity_status)
                print(form_time)

                # Single dictionary for Realtime Database
                data_realtime_db_humidity = {
                    "Status": checkStatus,
                    "humidity": humidity,
                    "status_notif_dht_humid": humidity_status
                }
                
                data_realtime_db_temperature = {
                    "Status": checkStatus,
                    "temperature": temperature,
                    "status_notif_dht_temp": temperature_status
                }

                # Separate dictionaries for Firestore
                data_firestore_temperature = {
                    "temperature": temperature,
                    "timestamp": form_time,
                    "workgroupId": unique_Id
                }

                data_firestore_humidity = {
                    "humidity": humidity,
                    "timestamp": form_time,
                    "workgroupId": unique_Id
                }

                # Send data to Realtime Database
                realtime_db_humidity.update(data_realtime_db_humidity)
                realtime_db_temperature.update(data_realtime_db_temperature)

                # Get the current time
                current_time = time.time()

                if (current_time - last_firestore_upload_time) >= 5:  # Check if 60 seconds have passed
                    last_firestore_upload_time = current_time

                    # Send data to Firestore collections
                    doc_ref_temperature = temperature_collection.add(data_firestore_temperature)
                    doc_ref_humidity = humidity_collection.add(data_firestore_humidity)

            else:
                print("Sensor failure. Check wiring.")

            time.sleep(5)  # Adjust the sleep interval for DHT22 readings

        except Exception as e:
            print(f"An error occurred: {str(e)}")

except KeyboardInterrupt:
    checkStatus = False
    data_realtime_db_humidity = {
        "Status": checkStatus,    
    }
    data_realtime_db_temperature = {
        "Status": checkStatus,
    }
    realtime_db_humidity.update(data_realtime_db_humidity)
    realtime_db_temperature.update(data_realtime_db_temperature)
    print("\nMeasurement stopped.")
