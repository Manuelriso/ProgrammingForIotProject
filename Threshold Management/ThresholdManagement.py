import requests
import cherrypy
import json
import uuid
import time
from MyMQTT import MyMQTT

class ThresholdManagement:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.serviceInfo = settings['serviceInfo']
        self.thingSpeakURL = settings["thingspeakURL"]
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]       
        self.actualTime = time.time()
    
    def registerService(self):
        self.serviceInfo['last_update'] = self.actualTime
        requests.post(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_update'] = time.time()
        requests.put(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    
    def updateThresholds(self):
        #We obtain all areas from the catalog
        response=requests.get(f'{self.catalogURL}/areas')
        if response.status_code == 200:
            data = response.json()  # Converte la risposta in dizionario Python
        else:
            print("Errore nella richiesta:", response.status_code)        
        
        for area in data["areas"]:
            areaID=area["ID"]
            temperatureThreshold=area["temperatureThreshold"]
            humidityThreshold=area["humidityThreshold"]
            luminosityThreshold=area["luminosityThreshold"]
            
            
            #I get all data about temperature,humidity and luminosity from the ThisgSpeak
            responseTemperature=requests.get(f'{self.thingSpeakURL}/{areaID}/temperature')
            responseHumidity=requests.get(f'{self.thingSpeakURL}/{areaID}/humidity')
            responseLuminosity=requests.get(f'{self.thingSpeakURL}/{areaID}/luminosity')
            temperatureData=responseTemperature.json()
            humidityData=responseHumidity.json()
            luminosityData=responseLuminosity.json()
            
            #I calculate the mean of every pattern of data
            temperatureSum=0
            humiditySum=0
            luminositySum=0
            for value in temperatureData["values"]:
                temperatureSum+=value
            
            for value in humidityData["values"]:
                humiditySum+=value
                
            for value in luminosityData["values"]:
                luminositySum+=value
                
            
            temperatureMean=temperatureSum/len(temperatureData["values"])
            humidityMean=humiditySum/len(humidityData["values"])
            luminosityMean=luminositySum/len(luminosityData["values"])
            
            #if the temperature mean is much bigger then the threshold, then we need to dicrease the threshold, because today is very hot
            if(temperatureMean>temperatureThreshold+5):
                temperatureThreshold-=1
            #In the opposite way, if outside is really cold, we can also increase the threshold
            if(temperatureMean<temperatureThreshold-5):
                temperatureThreshold+=1
                
            
            #We do the same things for humidity and luminosity
            if(humidityMean>humidityThreshold+5):
                humidityThreshold-=1
            if(humidityMean<humidityThreshold-5):
                humidityThreshold+=1 
                
            
            if(luminosityMean>luminosityThreshold+5):
                luminosityThreshold-=1
            if(luminosityMean<luminosityThreshold-5):
                luminosityThreshold+=1  
                
            area["temperatureThreshold"]=temperatureThreshold 
            area["humidityThreshold"]=humidityThreshold 
            area["luminosityThreshold"]=luminosityThreshold 
            
            requests.put(f'{self.catalogURL}/area', data=json.dumps(area))
            
            
    
    def GET(self,*uri, **params): 
        return
    
    def POST(self,*uri, **params):
        return

if __name__ == "__main__":
    settings = json.load(open('settings.json'))
    ts_adaptor = ThresholdManagement(settings)
    ts_adaptor.registerService()
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    #Inidirizzo IP--> http://localhost:8081/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8081})
    cherrypy.tree.mount(ts_adaptor, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(3)
            counter += 1
            if counter == 20:
                ts_adaptor.updateService()
                ts_adaptor.updateThresholds()
                counter = 0
    except KeyboardInterrupt:
        cherrypy.engine.stop()
        print("Thingspeak Adaptor Stopped")
