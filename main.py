# Modified code with moving average filtering applied to sensor and load cell readings

from machine import Pin, I2C, SPI, ADC
import network
import urequests
import ujson
import ssd1306
import time
from mfrc522 import MFRC522
import utime
import dht
from hx711 import HX711

# WiFi credentials
'''
WIFI_SSID = "Anindya"
WIFI_PASSWORD = "FlowerBloom"


WIFI_SSID = "iPhone"
WIFI_PASSWORD = "1234567N"
'''

WIFI_SSID = "DIPRO"
WIFI_PASSWORD = "Diprooo01@"
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 10
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("Failed to connect to Wi-Fi")
                return False
            time.sleep(1)
    print("Connected. IP:", wlan.ifconfig()[0])
    return True

def get_stable_sensor_value(pin, a, b, ignore_count=5, sample_count=10, delay=0.1):
    adc = adc_pins[pin]
    readings = []

    # Ignore first 10 readings
    for _ in range(ignore_count):
        _ = adc.read()
        time.sleep(delay)

    # Collect next 20 readings
    for _ in range(sample_count):
        adc_val = adc.read()
        voltage = adc_val / 4095 * 3.3
        ppm = voltage_to_ppm(voltage, a, b)
        readings.append(ppm)
        time.sleep(delay)

    return sum(readings) / len(readings)

def voltage_to_ppm(voltage, a, b):
    if voltage == 0:
        return 0
    return a * (voltage ** b)

def get_all_mq_ppms(ignore_count=10, sample_count=20, delay=0.1):
    readings = {pin: [] for pin in adc_pins}

    # Ignore unstable initial readings
    for _ in range(ignore_count):
        for pin in adc_pins:
            _ = adc_pins[pin].read()
        time.sleep(delay)

    # Collect stable samples
    for _ in range(sample_count):
        for pin in adc_pins:
            raw = adc_pins[pin].read()
            voltage = raw / 4095 * 3.3
            a, b = sensor_params[pin]["a"], sensor_params[pin]["b"]
            ppm = voltage_to_ppm(voltage, a, b)
            readings[pin].append(ppm)
        time.sleep(delay)

    # Return averaged PPMs
    return {pin: sum(vals) / len(vals) for pin, vals in readings.items()}

def get_stable_weight(ignore_count=10, sample_count=20, delay=0.5):
    # Ignore initial samples
    for _ in range(ignore_count):
        _ = hx.get_units()
        time.sleep(delay)

    readings = []
    for _ in range(sample_count):
        readings.append(hx.get_units())
        time.sleep(delay)

    return sum(readings) / len(readings)


# Call this before using urequests
#connect_to_wifi()


# Google Apps Script Web App URL
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyoZ4LWY3-BmzjhHuClhY-oHJQF7UUQVQbgC919zAotKOKQeHPQmVaP9XywccZxOmZ2/exec"

# UID-to-name mapping
known_users = {
    "CB2CBD4B11": "Anindya",
    "83F35DFCD1": "Nittya",
    "CDE781A4": "Charlie"
}

# Sensor Descriptions
sensors = {
    32: ("MQ-3", "Alcohol"),
    33: ("MQ-4", "Methane"),
    35: ("MQ-135", "Air Quality"),
    36: ("MQ-8", "Hydrogen"),
    34: ("DHT11", "Humidity + Temperature")
}

# Initialize Analog MQ Sensors
adc_pins = {
    32: ADC(Pin(32)),
    33: ADC(Pin(33)),
    35: ADC(Pin(35)),
    36: ADC(Pin(36))
}

fan = Pin(12, Pin.OUT)

for adc in adc_pins.values():
    adc.atten(ADC.ATTN_11DB)
    adc.width(ADC.WIDTH_12BIT)

# Initialize DHT Sensor
dht_sensor = dht.DHT11(Pin(27))

# JSON-aware send_to_google_sheets function
def send_to_google_sheets(data):
    try:
        clean_data = {k: v for k, v in data.items() if v is not None}
        headers = {'Content-Type': 'application/json'}
        res = urequests.post(GOOGLE_SCRIPT_URL, data=ujson.dumps(clean_data), headers=headers)
        #print("Sheet Response:", res.text)
        return res.status_code == 200
    except Exception as e:
        #print("Send error:", str(e))
        return False

# Conversion Function
def voltage_to_ppm(voltage, a, b):
    if voltage == 0:
        return 0
    return a * (voltage ** b)

# Sensor Parameters
sensor_params = {
    32: {"a": 21, "b": 1.59},
    33: {"a": 35.89, "b": 2.83},
    35: {"a": 5, "b": 2.5},
    36: {"a": 0.3, "b": 2.25}
}

# OLED Display
i2c = I2C(1, scl=Pin(26), sda=Pin(14))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# RFID SPI
spi = SPI(1, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(23), miso=Pin(19))
rdr = MFRC522(spi=spi, cs=Pin(21), rst=Pin(22))

# Button
button = Pin(25, Pin.IN, Pin.PULL_UP)

def show_text(line1="", line2="", line3=""):
    oled.fill(0)
    oled.text(line1, 0, 0)
    oled.text(line2, 0, 10)
    oled.text(line3, 0, 20)
    oled.show()
    
    

# Load Cell
hx = HX711(dout=Pin(4), pd_sck=Pin(5))

time.sleep(2)
print("Taring... Remove any weight.")
show_text("Taring... Remove", "any weight.")
time.sleep(3)
hx.tare()
print("Tare done.")
show_text("Tare done.")
time.sleep(1)

# Calibration
known_weight = 2.1  # kg
known_weight_str = "weight of" + str(round(known_weight, 1)) + " kg"
print("Place a known weight of", known_weight, "kg on the sensor.")
show_text("Place a known", known_weight_str)
time.sleep(5)

reading = hx.get_value()
scale = reading / known_weight
hx.set_scale(scale)

print("Calibration done.")
show_text("Calibration done.")
time.sleep(1)

id_init = 0
valid_id = 0
yield_init = 0

# Main Loop
while True:
    alcohol_ppm = None
    methane_ppm = None
    air_quality_ppm = None
    hydrogen_ppm = None
    temperature_celsius = None
    humidity_percent = None
    uid = None
    weight = 0
    weight1 = None
    _name = None
    Quality = None
    timeout = 7
    start_time = utime.time()
    

    if id_init == 0:
        show_text("Scan your", "RFID")
    time.sleep(2)
    while utime.time() - start_time < timeout:
        (stat, _) = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            (stat, raw_uid) = rdr.anticoll()
            if stat == rdr.OK:
                uid = "".join("{:02X}".format(i) for i in raw_uid)
                break
        #print(utime.time())
        utime.sleep(0.1)
        uid = "CB2CBD4B11"
        

    if uid in known_users:
        valid_id = 1
        _name = known_users[uid]
        show_text("Welcome", _name)
        id_init = 1
    elif uid == None:
        show_text("Place your card", "properly")
        utime.sleep(0.5)
    else:
        show_text("Undefined User")
        valid_id = 0
        id_init = 0
        utime.sleep(2)

    time.sleep(2)

    if valid_id:
        show_text("Place your", "yield")
        while yield_init == 0:
            yield_init = not button.value()
            time.sleep(0.1)

        #weight = hx.get_units()
        weight = 3.087
        ppm_results = get_all_mq_ppms()
        alcohol_ppm = ppm_results[32]
        methane_ppm = ppm_results[33]
        air_quality_ppm = ppm_results[35]
        hydrogen_ppm = ppm_results[36]

        for pin, (name, gas_type) in sensors.items():
            if pin in adc_pins:
                '''
                #params = sensor_params[pin]
                #ppm = get_stable_sensor_value(pin, params["a"], params["b"])

                if pin == 32:
                    alcohol_ppm = ppm
                elif pin == 33:
                    methane_ppm = ppm
                elif pin == 35:
                    air_quality_ppm = ppm
                elif pin == 36:
                    hydrogen_ppm = ppm
            '''
            elif pin == 34:
                try:
                    dht_sensor.measure()
                    temperature_celsius = dht_sensor.temperature()
                    humidity_percent = dht_sensor.humidity()
                except:
                    temperature_celsius = None
                    humidity_percent = None
        
        thr_methane = 55
        thr_alcohol = 0.4
        thr_hydrogen = 1
        thr_ammonia = 0.4
        thr_humid_min = 85
        thr_humid_max = 90
        thr_temp_min = 0
        thr_temp_max = 15
        
        q_methane = max(1 - methane_ppm/(weight*thr_methane), 0)
        q_alcohol = max(1 - alcohol_ppm/(weight*thr_alcohol), 0)
        q_hydrogen = max(1 - hydrogen_ppm/(weight*thr_hydrogen), 0)
        q_ammonia = max(1 - air_quality_ppm/(weight*thr_ammonia), 0)
        
        if temperature_celsius < 0:
                        q_temp = max(1 + temperature_celsius/15 , 0)
        elif temperature_celsius > 15:
                         q_temp = max(1 - (temperature_celsius - thr_temp_max)/15 , 0)
        else:
                         q_temp = 1
                         
        if humidity_percent < 85:
                         q_humid = max(1 - (thr_humid_min - humidity_percent)/5 , 0)
        elif humidity_percent > 90:
                         q_humid = max(1 - (humidity_percent - thr_temp_max)/5 , 0)
        else:
                         q_humid = 1
        
        Quality = (2 * q_alcohol + 2 * q_methane + 4 * q_ammonia + 2 * q_hydrogen + q_temp + q_humid)*100/12 
        
        alcohol_str = "Alcohol: " + (str(round(alcohol_ppm, 1)) + "ppm" if alcohol_ppm is not None else "N/A")
        methane_str = "Methane: " + (str(round(methane_ppm, 1)) + "ppm" if methane_ppm is not None else "N/A")
        air_str = "Air Q: " + (str(round(air_quality_ppm, 1)) + "ppm" if air_quality_ppm is not None else "N/A")
        hydrogen_str = "Hydrogen:" + (str(round(hydrogen_ppm, 1)) + "ppm" if hydrogen_ppm is not None else "N/A")
        temp_str = "Temp: " + (str(round(temperature_celsius, 1)) + "C" if temperature_celsius is not None else "N/A")
        hum_str = "Humidity: " + (str(round(humidity_percent, 1)) + "%" if humidity_percent is not None else "N/A")
        weight_str = "Weight: " + (str(round(weight, 2)) + "kg" if weight is not None else "N/A")
        quality_str = "Quality: " + (str(round(Quality, 2)) + "%" if Quality is not None else "N/A")
                         
        print(alcohol_str)               
        print(hum_str)
        print(weight_str)
        print(quality_str)
                         
        oled.fill(0)
        oled.text(alcohol_str, 0, 0)
        oled.text(methane_str, 0, 10)
        oled.text(air_str, 0, 20)
        oled.text(quality_str, 0, 30)
        oled.text(weight_str, 0, 40)
        oled.show()

        data = {
            "user_name": _name,
            "temperature": temperature_celsius,
            "humidity": humidity_percent,
            "load_cell": weight,
            "nh3_sensor": air_quality_ppm,
            "h2_sensor": hydrogen_ppm,
            "ch4_sensor": methane_ppm,
            "alcohol_sensor": alcohol_ppm
        }

        send_to_google_sheets(data)
        time.sleep(15)
        show_text("Offload your", "yield")
        time.sleep(2)
        while yield_init:
            weight1 = hx.get_units()
            if weight1 < 0.01:
                fan.on()
                time.sleep(3)
                fan.off()
                yield_init = 0

    id_init = 0
    valid_id = 0
