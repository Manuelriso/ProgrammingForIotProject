import time
import cherrypy
import requests
import random
import json
#from CatalogClient import CatalogAPI, Catalog_Navigator
# import board # Uncomment if using a DHT sensor
# import adafruit_dht # Uncomment if using a DHT sensor
import paho.mqtt.client as PahoMQTT

# sensor = adafruit_dht.DHT11(board.D4) # Uncomment if using a DHT sensor

def generate_temperature(base_temp=20.0, variation=8.0):
    """Simulate a temperature value around a base temperature."""
    return round(random.uniform(base_temp - variation, base_temp + variation), 1)

def generate_humidity(base_humidity=60.0, variation=10.0):
    """Simulate a humidity value around a base percentage."""
    return round(random.uniform(base_humidity - variation, base_humidity + variation), 1)

class MyMQTT:
    def __init__(self, clientID, broker, port):
        self.broker = broker
        self.port = port
        self.clientID = clientID
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID, True)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
    
    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d" % (self.broker, rc))
    
    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        print(f"topic-->{topic} and msg-->{msg}")
        self._paho_mqtt.publish(topic, json.dumps(msg), 2) # 2 is the qos
    
    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

if __name__ == '__main__':
    #c = Catalog_Navigator(settings=json.load(open('settings.json')))
    #catalog = c.get_catalog()
    pub = MyMQTT("10", "mqtt.eclipseprojects.io", 1883) #tobe modified according to settings
    #save service info into CATALOG (post)
    settings = json.load(open('settings.json'))
    catalogURL=settings["catalogURL"]
    serviceInfo=settings["serviceInfo"]
    serviceInfo['last_update'] = time.time()
    #requests.post(f'{catalogURL}/service', data=json.dumps(serviceInfo))
    pub.start()
    #print(f"Catalog: {catalog}")

    while True:
        topicTemp="greenhouse1/area1/temperature"
        dictTemp = {
            "bn": f"greenhouse1/area1/temperature",
            "e": [{
                "n": "temperature",
                "v": sensor.temperature,
                "t": time.time(),
                "u": "double"
             }]
        }
        pub.myPublish(topicTemp, dictTemp)
        #sense humidity
        dictHum = {
            "bn": f"greenhouse1/area1/humidity",
            "e": [{
                "n": "humidity",
                "v": sensor.humidity,
                "t": time.time(),
                "u": "percentage"
            }]
        }
        topicHum="greenhouse1/area1/humidity"
        pub.myPublish(topicHum, dictHum) 
                                
        time.sleep(15) #frequency of sensors (due to database update)
