#Used for luminosity 
import time
import cherrypy
import requests
import random
import json
from CatalogClient import CatalogAPI, Catalog_Navigator
# import board # Uncomment if using a DHT sensor
# import adafruit_dht # Uncomment if using a DHT sensor
import paho.mqtt.client as PahoMQTT

def generate_luminosity(base_humidity=60.0, variation=20.0):
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
    pub = MyMQTT("47", "mqtt.eclipseprojects.io", 1883) #tobe modified according to settings
    pub.start()
    #print(f"Catalog: {catalog}")
    settings = json.load(open('settings.json'))
    catalogURL = settings['catalogURL']
    serviceInfo=settings["serviceInfo"]
    #save service info into CATALOG (post)
    serviceInfo['last_update'] = time.time()
    requests.post(f'{catalogURL}/service', data=json.dumps(serviceInfo))

    while True:
            catalog = c.get_catalog()
            # debug
            #print(f"Catalog: {catalog}, brongioli.")
            for greenhouse in catalog["greenhouses"]: # iterate over greenhouses
                for area in greenhouse["areas"]:
                    # sense luminosity
                    topicLum = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "luminosityDataTopic")
                    dictLum = {
                        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/luminosity",
                        "e": [{
                                "n": "luminosity",
                                "v": generate_luminosity(), # just random percentage value
                                "t": time.time(),
                                "u": "percentage"
                            }]
                    }
                    area["currentLuminosity"] = dictLum["e"][0]["v"] #update json
                    pub.myPublish(topicLum, dictLum) #publish to topic Luminosity
                    print(f"Luminosity publish on {topicLum}--{dictLum}")

                    
                    # now put request to the catalog
            for greenhouse in catalog["greenhouses"]:
                update = requests.put(f"{catalogURL}/greenhouse", data=json.dumps(greenhouse))
                print(f"Update status code: {update.status_code}")
                if update.status_code == 200:
                    print("Catalog updated successfully")
                else:
                    print("Failed to update catalog")
            #save service info into CATALOG (put)
            serviceInfo['last_update'] = time.time()
            requests.put(f'{catalogURL}/service', data=json.dumps(serviceInfo))                  
            time.sleep(16) #frequency of sensors (due to database update)
