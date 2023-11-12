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

realtime_db = db.reference('/dht22_temperature_humidity', app=firebase_admin.get_app(name='realtime'))

db = firestore.client(app=firebase_admin.get_app(name='firestore'))

last_firestore_upload_time = time.time()

while True:
    try:
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            temperature = round(temperature, 1)
            humidity = round(humidity, 1)
            
            print("Temperature: {:.1f}C, Humidity: {:.1f}%".format(temperature, humidity))

            if temperature < 35:
                message = "Ambient Temperature"
            elif temperature <= 40:
                message = "Warning Exceeding Ambient Temperature"
            elif temperature <= 50:
                message = "Exceeding Maximum Temperature"
            else:
                message = "Temperature within a safe range"

            print(message)

            # Create a dictionary with the data to send to Firebase
            data_realtime_db = {
                "temperature": temperature,
                "humidity": humidity,
                "status": message
            }
            
            # Send the data to Firebase Realtime Database
            realtime_db.set(data_realtime_db)

            # Get the current time
            current_time = time.time()
            
            if (current_time - last_firestore_upload_time) >= 60:  # Check if 60 seconds have passed
                last_firestore_upload_time = current_time

                # Dictionary with the data to send to Firestore
                data_firestore = {
                    "temperature": temperature,
                    "humidity": humidity,
                    "status": message
                    # Add more data as needed
                }

                doc_ref = db.collection('dht22_temperature_humidity').add(data_firestore)
            
        else:
            print("Sensor failure. Check wiring.")

        time.sleep(3)  # Adjust the sleep interval for DHT22 readings

    except Exception as e:
        print(f"An error occurred: {str(e)}")
