from gpiozero import MotionSensor
import paho.mqtt.client as PahoMQTT
import json
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

if '__name__' == '__main__':
    c = Catalog_Navigator()
    catalog = c.getCatalog()    
    pub = MyMQTT(20, "mqtt.eclipseprojects.io", 1883)
    pub.start()

    while True:
        print("Continue scan")
        pir.wait_for_motion()
        print("Motion detected") 
        dictMotion = 1
        catalog["greenhouses"][0]["areas"][0]["motionDetected"] = dictMotion
        pub.myPublish("greenhouse1/area1/motion", dictMotion)
        pir.wait_for_no_motion()
        print("Motion stopped")
        dictMotion = 0
        catalog["greenhouses"][0]["areas"][0]["motionDetected"] = dictMotion
        pub.myPublish("greenhouse1/area1/motion", dictMotion)