#Used for luminosity 
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

def generate_luminosity(base_humidity=60.0, variation=20.0):
    """Simulate a humidity value around a base percentage."""
    return round(random.uniform(base_humidity - variation, base_humidity + variation), 1)

class OtherDeviceConnectorMQTT:
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
            
        self.mqttClient.mysubscribe(self.topics)        
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
        message_value = message_decoded["e"][0]["v"]
        
        layers=topic.split("/")
        greenhouse=layers[0]
        area=layers[1]
        
        #in areaID only the ID of the area, same for the greenhouse
        areaID=area.replace("area", "")
        greenhouseID=greenhouse.replace("greenhouse", "")
        
        if(message_value=="on"):
            response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
            area=response.json()
            if response.status_code == 200:
                if(area["light"]=="off"):
                    area["light"]="on"
                    response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                    if response.status_code == 200:
                        print(f"I've inserted on in the light for the greenhouse {greenhouseID} area {areaID}")
                        
        elif(message_value=="off"):
            response = requests.get(f'{self.catalogURL}/greenhouse{greenhouseID}/areas/{areaID}')
            area=response.json()
            if response.status_code == 200:
                if(area["light"]=="on"):
                    area["light"]="off"
                    response = requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area',data=json.dumps(area))
                    if response.status_code == 200:
                        print(f"I've inserted off in the light for the greenhouse {greenhouseID} area {areaID}")

if __name__ == '__main__':
    c = Catalog_Navigator(settings=json.load(open('settings.json')))
    catalog = c.get_catalog()
    settings = json.load(open('settings.json'))
    connector = OtherDeviceConnectorMQTT(settings)
    #print(f"Catalog: {catalog}")
    catalogURL = settings['catalogURL']
    serviceInfo=settings["serviceInfo"]
    #save service info into CATALOG (post)
    serviceInfo['last_update'] = time.time()
    time.sleep(1)
    connector.registerService()

    while True:
            catalog = c.get_catalog()
            # debug
            #print(f"Catalog: {catalog}, brongioli.")
            for greenhouse in catalog["greenhouses"]: # iterate over greenhouses
                for area in greenhouse["areas"]:
                    # sense luminosity
                    topicLum = c.searchByTopic(greenhouse["greenhouseID"], area["ID"], "luminosityDataTopic")
                    dictLum = {
                        "bn": f"greenhouse{greenhouse['greenhouseID']}/area{area['ID']}/luminosity",
                        "e": [{
                                "n": "luminosity",
                                "v": generate_luminosity(), # just random percentage value
                                "t": time.time(),
                                "u": "percentage"
                            }]
                    }
                    area["currentLuminosity"] = dictLum["e"][0]["v"] #update json
                    connector.mqttClient.myPublish(topicLum, dictLum) #publish to topic Luminosity
                    print(f"Luminosity publish on {topicLum}--{dictLum}")

                    
                    # now put request to the catalog
            for greenhouse in catalog["greenhouses"]:
                update = requests.put(f"{catalogURL}/greenhouse", data=json.dumps(greenhouse))
                print(f"Update status code: {update.status_code}")
                if update.status_code == 200:
                    print("Catalog updated successfully")
                else:
                    print("Failed to update catalog")
            #save service info into CATALOG (put)
            serviceInfo['last_update'] = time.time()
            connector.updateService()                  
            time.sleep(16) #frequency of sensors (due to database update)
