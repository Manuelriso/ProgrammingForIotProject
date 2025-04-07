from MyMQTT import *
import json
import time


class Publisher:
    def __init__(self, clientID, broker, port, topic_publish,topic_publish2):
        self.topic_publish = topic_publish
        self.topic_publish_humidity=topic_publish2
        self.__message = {
            'bn': "boh",
            "e" : [
                {
                    "n":"ciao",
                    "v":0,
                    "t":0,
                    "u":"occhio"
                }
            ]
        }
        self.client = MyMQTT(clientID, broker, port, None)

    def startSim(self):
        self.client.start()

    def stopSim(self):
        self.client.unsubscribe()
        self.client.stop()

    def publish(self, value):
        #{'bn':f'SensorREST_MQTT_{self.deviceID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}
        message = self.__message
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="temperature"
        message['e'][0]['v']=24
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="C"
        self.client.myPublish(self.topic_publish, message)
        print(f"I've sent on {self.topic_publish} the message {message}")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="humidity"
        message['e'][0]['v']=88
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic_publish_humidity, message)
        print(f"I've sent on {self.topic_publish_humidity} the message {message}")
        # print(f"published Message: {message} \n \n")


if __name__ == "__main__":
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    topic_publish_lM = "greenhouse1/area3/temperature"
    topic_publish_humidity="greenhouse3/area3/humidity"
    light_manager = Publisher("manuel44", broker, port, topic_publish_lM,topic_publish_humidity)
    light_manager.startSim()
    time.sleep(2)

    while True:
        light_manager.publish("ciao")
        time.sleep(30)

    light_manager.stopSim()
