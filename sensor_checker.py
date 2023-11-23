from gpiozero import DigitalInputDevice
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Mode
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, firestore
from config import FIREBASE_CONFIG

cred = credentials.Certificate(FIREBASE_CONFIG['serviceAccountKeyPath'])
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_CONFIG['databaseURL']
}, name='realtime')

realtime_db_humidity = db.reference('/dht22_temperature_humidity', app=firebase_admin.get_app(name='realtime'))
realtime_db_temperature = db.reference('/dht22_temperature_temperature', app=firebase_admin.get_app(name='realtime'))
realtime_db_ds18b20 = db.reference('/DS18B20_water_temperature', app=firebase_admin.get_app(name='realtime'))
realtime_db_plant = db.reference('/ultrasonic_plant', app=firebase_admin.get_app(name='realtime'))
realtime_db_water = db.reference('/ultrasonic_water', app=firebase_admin.get_app(name='realtime'))
realtime_db_TDS = db.reference('/tds_values', app=firebase_admin.get_app(name='realtime'))

sensor_DHT = 26
sensor_Plant = 27
sensor_Water = 23
sensor_Temperature = 6

sensor_TDS = 0x48

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    adc = ADS.ADS1115(i2c, address=sensor_TDS)
    adc.mode = Mode.CONTINUOUS

    sensors = {
        "DHT Sensor": DigitalInputDevice(sensor_DHT),
        "Plant Sensor": DigitalInputDevice(sensor_Plant),
        "Water Sensor": DigitalInputDevice(sensor_Water),
        "DS18B20 Sensor": DigitalInputDevice(sensor_Temperature),
        "TDS Sensor": adc
    }

    prev_status = {
        "DHT Sensor": None,
        "Plant Sensor": None,
        "Water Sensor": None,
        "DS18B20 Sensor": None,
        "TDS Sensor": None
    }

    while True:
        for sensor_name, sensor_obj in sensors.items():
            if isinstance(sensor_obj, DigitalInputDevice):
                if sensor_obj.is_active:
                    print(f"{sensor_name} is ON")
                else:
                    print(f"{sensor_name} is OFF")

                # Update the database only if the status has changed
                if sensor_obj.is_active != prev_status[sensor_name]:
                    data_realtime_db = {
                        "Status": sensor_obj.is_active
                    }
                    # Update the database under the specific sensor
                    if sensor_name == "DHT Sensor":
                        realtime_db_humidity.update(data_realtime_db)
                        realtime_db_temperature.update(data_realtime_db)
                    elif sensor_name == "DS18B20 Sensor":
                        realtime_db_ds18b20.update(data_realtime_db)
                    elif sensor_name == "Plant Sensor":
                        realtime_db_plant.update(data_realtime_db)
                    elif sensor_name == "Water Sensor":
                        realtime_db_water.update(data_realtime_db)
                    
                prev_status[sensor_name] = sensor_obj.is_active  # Update prev_status

            elif isinstance(sensor_obj, ADS.ADS1115):
                try:
                    # Attempt to read a value from the ADC channel to check if the sensor is connected
                    sensor_value = AnalogIn(adc, 0).voltage
                    print(f"{sensor_name} is ON")
                    sensor_connected = True
                    
                except Exception as e:
                    print(f"{sensor_name} is OFF (Error: {e})")
                    sensor_connected = False

                # Update the database only if the connection status has changed
                if sensor_connected != prev_status[sensor_name]:
                    data_realtime_db = {
                        "Status": sensor_connected,
                    }

                    if sensor_name == "TDS Sensor":
                        realtime_db_TDS.update(data_realtime_db)

                prev_status[sensor_name] = sensor_connected

        time.sleep(10)

except KeyboardInterrupt:
    try:
        # Set all sensor statuses to OFF or False before exiting
        for sensor_name, sensor_obj in sensors.items():
            if isinstance(sensor_obj, DigitalInputDevice):
                data_realtime_db = {
                    "Status": False
                }
                # Update the database under the specific sensor
                if sensor_name == "DHT Sensor":
                    realtime_db_humidity.update(data_realtime_db)
                    realtime_db_temperature.update(data_realtime_db)
                elif sensor_name == "DS18B20 Sensor":
                    realtime_db_ds18b20.update(data_realtime_db)
                elif sensor_name == "Plant Sensor":
                    realtime_db_plant.update(data_realtime_db)
                elif sensor_name == "Water Sensor":
                    realtime_db_water.update(data_realtime_db)

            elif isinstance(sensor_obj, ADS.ADS1115):
                data_realtime_db = {
                    "Status": False,
                }
                if sensor_name == "TDS Sensor":
                    realtime_db_TDS.update(data_realtime_db)

    except Exception as e:
        print(f"Error during cleanup: {e}")

    print("Program terminated by user.")
