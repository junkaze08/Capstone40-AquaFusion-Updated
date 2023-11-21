import time
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
realtime_db = db.reference('/tds_values', app=firebase_admin.get_app(name='realtime'))

# Initialize Firestore
db = firestore.client(app=firebase_admin.get_app(name='firestore'))

# Create a variable to track the last time data was sent to Firestore
last_firestore_upload_time = time.time()

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
    tds_value = (133.42 * compensation_voltage**3 - 255.86 * compensation_voltage**2 + 857.39 * compensation_voltage) * 0.5 - 6.0

    # Ensure the result is not less than 0
    tds_value = max(tds_value, 0)

    return tds_value

while True:
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
    

    # Print TDS value (adjusted by subtracting 2, limited to not be less than 0)
    print("TDS Value: {:.2f} ppm".format(ppm))

    # Dictionary with the data to send to Firebase Realtime Database
    data_realtime_db = {
        "ppm": ppm,
        # Add more data as needed
    }

    # Send the data to Firebase Realtime Database
    realtime_db.set(data_realtime_db)

    # Get the current time
    current_time = time.time()

    # Check if an hour has passed since the last Firestore upload
    if (current_time - last_firestore_upload_time) >= 60:  # 60 seconds = 1 minute
        last_firestore_upload_time = current_time

        # Dictionary with the data to send to Firestore
        data_firestore = {
            "ppm": ppm,
            # Add more data as needed
        }

        doc_ref = db.collection('tds_values').add(data_firestore)

    # Wait for the next iteration
    time.sleep(2)
