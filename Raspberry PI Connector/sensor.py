import time
import cherrypy
import requests
import random
import json
import uuid
from CatalogClient import CatalogAPI, Catalog_Navigator
# import board # Uncomment if using a DHT sensor
# import adafruit_dht # Uncomment if using a DHT sensor
import paho.mqtt.client as PahoMQTT
from MyMQTT import *

# sensor = adafruit_dht.DHT11(board.D4) # Uncomment if using a DHT sensor

def generate_temperature(base_temp=20.0, variation=8.0):
    """Simulate a temperature value around a base temperature."""
    return round(random.uniform(base_temp - variation, base_temp + variation), 1)

def generate_humidity(base_humidity=60.0, variation=10.0):
    """Simulate a humidity value around a base percentage."""
    return round(random.uniform(base_humidity - variation, base_humidity + variation), 1)


def generate_binary(probability_of_one=0.5):
    return 1 if random.random() < probability_of_one else 0


class RaspberryConnectorMQTT:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.serviceInfo = settings['serviceInfo']
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        self.topics = settings["mqttTopics"]  # Lista di topic
        
        
        self.mqttClient = MyMQTT(client_id=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)
        self.mqttClient.start()   
        
        for topic in self.topics:
            self.mqttClient.mysubscribe(topic)
                    
        self.actualTime = time.time()
    
    def registerService(self):
        self.serviceInfo['last_update'] = self.actualTime
        requests.post(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_update'] = time.time()
        requests.put(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def stop(self):
        self.mqttClient.stop()
    
    def notify(self, topic, payload):
        message_decoded = json.loads(payload)
        message_value = int(message_decoded["e"][0]["v"])
        
        layers=topic.split("/")
        greenhouse=layers[0]
        area=layers[1]
        actuation=layers[3]
        
        #in areaID only the ID of the area, same for the greenhouse
        areaID=area.replace("area", "")
        greenhouseID=greenhouse.replace("greenhouse", "")
        
        if(actuation=="pump"):
            if(message_value==1):
                response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
                area=response.json()
                if response.status_code == 200:
                    if(area["pump"]==0):
                        area["pump"]=1
                        response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                        if response.status_code == 200:
                            print(f"I've inserted 1 in the pump for the greenhouse {greenhouseID} area {areaID}")
                            
            elif(message_value==0):
                response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
                area=response.json()
                if response.status_code == 200:
                    if(area["pump"]==1):
                        area["pump"]=0
                        response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                        if response.status_code == 200:
                            print(f"I've inserted 0 in the pump for the greenhouse {greenhouseID} area {areaID}")
                            
        elif(actuation=="ventilation"):
            if(message_value==1):
                response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
                area=response.json()
                if response.status_code == 200:
                    if(area["ventilation"]==0):
                        area["ventilation"]=1
                        response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                        if response.status_code == 200:
                            print(f"I've inserted 1 in the ventilation for the greenhouse {greenhouseID} area {areaID}")
                            
            elif(message_value==0):
                response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
                area=response.json()
                if response.status_code == 200:
                    if(area["ventilation"]==1):
                        area["ventilation"]=0
                        response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                        if response.status_code == 200:
                            print(f"I've inserted 0 in the ventilation for the greenhouse {greenhouseID} area {areaID}")


if __name__ == '__main__':
    c = Catalog_Navigator(settings=json.load(open('settings.json')))
    catalog = c.get_catalog()
    settings = json.load(open('settings.json'))
    connector = RaspberryConnectorMQTT(settings)
    #save service info into CATALOG (post)
    catalogURL=settings["catalogURL"]
    connector.registerService()
    #print(f"Catalog: {catalog}")

while True:
    # Prendi il catalogo aggiornato (senza reinizializzare)
    catalog = c.get_catalog()

    for greenhouse in catalog["greenhouses"]:  # Cicla su ogni serra
        for area in greenhouse["areas"]:  # Cicla sulle aree della serra
            if greenhouse["greenhouseID"] != 1 or area["ID"] != 1:

                topicTemp = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "temperatureDataTopic")
                print(f"Topic for temperature: {topicTemp}")

                dictTemp = {
                    "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/temperature",
                    "e": [{
                        "n": "temperature",
                        "v": generate_temperature(),
                        "t": time.time(),
                        "u": "double"
                    }]
                }

                area["currentTemperature"] = dictTemp["e"][0]["v"]
                print(f"Temperature GH{greenhouse['greenhouseID']} Area{area['ID']}: {area['currentTemperature']}")
                connector.mqttClient.myPublish(topicTemp, dictTemp)

                topicHum = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "humidityDataTopic")
                dictHum = {
                    "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/humidity",
                    "e": [{
                        "n": "humidity",
                        "v": generate_humidity(),
                        "t": time.time(),
                        "u": "percentage"
                    }]
                }

                area["currentHumidity"] = dictHum["e"][0]["v"]
                print(f"Humidity GH{greenhouse['greenhouseID']} Area{area['ID']}: {area['currentHumidity']}")
                connector.mqttClient.myPublish(topicHum, dictHum)

                topicMotion = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "motionTopic")
                binary = generate_binary()

                generalMotion = { "bn":topicMotion,"e":[{"v": "on", "t":time.time(),"u":"boolean","n":"motion"}] } if binary == 1 else {  "bn":topicMotion,"e":[{"v": "off", "t":time.time(),"u":"boolean","n":"motion"}] }
                print(f"Motion GH{greenhouse['greenhouseID']} Area{area['ID']}: {binary}")
                connector.mqttClient.myPublish(topicMotion, generalMotion)

    for greenhouse in catalog["greenhouses"]:
        update = requests.put(f"{catalogURL}/greenhouse", data=json.dumps(greenhouse))
        print(f"Update status code: {update.status_code}")
        if update.status_code == 200:
            print("✅ Catalog updated successfully")
        else:
            print("❌ Failed to update catalog")

    connector.updateService()

    time.sleep(20)  # Sleep per simulare letture periodiche
