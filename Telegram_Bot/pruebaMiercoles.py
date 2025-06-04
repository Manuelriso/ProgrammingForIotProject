import time

from MyMQTTforBOT import MyMQTT  # Asegurate de que este archivo se llame MyMQTT.py o ajustá el import

# Parámetros
clientID = "TestPublisher"
broker = "mqtt.eclipseprojects.io"
port = 1883
topic = "greenhouse2/area1/motion"
payload = {"motion": "on"}

# Crear instancia del cliente MQTT
publisher = MyMQTT(clientID=clientID, broker=broker, port=port)

# Iniciar conexión
publisher.start()

# Publicar el mensaje
response = publisher.myPublish(topic, payload)
print(f"[→] Publicación a '{topic}' → {response}")

# Esperar un poco y detener
time.sleep(1)
publisher.stop()
