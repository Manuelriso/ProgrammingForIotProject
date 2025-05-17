import paho.mqtt.client as PahoMQTT
import json

class MyMQTT:
    def __init__(self, broker, port, client_id, notifier):
        self.broker=broker
        self.port=port
        self.client_id=client_id
        self.notifier=notifier
        self._issubscriber=False
        self._paho_mqtt=PahoMQTT.Client(self.client_id, True)
        self._paho_mqtt.on_connect=self.myOnConnect
        self._paho_mqtt.on_message=self.myOnMessageRecieved

    def myOnConnect(self, paho_mqtt,user_data, flags, rc ):
        print("connected to %s with rc: %d" % (self.broker, rc))

    def myOnMessageRecieved(self, paho_mqtt, user_data, msg):
        self.notifier.notify(msg.topic, msg.payload)

    def mypublish (self, topic,msg):
        self._paho_mqtt.publish(topic, json.loads(msg))

    def mysubscribe(self, topic):
        self._issubscriber= True
        self.topic=topic
        self._paho_mqtt.subscribe(topic, 2)

    def start(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def unsubscribe(self):
        if(self._issubscriber):
            self._paho_mqtt.unsubscribe(self.topic)
    
    def stop(self):
        if (self._issubscriber):
            self._paho_mqtt.unsubscribe(self.topic)
        
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
