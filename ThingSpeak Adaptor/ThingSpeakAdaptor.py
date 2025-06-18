import requests
import cherrypy
import json
import uuid
import time
from MyMQTT import MyMQTT

class ThingspeakAdaptorRESTMQTT:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.serviceInfo = settings['serviceInfo']
        self.baseURL = settings["ThingspeakURL"]
        self.channelWriteAPIkeyTemperature = settings["ChannelWriteAPIkeyTemperature"]
        self.channelReadAPIkeyTemperature = settings["ChannelReadAPIKeyTemperature"]
        self.channelWriteAPIkeyHumidity = settings["ChannelWriteAPIkeyHumidity"]
        self.channelReadAPIkeyHumidity = settings["ChannelReadAPIKeyHumidity"]
        self.channelWriteAPIkeyLuminosity = settings["ChannelWriteAPIkeyLuminosity"]
        self.channelReadAPIkeyLuminosity = settings["ChannelReadAPIKeyLuminosity"]
        self.temperatureChannelID=settings["TemperatureChannelID"]
        self.humidityChannelID=settings["HumidityChannelID"]
        self.luminosityChannelID=settings["LuminosityChannelID"]
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        self.topics = settings["mqttTopics"]  # Lista di topic
        
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)
        self.mqttClient.start()
        
        for topic in self.topics:
            self.mqttClient.mySubscribe(topic)
        
        self.actualTime = time.time()
    
    def registerService(self):
        self.serviceInfo['last_updated'] = self.actualTime
        requests.post(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_updated'] = time.time()
        requests.put(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))
    
    def stop(self):
        self.mqttClient.stop()
    
    
    #Topic=greenhouse1/area1/temperature
    def notify(self, topic, payload):
        #{'bn':f'SensorREST_MQTT_{self.deviceID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}
        topic_parts = topic.split("/")
        
        if topic_parts[0].startswith("greenhouse"):

            print(f"Payload received: {payload}")
            
            message_decoded = json.loads(payload)
            #Control on the right structure of the payload
            if not isinstance(message_decoded, dict) or 'e' not in message_decoded:
                return  
        
            if not isinstance(message_decoded['e'], list) or len(message_decoded['e']) == 0:
                return  
        
            if not isinstance(message_decoded['e'][0], dict) or 'v' not in message_decoded['e'][0]:
                return  
            

            message_value = message_decoded['e'][0]['v']
            decide_measurement = message_decoded['e'][0]['n']
            
            error=False
            if decide_measurement=="temperature":
                print("\n \n Temperature Message")
                field_number=1
                #I'm extracting the "area" of our garden, in order to change the right database.
                area=topic.split("/")[1]
                channel=area.replace("area", "")
                #I extract the greenhouse
                greenhouse=topic.split("/")[0]
                greenhouseID=int(greenhouse.replace("greenhouse", ""))
                
            elif decide_measurement=="humidity":
                print("\n \n Humidity Message")
                field_number=2
                area=topic.split("/")[1]
                channel=area.replace("area", "")
                #I extract the greenhouse
                greenhouse=topic.split("/")[0]
                greenhouseID=int(greenhouse.replace("greenhouse", ""))
                
            elif decide_measurement=="luminosity":
                print("\n \n Luminosity Message")
                field_number=3
                area=topic.split("/")[1]
                channel=area.replace("area", "")
                #I extract the greenhouse
                greenhouse=topic.split("/")[0]
                greenhouseID=int(greenhouse.replace("greenhouse", ""))
            else: 
                error=True
            if error:
                print("Error")
            else:
                print(message_decoded)
                self.uploadThingspeak(field_number=field_number,field_value=message_value,channel=channel,greenhouseID=greenhouseID)

    
    def uploadThingspeak(self, field_number, field_value,channel,greenhouseID):
        if(greenhouseID==1):
            if(field_number==1):
                urlToSend = f'{self.baseURL}{self.channelWriteAPIkeyTemperature}&field{channel}={field_value}'
                response = requests.get(urlToSend)
            elif(field_number==2):
                urlToSend = f'{self.baseURL}{self.channelWriteAPIkeyHumidity}&field{channel}={field_value}'
                response = requests.get(urlToSend)
            elif(field_number==3):
                urlToSend = f'{self.baseURL}{self.channelWriteAPIkeyLuminosity}&field{channel}={field_value}'
                response = requests.get(urlToSend)
            else:
                print("Error")
            
            print(response.text)
        else:
            print(f"I received the message on the greenhouse {greenhouseID}, but I can't store it in the database")
            
        print(f"I uploaded a value in the channel {channel}, fieldvalue={field_number} in the greenhouse {greenhouseID}")
    
    def GET(self,*uri, **params): #.../greenhouse1/area1/temperature
        if(len(uri)==3 and uri[2]=="temperature"):
            greenhouse=int(uri[0].replace("greenhouse",""))
            
            #We can only create a database for one greenhouse
            if(greenhouse!=1):
                print("There's a problem, we don't have enough channel in the database, ill send you data of the first greenhouse")
            
            channel=uri[1].replace("area","")
            
            urlToSend=f"https://api.thingspeak.com/channels/{self.temperatureChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyTemperature}&results=10"
            r=requests.get(urlToSend)
            data=r.json()
            field_key = f"field{channel}"
            field_values = [float(feed[field_key]) for feed in data["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
            
        elif(len(uri)==3 and uri[2]=="humidity"):
            greenhouse=int(uri[0].replace("greenhouse",""))
            
            #We can only create a database for one greenhouse
            if(greenhouse!=1):
                print("There's a problem, we don't have enough channel in the database, ill send you data of the first greenhouse")
            
            channel=uri[1].replace("area","")
            urlToSend=f"https://api.thingspeak.com/channels/{self.humidityChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyHumidity}&results=10"
            r=requests.get(urlToSend)
            data=r.json()
            field_key = f"field{channel}"
            field_values = [feed[field_key] for feed in data["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
            
        elif(len(uri)==3 and uri[2]=="luminosity"):
            greenhouse=int(uri[0].replace("greenhouse",""))
            
            #We can only create a database for one greenhouse
            if(greenhouse!=1):
                print("There's a problem, we don't have enough channel in the database, ill send you data of the first greenhouse")
            
            channel=uri[1].replace("area","")
            urlToSend=f"https://api.thingspeak.com/channels/{self.luminosityChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyLuminosity}&results=10"
            r=requests.get(urlToSend)
            data=r.json()
            field_key = f"field{channel}"
            field_values = [feed[field_key] for feed in data["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
        else:
            raise cherrypy.HTTPError("Error in the parameters")
        
        cherrypy.response.status=200
        return json_output
    
    def POST(self):
        return

if __name__ == "__main__":
    settings = json.load(open('settings.json'))
    ts_adaptor = ThingspeakAdaptorRESTMQTT(settings)
    ts_adaptor.registerService()
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    #Indirizzo IP--> http://localhost:9090/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 9090})
    cherrypy.tree.mount(ts_adaptor, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            if counter == 13:
                ts_adaptor.updateService()
                counter = 0
    except KeyboardInterrupt:
        ts_adaptor.stop()
        cherrypy.engine.stop()
        print("Thingspeak Adaptor Stopped")
