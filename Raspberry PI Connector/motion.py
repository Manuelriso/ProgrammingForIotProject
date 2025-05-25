# only real time hardware
from gpiozero import MotionSensor
import paho.mqtt.client as PahoMQTT
import requests
import json
import time
from CatalogClient import CatalogAPI, Catalog_Navigator
import board

pir = MotionSensor(17) # out plugged into GPIO17

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
    catalog = c.getCatalog()    
    pub = MyMQTT("20", "mqtt.eclipseprojects.io", 1883) #tobe modified according to settings
    pub.start()

    while True:
        # c = Catalog_Navigator()
        catalog = c.getCatalog()  
        print("Continue scan")
        pir.wait_for_motion() #these functions are blocking
        print("Motion detected") 
        MqttMotion = {
                    "bn": f"greenhouse1/area1/motion",
                    "e": [{
                            "n": "motion",
                            "v": 1,
                            "t": time.time(),
                            "u": "boolean"
                        }]
        }
        catalog["greenhouses"][0]["areas"][0]["motionDetected"] = 1
        pub.myPublish("greenhouse1/area1/motion", MqttMotion)
        #put
        update = requests.put("http://localhost:8082/greenhouse", json=catalog)
        pir.wait_for_no_motion() #these functions are blocking
        print("Motion stopped")
        MqttMotion = {
                    "bn": f"greenhouse1/area1",
                    "e": [{
                            "n": "motion",
                            "v": 0,
                            "t": time.time(),
                            "u": "boolean"
                        }]
        }
        catalog["greenhouses"][0]["areas"][0]["motionDetected"] = 0
        pub.myPublish("greenhouse1/area1/motion", MqttMotion)
        #put
        for greenhouse in catalog["greenhouses"]:
            update = requests.put("http://localhost:8082/greenhouse", data=json.dumps(greenhouse))
            print(f"Update status code: {update.status_code}")
            if update.status_code == 200:
                print("Catalog updated successfully")
            else:
                print("Failed to update catalog")
                
