# AquaFusion - BSIT 4A - CPSTONE
import Adafruit_ADS1x15
import time
from collections import deque
import statistics
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_PH

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
realtime_db = db.reference(FIREBASE_PH['sensorCollection'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_lower = db.reference(FIREBASE_PH['sensorLower'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper = db.reference(FIREBASE_PH['sensorUpper'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_normal = db.reference(FIREBASE_PH['sensorNormal'], app=firebase_admin.get_app(name='realtime'))

pH_normal = realtime_db_threshold_normal.get()

pH_limits_lower = realtime_db_threshold_lower.get()

pH_limits_upper = realtime_db_threshold_upper.get()

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

def on_threshold_change_lower(event):
    global pH_limits_lower
    if event.data is not None:
        pH_limits_lower = str(event.data)
        print("Threshold lower levels updated:", pH_limits_lower)
    else:
        print("Threshold levels data not available in the database.")
    
def on_threshold_change_upper(event):
    global pH_limits_upper
    if event.data is not None:
        pH_limits_upper = str(event.data)
        print("Threshold upper levels updated:", pH_limits_upper)
    else:
        print("Threshold levels data not available in the database.")

threshold_listener_lower = realtime_db_threshold_lower.listen(on_threshold_change_lower)
threshold_listener_upper = realtime_db_threshold_upper.listen(on_threshold_change_upper)

try:
# Read the pH level and send data to both Realtime Database and Firestore
    while True:
        measurings = 0
        utc_offset = 8

        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        time_period = time.strftime("%Y:%m:%d", curr_time)
        
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
            
        lower_key = FIREBASE_PH['sensorConditionalLower']
        upper_key = FIREBASE_PH['sensorConditionalUpper']
        
        if pH_normal and lower_key in pH_normal and upper_key in pH_normal:
            lower_limit = pH_normal[lower_key]
            upper_limit = pH_normal[upper_key]
            
            if finalpH < lower_limit:
                ph_status = "Warning: Too Low pH Level!" 
            elif lower_limit <= finalpH <= upper_limit:
                ph_status = "Optimal pH Level"
            else:
                ph_status = "Warning: Too High pH Level!"
        
        # Get the current time
        current_time = time.time()
        print(ph_status)

        # Send data to Realtime Database every 1 second
        data_realtime_db = {
            "Status": checkStatus,
            "ph_level": finalpH,
            "status_notif": ph_status
        }
        realtime_db.update(data_realtime_db)

        # Send data to Firestore every 60 seconds
        if (current_time - last_firestore_upload_time) >= 5:  # 60 seconds
            last_firestore_upload_time = current_time
            data_firestore = {
                "ph_level": finalpH,
                "timestamp": form_time,
                "timeperiod": time_period,
                "workgroupId": unique_Id            
            }
            doc_ref = db.collection('PH_values').add(data_firestore)

        time.sleep(4)

except KeyboardInterrupt:
    threshold_listener_lower.close()
    threshold_listener_upper.close()
    checkStatus = False
    data_realtime_db = {
        "Status": checkStatus,    
    }
    realtime_db.update(data_realtime_db)
    print("\nMeasurement stopped.")
