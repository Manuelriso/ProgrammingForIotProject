import requests
import cherrypy
import json
import uuid
import time
from MyMQTT import MyMQTT

class SecurityRESTMQTT:
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
        #{"motion": "on"}
        message_decoded = json.loads(payload)
        message_value = message_decoded["e"][0]["v"]
        
        #Creation of the topic to send the alert "greenhouse1/area1/motion/alert"
        layers=topic.split("/")
        greenhouse=layers[0]
        area=layers[1]
        
        #in areaID only the ID of the area, same for the greenhouse
        areaID=area.replace("area", "")
        greenhouseID=greenhouse.replace("greenhouse", "")
        value=layers[2]
        topic_to_publish=f"{greenhouse}/{area}/{value}/alert"
        
        messageToSend={}
        messageToSend={
                    "bn":topic_to_publish,
                    "e":[
                            {"v": "on",
                            "t":time.time(),
                            "u":"boolean",
                            "n":"motion"
                            }
                        ] 
                    }
        
        
        if(message_value=="on"):
            self.mqttClient.myPublish(topic_to_publish,json.dumps(messageToSend))
            requests.put(f'{self.catalogURL}/{greenhouse}/{area}/motion', data=json.dumps(self.serviceInfo))
            print(f"I published {messageToSend} to {topic_to_publish}")
        
        

if __name__ == "__main__":
    settings = json.load(open('settings.json'))
    security = SecurityRESTMQTT(settings)
    security.registerService()
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    #Inidirizzo IP--> http://localhost:30/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 30})
    cherrypy.tree.mount(security, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            if counter == 10:
                security.updateService()
                counter = 0
    except KeyboardInterrupt:
        security.stop()
        cherrypy.engine.stop()
        print("Security Stopped")
