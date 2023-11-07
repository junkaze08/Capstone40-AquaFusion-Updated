# AquaFusion - BSIT 4A - CPSTONE
import time
import pyrebase
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
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

# Initialize the I2C bus and ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Create an analog input channel on the ADS1115 (A0 in this example)
chan = AnalogIn(ads, ADS.P2)

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()
last_realtime_upload_time = time.time()

def read_analog_temperature():
    try:
        # Read analog voltage from the ADS1115
        analog_value = chan.value
        voltage = analog_value * 0.0001875  # 3.3V reference voltage

        # Convert the voltage to temperature
        # Modify this part based on your specific temperature sensor
        temperature = voltage  # Modify this line for your temperature conversion

        return temperature
    except Exception as e:
        print(f"Error reading analog temperature: {e}")
        return None

while True:
    temperature = read_analog_temperature()
    
    # Get the current time
    current_time = time.time()

    if temperature is not None:
        print(f"Temperature: {temperature}°C")

        if (current_time - last_realtime_upload_time) >= 5:  # Upload to Realtime Database every 5 seconds
            data_realtime_db = {"temperature": temperature}
            realtime_db.set(data_realtime_db)
            last_realtime_upload_time = current_time
        
        if (current_time - last_firestore_upload_time) >= 60:  # Upload to Firestore every 60 seconds
            data_firestore = {"temperature": temperature}
            doc_ref = db.collection('Temperature').add(data_firestore)
            last_firestore_upload_time = current_time

    else:
        print("Error reading temperature data")

    time.sleep(5)  # Sleep for 1 second to control the loop rate
