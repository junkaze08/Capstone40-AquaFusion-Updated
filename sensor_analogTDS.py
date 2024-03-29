# AquaFusion - BSIT 4A - CPSTONE
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_TDS

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
realtime_db = db.reference(FIREBASE_TDS['sensorCollection'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_lower = db.reference(FIREBASE_TDS['sensorLower'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper = db.reference(FIREBASE_TDS['sensorUpper'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_normal = db.reference(FIREBASE_TDS['sensorNormal'], app=firebase_admin.get_app(name='realtime'))

tds_normal = realtime_db_threshold_normal.get()

tds_limits_lower = realtime_db_threshold_lower.get()

tds_limits_upper = realtime_db_threshold_upper.get()

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()

unique_Id = WORKGROUP_ID['uniqueId']

TdsSensorPin = 0  # A0 on ADS1115
VREF = 5.0  # Analog reference voltage (Volt) of the ADC
SCOUNT = 30  # Sum of sample points

analogBuffer = [0] * SCOUNT
analogBufferIndex = 0

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

def create_ads_object():
    return ADS.ADS1115(i2c)

# Create the initial ADC object
ads = create_ads_object()

# Create single-ended input on channel 0
chan = AnalogIn(ads, ADS.P0)

def get_median_value(bArray):
    bTab = sorted(bArray)
    iFilterLen = len(bArray)

    if iFilterLen % 2 == 1:
        bTemp = bTab[(iFilterLen - 1) // 2]
    else:
        bTemp = (bTab[iFilterLen // 2] + bTab[iFilterLen // 2 - 1]) / 2

    return bTemp

def calculate_tds(voltage):
    temperature = 25.0
    compensation_coefficient = 1.0 + 0.02 * (temperature - 25.0)
    compensation_voltage = voltage / compensation_coefficient
    tds_value = (133.42 * compensation_voltage**3 - 255.86 * compensation_voltage**2 + 857.39 * compensation_voltage) * 0.5 - 12.0

    # Ensure the result is not less than 0
    tds_value = max(tds_value, 0)

    return tds_value

def on_threshold_change_lower(event):
    global tds_limits_lower
    if event.data is not None:
        tds_limits_lower = str(event.data)
        print("Threshold lower levels updated:", tds_limits_lower)
    else:
        print("Threshold levels data not available in the database.")
    
def on_threshold_change_upper(event):
    global tds_limits_upper
    if event.data is not None:
        tds_limits_upper = str(event.data)
        print("Threshold upper levels updated:", tds_limits_upper)
    else:
        print("Threshold levels data not available in the database.")

threshold_listener_lower = realtime_db_threshold_lower.listen(on_threshold_change_lower)
threshold_listener_upper = realtime_db_threshold_upper.listen(on_threshold_change_upper)

try:
    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        time_period = time.strftime("%Y:%m:%d", curr_time)

        # Read analog value from ADS1115
        analogBuffer[analogBufferIndex] = chan.value
        analogBufferIndex += 1

        if analogBufferIndex == SCOUNT:
            analogBufferIndex = 0

        # Check if TDS value is 0.00 and reset the ADC
        if get_median_value(analogBuffer) == 0.00:
            ads = create_ads_object()  # Create a new ADC object
            time.sleep(0.1)  # Wait for ADC to reset
            continue  # Skip the rest of the loop iteration

        # Wait for a short time to avoid rapid readings
        time.sleep(0.2)

        # Calculate TDS value
        average_value = get_median_value(analogBuffer)
        scaled_value = average_value * (VREF / 32767.0)
        ppmRound = calculate_tds (scaled_value)
        ppm = round(ppmRound, 2)
        
        if ppm >= 0:
            checkStatus = True
        
        lower_key = FIREBASE_TDS['sensorConditionalLower']
        upper_key = FIREBASE_TDS['sensorConditionalUpper']
        
        if tds_normal and lower_key in tds_normal and upper_key in tds_normal:
            lower_limit = tds_normal[lower_key]
            upper_limit = tds_normal[upper_key]
            
            if ppm < lower_limit:
                status_notif = "Warning: TDS level is low!" 
            elif lower_limit <= ppm <= upper_limit:
                status_notif = "TDS level is optimal!"
            else:
                status_notif = "Warning: TDS level is too high!"
        
        # Print TDS value (adjusted by subtracting 2, limited to not be less than 0)
        print("TDS Value: {:.2f} ppm".format(ppm))
        print(status_notif)
        print(form_time)

        # Dictionary with the data to send to Firebase Realtime Database
        data_realtime_db = {
            "Status": checkStatus,
            "ppm": ppm,
            "status_notif": status_notif
            # Add more data as needed
        }

        # Send the data to Firebase Realtime Database
        realtime_db.update(data_realtime_db)

        # Get the current time
        current_time = time.time()

        # Check if an hour has passed since the last Firestore upload
        if (current_time - last_firestore_upload_time) >= 5:  # 60 seconds = 1 minute
            last_firestore_upload_time = current_time

            # Dictionary with the data to send to Firestore
            data_firestore = {
                "ppm": ppm,
                "timestamp": form_time,
                "timeperiod": time_period,
                "workgroupId": unique_Id
                # Add more data as needed
            }

            doc_ref = db.collection('tds_values').add(data_firestore)

        # Wait for the next iteration
        time.sleep(2)

except KeyboardInterrupt:
    threshold_listener_lower.close()
    threshold_listener_upper.close()
    checkStatus = False
    data_realtime_db = {
        "Status": checkStatus,    
    }
    realtime_db.update(data_realtime_db)
    print("\nMeasurement stopped.")