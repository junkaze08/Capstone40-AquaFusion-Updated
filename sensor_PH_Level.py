# AquaFusion - BSIT 4A - CPSTONE
import Adafruit_ADS1x15
import time
from collections import deque
import statistics
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

adc = Adafruit_ADS1x15.ADS1115()

RESOLUTION = 65535  # 16-bit
GAIN = 1

b = 0.00
m = 0.167

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()

# Number of measurements for calculating mean and standard deviation
MEASUREMENT_COUNT = 10

# Number of recent pH values to consider in the rolling median filter
ROLLING_MEDIAN_WINDOW = 5

# Lists to store pH values for statistical analysis
pH_values = []
rolling_pH_values = deque(maxlen=ROLLING_MEDIAN_WINDOW)

try:
# Read the pH level and send data to both Realtime Database and Firestore
    while True:
        measurings = 0
        utc_offset = 8

        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        
        for i in range(MEASUREMENT_COUNT):
            # Read ADC channel 1 (A1)
            measurings += adc.read_adc(1, gain=GAIN)
            time.sleep(0.01)

        # Calculate voltage
        voltage = (6.144 / RESOLUTION) * (measurings / MEASUREMENT_COUNT)

        # Calculate pH
        pH_value = 7 + ((2.5 - voltage) / m) + b
        finalpH = round(pH_value - 4.05, 2)

        # Store the pH value in the list
        pH_values.append(finalpH)

        # Keep only the last MEASUREMENT_COUNT values for statistical analysis
        pH_values = pH_values[-MEASUREMENT_COUNT:]

        # Calculate rolling median
        rolling_pH_values.append(finalpH)
        median_pH = statistics.median(rolling_pH_values)

        # Ignore values that deviate significantly from the rolling median
        if abs(finalpH - median_pH) < 0.5:  # Adjust the threshold as needed
            print(f"pH: {finalpH:.2f}")
            print(form_time)
        else:
            print(f"Ignoring outlier pH value: {finalpH:.2f}")
        
        if finalpH >= 0:
            checkStatus = True
            
        # Get the current time
        current_time = time.time()

        # Send data to Realtime Database every 1 second
        data_realtime_db = {
            "Status": checkStatus,
            "ph_level": finalpH
        }
        realtime_db.update(data_realtime_db)

        # Send data to Firestore every 60 seconds
        if (current_time - last_firestore_upload_time) >= 5:  # 60 seconds
            last_firestore_upload_time = current_time
            data_firestore = {
                "ph_level": finalpH,
                "timestamp": form_time,
                "workgroupId": unique_Id            
            }
            doc_ref = db.collection('PH_values').add(data_firestore)

        time.sleep(4)

except KeyboardInterrupt:
    checkStatus = False
    data_realtime_db = {
        "Status": checkStatus,    
    }
    realtime_db.update(data_realtime_db)
    print("\nMeasurement stopped.")
