# AquaFusion - BSIT 4A - CPSTONE
import Adafruit_DHT
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG

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

# Reference to the Firestore collection for humidity
humidity_collection = db.collection('DHT22_Humidity')

# Reference to the Firestore collection for temperature
temperature_collection = db.collection('DHT22_Temperature')

# Time tracking variables
last_firestore_upload_time = 0

while True:
    try:
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            temperature = round(temperature, 1)
            humidity = round(humidity, 1)

            print("Temperature: {:.1f}C, Humidity: {:.1f}%".format(temperature, humidity))

            if temperature < 35:
                temperature_status = "Ambient Temperature"
            elif temperature <= 40:
                temperature_status = "Warning Exceeding Ambient Temperature"
            elif temperature <= 50:
                temperature_status = "Exceeding Maximum Temperature"
            else:
                temperature_status = "Temperature within a safe range"

            print(temperature_status)

            # Single dictionary for Realtime Database
            data_realtime_db_humidity = {
                "humidity": humidity
            }
            
            data_realtime_db_temperature = {
                "temperature": temperature,
                "status": temperature_status
            }

            # Separate dictionaries for Firestore
            data_firestore_temperature = {
                "temperature": temperature,
                "status": temperature_status
            }

            data_firestore_humidity = {
                "humidity": humidity
            }

            # Send data to Realtime Database
            realtime_db_humidity.set(data_realtime_db_humidity)
            realtime_db_temperature.set(data_realtime_db_temperature)

            # Get the current time
            current_time = time.time()

            if (current_time - last_firestore_upload_time) >= 5:  # Check if 60 seconds have passed
                last_firestore_upload_time = current_time

                # Send data to Firestore collections
                doc_ref_temperature = temperature_collection.add(data_firestore_temperature)
                doc_ref_humidity = humidity_collection.add(data_firestore_humidity)

        else:
            print("Sensor failure. Check wiring.")

        time.sleep(3)  # Adjust the sleep interval for DHT22 readings

    except Exception as e:
        print(f"An error occurred: {str(e)}")
