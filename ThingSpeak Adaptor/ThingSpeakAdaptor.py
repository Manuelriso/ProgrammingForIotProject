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
        self.serviceInfo['last_update'] = self.actualTime
        requests.post(f'{self.catalogURL}/services', data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_update'] = self.actualTime
        requests.put(f'{self.catalogURL}/services', data=json.dumps(self.serviceInfo))
    
    def stop(self):
        self.mqttClient.stop()
    
    def notify(self, topic, payload):
        #{'bn':f'SensorREST_MQTT_{self.deviceID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}
        message_decoded = json.loads(payload)
        message_value = message_decoded["e"][0]['v']
        decide_measurement = message_decoded["e"][0]["n"]
        
        error=False
        if decide_measurement=="temperature":
            print("\n \n Temperature Message")
            field_number=1
            #I'm extracting the "area" of our garden, in order to change the right database.
            channel=topic.split("/")[0]
        elif decide_measurement=="humidity":
            print("\n \n Humidity Message")
            field_number=2
            channel=topic.split("/")[0]
        elif decide_measurement=="luminosity":
            print("\n \n Luminosity Message")
            field_number=3
            channel=topic.split("/")[0]
        else: 
            error=True
        if error:
            print("Error")
        else:
            print(message_decoded)
            self.uploadThingspeak(field_number=field_number,field_value=message_value,channel=channel)

    
    def uploadThingspeak(self, field_number, field_value,channel):
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
    
    def GET(self,*uri, **params): #.../1/temperature
        if(uri[1]=="temperature"):
            channel=uri[0]
            urlToSend=f"https://api.thingspeak.com/channels/{self.temperatureChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyTemperature}&results=10"
            r=requests.get(urlToSend)
            data=r.json()
            field_key = f"field{channel}"
            field_values = [feed[field_key] for feed in data["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
        elif(uri[1]=="humidity"):
            channel=uri[0]
            urlToSend=f"https://api.thingspeak.com/channels/{self.humidityChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyHumidity}&results=10"
            r=requests.get(urlToSend)
            data=r.json()
            field_key = f"field{channel}"
            field_values = [feed[field_key] for feed in data["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
        elif(uri[1]=="luminosity"):
            channel=uri[0]
            urlToSend=f"https://api.thingspeak.com/channels/{self.luminosityChannelID}/fields/{channel}.json?api_key={self.channelReadAPIkeyLuminosity}&results=10"
            r=requests.get(urlToSend)
            field_key = f"field{channel}"
            field_values = [feed[field_key] for feed in r.text["feeds"] if feed[field_key] is not None]
            json_output = json.dumps({"values": field_values})
            
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
    
    #Inidirizzo IP--> http://localhost:9090/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 9090})
    cherrypy.tree.mount(ts_adaptor, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            if counter == 20:
                ts_adaptor.updateService()
                counter = 0
    except KeyboardInterrupt:
        ts_adaptor.stop()
        cherrypy.engine.stop()
        print("Thingspeak Adaptor Stopped")
