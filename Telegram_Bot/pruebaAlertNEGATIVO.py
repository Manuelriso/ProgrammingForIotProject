import time
import json
import paho.mqtt.client as mqtt

broker = "mqtt.eclipseprojects.io"
port = 1883
topic = "greenhouse4/area1/motion"

MqttMotion = {
    "bn": topic,
    "e": [{
        "n": "motion",
        "v": 0,
        "t": int(time.time()),
        "u": "boolean"
    }]
}

client = mqtt.Client()
client.connect(broker, port)
client.publish(topic, json.dumps(MqttMotion))
client.disconnect()
print("Mensaje publicado!")
