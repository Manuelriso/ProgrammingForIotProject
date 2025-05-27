import time
import cherrypy
import requests
import random
import json
from CatalogClient import CatalogAPI, Catalog_Navigator
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

def generate_binary():
    """Generate a random binary value (0 or 1)."""
    return random.randint(0, 1)

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
        self._paho_mqtt.publish(topic, json.dumps(msg), 2) # 2 is the qos
    
    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

if __name__ == '__main__':
    c = Catalog_Navigator(settings=json.load(open('settings.json')))
    catalog = c.get_catalog()
    pub = MyMQTT("10", "mqtt.eclipseprojects.io", 1883) #tobe modified according to settings
    pub.start()
    print(f"Catalog: {catalog}")

    while True:
            #get must return the updated value already, without reinitializing the catalog
            # c = Catalog_Navigator(settings=json.load(open('settings.json')))
            catalog = c.get_catalog()
            # debug
            print(f"Catalog: {catalog}, brongioli.")
            for greenhouse in catalog["greenhouses"]: # iterate over greenhouses
                for area in greenhouse["areas"]:
                    # Comment if not using the board (only ID 1)
                    # the indentation must be modified also (''' near before if)

                    # if area["ID"] == "1":
                        #sense temperature
                    #    topicTemp = c.searchByTopic(1, 1, "temperatureDataTopic")
                    #    dictTemp = {
                    #        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area["ID"]}/temperature",
                    #        "e": [{
                    #                "n": "temperature",
                    #                "v": sensor.temperature,
                    #                "t": time.time(),
                    #                "u": "double"
                    #            }]
                    #        }
                    #    area["currentTemperature"] = dictTemp["e"][0]["v"]
                    #    pub.myPublish(topicTemp, dictTemp)
                    #    #sense humidity
                    #    topicHum = c.searchByTopic(1, 1, "humidityDataTopic")
                    #    dictHum = {
                    #        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area["ID"]}/humidity",
                    #        "e": [{
                    #                "n": "humidity",
                    #                "v": sensor.humidity,
                    #                "t": time.time(),
                    #                "u": "percentage"
                    #            }]
                    #        }
                    #    area["currentHumidity"] = dictHum["e"][0]["v"]
                    #    pub.myPublish(topicHum, dictHum) 
                    #else: 
                    topicTemp = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "temperatureDataTopic")
                    print(f"Topic for temperature: {topicTemp}")
                    dictTemp = {
                        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/temperature",
                        "e": [{
                                "n": "temperature",
                                "v": generate_temperature(),
                                "t": time.time(),
                                "u": "double"
                            }]
                    }
                    area["currentTemperature"] = dictTemp["e"][0]["v"]
                    #debug
                    print(f"Temperature for greenhouse{greenhouse['greenhouseID']} and area{area['ID']}: {area['currentTemperature']}")
                    pub.myPublish(topicTemp, dictTemp)
                
                    # sense humidity
                    topicHum = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "humidityDataTopic")
                    dictHum = {
                        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/humidity",
                        "e": [{
                                "n": "humidity",
                                "v": generate_humidity(),
                               "t": time.time(),
                                "u": "percentage"
                            }]
                    }
                    area["currentHumidity"] = dictHum["e"][0]["v"]
                    #debug
                    print(f"Humidity for greenhouse{greenhouse['greenhouseID']} and area{area['ID']}: {area['currentHumidity']}")
                    pub.myPublish(topicHum, dictHum)
                
                    # sense motion
                    topicMotion = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "motionTopic")
                    generalMotion = {
                        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/motion",
                        "e": [{
                               "n": "motion",
                               "v": generate_binary(), # if allerts are a problem, just put zeros here
                               "t": time.time(),
                                "u": "boolean"
                            }]
                    }
                    area["motionDetected"] = generalMotion["e"][0]["v"]
                    #debug
                    print(f"Motion for greenhouse{greenhouse['greenhouseID']} and area{area['ID']}: {area['motionDetected']}")
                    pub.myPublish(topicMotion, generalMotion)
                    
                    # now put request to the catalog
            for greenhouse in catalog["greenhouses"]:
                update = requests.put("http://localhost:8082/greenhouse", data=json.dumps(greenhouse))
                print(f"Update status code: {update.status_code}")
                if update.status_code == 200:
                    print("Catalog updated successfully")
                else:
                    print("Failed to update catalog")
                
            time.sleep(15) #frequency of sensors (due to database update)
