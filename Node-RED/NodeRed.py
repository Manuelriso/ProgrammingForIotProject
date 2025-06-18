import requests
import cherrypy
import json
import uuid
import time
from MyMQTT import MyMQTT

class NodeRed:    
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.serviceInfo = settings['serviceInfo']
        self.thingSpeakURL = settings["thingspeakURL"]
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"] 
        self.actualTime=time.time()      
        
    
    def registerService(self):
        self.serviceInfo['last_updated'] = self.actualTime
        requests.post(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_updated'] = time.time()
        requests.put(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    

if __name__ == "__main__":
    settings = json.load(open('settings.json'))
    nodeRed = NodeRed(settings)
    nodeRed.registerService()
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    #Inidirizzo IP--> http://localhost:8082/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8082})
    cherrypy.tree.mount(nodeRed, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(3)
            counter += 1
            if counter == 25:
                nodeRed.updateService()
                counter = 0
    except KeyboardInterrupt:
        cherrypy.engine.stop()
        print("Thingspeak Adaptor Stopped")
