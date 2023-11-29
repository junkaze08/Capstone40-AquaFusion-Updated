# AquaFusion - BSIT 4A - CPSTONE
import time
import pyrebase
import busio
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
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
    'projectId': FIREBASE_CONFIG['projectId'],
}, name='firestore')

# Initialize Realtime Database
realtime_db = db.reference('/PH_values', app=firebase_admin.get_app(name='realtime'))

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

unique_Id = WORKGROUP_ID['uniqueId']

# Initialize the I2C bus and ADS1115 ADC
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Create an analog input channel on the ADS1115 (A0 in this example)
chan = AnalogIn(ads, ADS.P0)

# pH calibration coefficients (replace with your calibration data)
m = 1.0  # Replace with your calibration coefficient
b = 0.0  # Replace with your calibration coefficient

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()

# Function to convert raw ADC value to pH
def convert_to_ph(raw_value):
    # Divide raw value by 1000 to get a decimal value
    voltage = raw_value / 1000  

    # Apply calibration equation
    pH_val = m * voltage + b
    
    # Round to 1 decimal place
    pH = round(pH_val, 1)

    return pH

try:
# Read the pH level and send data to both Realtime Database and Firestore
    while True:
        utc_offset = 8

        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        # Read the raw analog value
        raw_value = chan.value

        # Convert the raw value to pH
        pH = convert_to_ph(raw_value)
        
        if pH >= 0:
            checkStatus = True

        # Print the pH level
        print(f'pH Level: {pH}')
        print(form_time)
        
        # Get the current time
        current_time = time.time()

        # Send data to Realtime Database every 1 second
        data_realtime_db = {
            "Status": checkStatus,
            "ph_level": pH
        }
        realtime_db.update(data_realtime_db)

        # Send data to Firestore every 60 seconds
        if (current_time - last_firestore_upload_time) >= 5:  # 60 seconds
            last_firestore_upload_time = current_time
            data_firestore = {
                "ph_level": pH,
                "timestamp": form_time,
                "workgroupId": unique_Id            
            }
            doc_ref = db.collection('PH_values').add(data_firestore)
        
        # Adjust the delay based on your needs (e.g., how often you want to read the pH value)
        time.sleep(5)

except KeyboardInterrupt:
    checkStatus = False
    data_realtime_db = {
        "Status": checkStatus,    
    }
    realtime_db.update(data_realtime_db)
    print("\nMeasurement stopped.")
