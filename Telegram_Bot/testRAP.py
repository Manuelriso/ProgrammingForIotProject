import paho.mqtt.client as mqtt
import time
client = mqtt.Client("test12345")  # clientID único
client.connect("mqtt.eclipseprojects.io", 1883)
client.loop_start()
time.sleep(1)  # esperar conexión
ret = client.publish("test/topic", '{"state":1}', qos=2)
print("Publish rc:", ret.rc)
client.loop_stop()
client.disconnect()
