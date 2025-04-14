from MyMQTT import *
import json
import time
import random
import requests


class Publisher:
    def __init__(self, clientID, broker, port, topic_publish,topic_publish2,topic_publish_luminosity,topic_motion,topic1,topic2):
        self.topic_publish = topic_publish
        self.topic_publish_humidity=topic_publish2
        self.topic_publish_luminosity=topic_publish_luminosity
        self.topic_motion=topic_motion
        self.topic1=topic1
        self.topic2=topic2
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
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="C"
        self.client.myPublish(self.topic_publish, message)
        print(f"I've sent on {self.topic_publish} the message {message}")

        response=requests.get("https://api.thingspeak.com/channels/2907689/fields/1.json?api_key=CXW8G70Y79I6DODX&results=10")
        temperatureData=response.json()
        field_key = f"field1"
        field_values = [float(feed[field_key]) for feed in temperatureData["feeds"] if feed[field_key] is not None]
        temperatureSum=0
        for value in field_values:
            temperatureSum+=value

        if(len(field_values)!=0):
            temperatureMean=temperatureSum/len(temperatureData["values"])
        else:
            temperatureMean=0
            
        print(f"\n\n\n\n{temperatureMean}\n\n\n\n")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="humidity"
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic_publish_humidity, message)
        print(f"I've sent on {self.topic_publish_humidity} the message {message}")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="luminosity"
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic_publish_luminosity, message)
        print(f"I've sent on {self.topic_publish_luminosity} the message {message}")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="luminosity"
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic_motion, message)
        print(f"I've sent on {self.topic_motion} the message {message}")
        # print(f"published Message: {message} \n \n")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="humidity"
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic1, message)
        print(f"I've sent on {self.topic1} the message {message}")
        # print(f"published Message: {message} \n \n")
        time.sleep(2)
        message['bn'] = "SensorDiMerd"
        message['e'][0]['n']="temperature"
        message['e'][0]['v']=random.randint(0, 100)
        message['e'][0]['t']=time.time()
        message['e'][0]['u']="%"
        self.client.myPublish(self.topic2, message)
        print(f"I've sent on {self.topic2} the message {message}")
        # print(f"published Message: {message} \n \n")


if __name__ == "__main__":
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    topic_publish_lM = "greenhouse1/area1/temperature"
    topic_publish_humidity="greenhouse1/area1/humidity"
    topic_publish_luminosity="greenhouse1/area1/luminosity"
    light_manager = Publisher("manuel44", broker, port, topic_publish_lM,topic_publish_humidity,topic_publish_luminosity,"greenhouse1/area1/motion","greenhouse2/area3/humidity","greenhouse1/area3/temperature")
    light_manager.startSim()
    time.sleep(2)

    while True:
        light_manager.publish("ciao")
        time.sleep(30)

    light_manager.stopSim()
