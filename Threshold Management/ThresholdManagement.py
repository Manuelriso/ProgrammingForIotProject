import requests
import cherrypy
import json
import uuid
import time
from MyMQTT import MyMQTT

#This function is used to compute a weighted mean of the vector it recieves as input
def weighted_mean(values):
    n = len(values)
    if n == 0:
        return 0
    weights = [i + 1 for i in range(n)] 
    total_weight = sum(weights)
    weighted_sum = sum(float(v) * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


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
        #We obtain all greenhouses, and for every area in each greenhouse, we do the threshold management
        response=requests.get(f'{self.catalogURL}/greenhouses')
        if response.status_code == 200:
            data = response.json()  # Python dictionary in data
        else:
            print("Request Error", response.status_code)        
        
        for greenhouse in data["greenhouses"]:
            greenhouseID=greenhouse["greenhouseID"]
            for area in greenhouse["areas"]:
                areaID=area["ID"]
                temperatureThreshold=area["temperatureThreshold"]
                humidityThreshold=area["humidityThreshold"]
                luminosityThreshold=area["luminosityThreshold"]
                
                
                #I get all data about temperature,humidity and luminosity from the ThingSpeakAdaptor
                responseTemperature=requests.get(f'{self.thingSpeakURL}/greenhouse{greenhouseID}/area{areaID}/temperature')
                time.sleep(2)
                responseHumidity=requests.get(f'{self.thingSpeakURL}/greenhouse{greenhouseID}/area{areaID}/humidity')
                time.sleep(2)
                responseLuminosity=requests.get(f'{self.thingSpeakURL}/greenhouse{greenhouseID}/area{areaID}/luminosity')
                temperatureData=responseTemperature.json()
                humidityData=responseHumidity.json()
                luminosityData=responseLuminosity.json()
                
                #I calculate the mean of every pattern of data
                temperatureSum=0
                humiditySum=0
                temperatureMean=0
                humidityMean=0
                luminosityMean=0
                luminositySum=0
                for value in temperatureData["values"]:
                    temperatureSum+=float(value)
                
                for value in humidityData["values"]:
                    humiditySum+=float(value)
                    
                for value in luminosityData["values"]:
                    luminositySum+=float(value)
                    
                
                if(len(temperatureData["values"])!=0 or len(humidityData["values"])!=0 or len(luminosityData["values"])!=0):
                    if(len(temperatureData["values"])!=0):
                        
                        #if the temperature weighted mean is much bigger then the threshold, then we need to dicrease the threshold, because today is very hot
                        #print(f"\n\nLunghezza temperatureValue-->{len(temperatureData['values'])}")
                        #print(f"\n\nValori -->{temperatureData['values']}")
                        temperatureMean = weighted_mean(temperatureData["values"])

                        if(temperatureMean>temperatureThreshold+5):
                            temperatureThreshold-=1
                        #In the opposite way, if outside is really cold, we can also increase the threshold
                        if(temperatureMean<temperatureThreshold-5):
                            temperatureThreshold+=1
                            
                        #print(f"{temperatureMean}")
                            
                            
                    if(len(humidityData["values"])!=0):
                        humidityMean = weighted_mean(humidityData["values"])

                        #We do the same things for humidity and luminosity
                        if(humidityMean>humidityThreshold+5):
                            humidityThreshold-=1
                        if(humidityMean<humidityThreshold-5):
                            humidityThreshold+=1 
                            
                        #print(f"{humidityMean}")
                        
                    if(len(luminosityData["values"])!=0):
                          
                        luminosityMean = weighted_mean(luminosityData["values"])
               
                        if(luminosityMean>luminosityThreshold+5):
                            luminosityThreshold-=1
                        if(luminosityMean<luminosityThreshold-5):
                            luminosityThreshold+=1
                        
                        #print(f"{luminosityMean}")
                            
                            
                                          
                
                if(temperatureThreshold<45 and temperatureThreshold>0):   
                    area["temperatureThreshold"]=temperatureThreshold 
                    
                if(humidityThreshold<100 and humidityThreshold>0):
                    area["humidityThreshold"]=humidityThreshold
                
                if(luminosityThreshold<100 and luminosityThreshold>0): 
                    area["luminosityThreshold"]=luminosityThreshold 
                
                requests.put(f'{self.catalogURL}/greenhouse{greenhouseID}/area', data=json.dumps(area))
                print(f"I've sent an update to the catalog for the greenhouse {greenhouseID} and for the area {areaID}")
            
            
    
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
            if counter == 21:
                ts_adaptor.updateService()
                ts_adaptor.updateThresholds()
                counter = 0
    except KeyboardInterrupt:
        cherrypy.engine.stop()
        print("Thingspeak Adaptor Stopped")
