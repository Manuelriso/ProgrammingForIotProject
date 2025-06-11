from gpiozero import MotionSensor
import paho.mqtt.client as PahoMQTT
import requests
import json
import time

# PIR on GPIO17 with longer sampling window
pir = MotionSensor(17, queue_len=5, threshold=0.5)  # more stable detection

class MyMQTT:
    def __init__(self, clientID, broker, port):
        self.broker = broker
        self.port = port
        self.clientID = clientID
        self._isSubscriber = False
        self._paho_mqtt = PahoMQTT.Client(clientID, True)
        self._paho_mqtt.on_connect = self.myOnConnect

    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print(f"Connected to {self.broker} with result code: {rc}")

    def myPublish(self, topic, msg):
        print(f"Motion sent! Topic --> {topic}\nMsg --> {msg}")
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def start(self):
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

if __name__ == '__main__':
    pub = MyMQTT("20", "mqtt.eclipseprojects.io", 1883)
    pub.start()

    settings = json.load(open('settings.json'))

    cooldown_period = 15  # seconds to ignore new motion after a trigger
    last_motion_time = 0

    while True:
        print("Scanning for motion...")
        pir.wait_for_motion()

        current_time = time.time()
        if current_time - last_motion_time > cooldown_period:
            print("Motion detected ✅")
            pub.myPublish("greenhouse1/area1/motion", {"bn":"greenhouse1/area1/motion","e":[{"v": "on", "t":time.time(),"u":"boolean","n":"motion"}]})
            last_motion_time = current_time

            time.sleep(2)  # short delay after detection (non-blocking)
        else:
            print("Motion ignored due to cooldown ⏳")

        pir.wait_for_no_motion()
        print("Motion stopped 🛑")

                
