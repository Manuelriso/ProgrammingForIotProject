from MyMQTT import *
import json
import time


class Publisher:
    def __init__(self, clientID, broker, port, topic_publish):
        self.topic_publish = topic_publish
        self.__message = {
            'motion': "on",
        }
        self.client = MyMQTT(clientID, broker, port, None)

    def startSim(self):
        self.client.start()

    def stopSim(self):
        self.client.unsubscribe()
        self.client.stop()

    def publish(self, value):
        message = self.__message
        message['motion'] = "on"
        self.client.myPublish(self.topic_publish, message)
        print("motion sent!")
        # print(f"published Message: {message} \n \n")


if __name__ == "__main__":
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    topic_publish_lM = "greenhouse1/area1/motion"
    light_manager = Publisher("manuel44", broker, port, topic_publish_lM)
    light_manager.startSim()
    time.sleep(2)

    while True:
        light_manager.publish("ciao")
        time.sleep(40)

    light_manager.stopSim()
