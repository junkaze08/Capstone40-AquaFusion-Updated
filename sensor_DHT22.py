# AquaFusion - BSIT 4A - CPSTONE
import Adafruit_DHT
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG, WORKGROUP_ID, FIREBASE_DHT

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

realtime_db_humidity = db.reference(FIREBASE_DHT['sensorCollectionHumidity'], app=firebase_admin.get_app(name='realtime'))
realtime_db_temperature = db.reference(FIREBASE_DHT['sensorCollectionTemperature'], app=firebase_admin.get_app(name='realtime'))

realtime_db_threshold_upper_humidity = db.reference(FIREBASE_DHT['sensorUpperHumidity'], app=firebase_admin.get_app(name='realtime'))
dht_limits_upper_humidity = realtime_db_threshold_upper_humidity.get()
realtime_db_threshold_lower_humidity = db.reference(FIREBASE_DHT['sensorLowerHumidity'], app=firebase_admin.get_app(name='realtime'))
dht_limits_lower_humidity = realtime_db_threshold_lower_humidity.get()

realtime_db_threshold_upper_temperature = db.reference(FIREBASE_DHT['sensorUpperTemperature'], app=firebase_admin.get_app(name='realtime'))
dht_limits_upper_temperature = realtime_db_threshold_upper_temperature.get()
realtime_db_threshold_lower_temperature = db.reference(FIREBASE_DHT['sensorLowerTemperature'], app=firebase_admin.get_app(name='realtime'))
dht_limits_lower_temperature = realtime_db_threshold_lower_temperature.get()

realtime_db_threshold_normal_humidity = db.reference(FIREBASE_DHT['sensorNormalHumidity'], app=firebase_admin.get_app(name='realtime'))
dht_normal_humidity = realtime_db_threshold_normal_humidity.get()

realtime_db_threshold_normal_temperature = db.reference(FIREBASE_DHT['sensorNormalTemperature'], app=firebase_admin.get_app(name='realtime'))
dht_normal_temperature = realtime_db_threshold_normal_temperature.get()

db = firestore.client(app=firebase_admin.get_app(name='firestore'))

# Reference to the Firestore collection for humidity
humidity_collection = db.collection('DHT22_Humidity')

# Reference to the Firestore collection for temperature
temperature_collection = db.collection('DHT22_Temperature')

unique_Id = WORKGROUP_ID['uniqueId']

# Time tracking variables
last_firestore_upload_time = 0

def on_threshold_change_upper_humidity(event):
    global dht_limits_upper_humidity
    if event.data is not None:
        dht_limits_upper_humidity = str(event.data)
        print("Threshold upper levels humidity updated:", dht_limits_upper_humidity)
    else:
        print("Threshold levels data not available in the database.")
        
def on_threshold_change_lower_humidity(event):
    global dht_limits_lower_humidity
    if event.data is not None:
        dht_limits_lower_humidity = str(event.data)
        print("Threshold lower levels humidity updated:", dht_limits_lower_humidity)
    else:
        print("Threshold levels data not available in the database.")
        
def on_threshold_change_upper_temperature(event):
    global dht_limits_upper_temperature
    if event.data is not None:
        dht_limits_upper_temperature = str(event.data)
        print("Threshold upper levels temperature updated:", dht_limits_upper_temperature)
    else:
        print("Threshold levels data not available in the database.")

def on_threshold_change_lower_temperature(event):
    global dht_limits_lower_temperature
    if event.data is not None:
        dht_limits_lower_temperature = str(event.data)
        print("Threshold lower levels temperature updated:", dht_limits_lower_temperature)
    else:
        print("Threshold levels data not available in the database.")

threshold_listener_lower_temperature = realtime_db_threshold_lower_temperature.listen(on_threshold_change_upper_temperature)
threshold_listener_upper_temperature = realtime_db_threshold_upper_temperature.listen(on_threshold_change_lower_temperature)
threshold_listener_lower_humidity = realtime_db_threshold_lower_humidity.listen(on_threshold_change_upper_humidity)
threshold_listener_upper_humidity = realtime_db_threshold_upper_humidity.listen(on_threshold_change_lower_humidity)

try:
    while True:
        utc_offset = 8
        curr_time = time.gmtime(time.time() + utc_offset * 3600)
        form_time = time.strftime("%H:%M:%S", curr_time)
        time_period = time.strftime("%Y:%m:%d", curr_time)
        try:
            humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
            if humidity is not None and temperature is not None:
                temperature = round(temperature, 1)
                humidity = round(humidity, 1)

                print("Temperature: {:.1f}C, Humidity: {:.1f}%".format(temperature, humidity))

                if temperature >= 0:
                    checkStatus = True
                
                lower_key_humidity = FIREBASE_DHT['sensorConditionalLowerHumidity']
                upper_key_humidity = FIREBASE_DHT['sensorConditionalUpperHumidity']
                lower_key_temperature = FIREBASE_DHT['sensorConditionalLowerTemperature']
                upper_key_temperature = FIREBASE_DHT['sensorConditionalUpperTemperature']
                
                if dht_normal_temperature and lower_key_temperature in dht_normal_temperature and upper_key_temperature in dht_normal_temperature:
                    lower_limit_temperature = dht_normal_temperature[lower_key_temperature]
                    upper_limit_temperature = dht_normal_temperature[upper_key_temperature]
                    
                    if temperature < lower_limit_temperature:
                        temperature_status = "Warning: Cold Temperature"
                    elif lower_limit_temperature <= temperature <= upper_limit_temperature:
                        temperature_status = "Optimal Temperature"
                    else:
                        temperature_status = "Warning: Hot Temperature"
                
                if dht_normal_humidity and lower_key_humidity in dht_normal_humidity and lower_key_humidity in dht_normal_humidity:
                    lower_limit_humidity = dht_normal_humidity[lower_key_humidity]
                    upper_limit_humidity = dht_normal_humidity[upper_key_humidity]
                        
                    if humidity < lower_limit_humidity:
                        humidity_status = "Warning: Too Low Humidity"
                    elif lower_limit_humidity <= humidity <= upper_limit_humidity:
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
                    "timeperiod": time_period,
                    "workgroupId": unique_Id
                }

                data_firestore_humidity = {
                    "humidity": humidity,
                    "timestamp": form_time,
                    "timeperiod": time_period,
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
    threshold_listener_lower_temperature.close()
    threshold_listener_upper_temperature.close()
    threshold_listener_lower_humidity.close()
    threshold_listener_upper_humidity.close()
        
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
