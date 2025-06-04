import requests
import cherrypy
import json
import uuid
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from MyMQTT import MyMQTT

class TelegramBOT:
    exposed = True
    
    def __init__(self, settings):
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.token=settings['telegram_id']
        self.bot=telepot.Bot(self.token)
        MessageLoop(self.bot, {
            'chat': self.on_chat_message,
            'callback_query': self.on_callback_query
        }).run_as_thread()
        self.serviceInfo = settings['serviceInfo']
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        self.topics = settings["mqttTopics"]  # Lista di topic
        self.standardGreenhouse=settings["standardGreenhouse"]
        
        self.standardArea=settings["standardArea"]
        
        
        self.mqttClient = MyMQTT(client_id=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)
        self.mqttClient.start()   
            
        self.mqttClient.mysubscribe(self.topics)        
        self.actualTime = time.time()
        
        self.user_states = {}
    
        
    def on_chat_message(self,msg):
        content_type, chat_type ,chat_ID = telepot.glance(msg)
        message=msg['text']
        
        if chat_ID not in self.user_states:
            self.user_states[chat_ID] = {"action":None}
        
        if chat_ID in self.user_states:
            state = self.user_states[chat_ID]
            
            if state["action"] == "insert_area":
                    area_id = int(message) 
                    #check of the existence of the area
                    response=requests.get(f'{self.catalogURL}/greenhouses/{state["greenhouse_id"]}')
                    responseComplete=response.json()
                    areas=responseComplete["areas"]
                    if(len(areas)==10):
                        self.bot.sendMessage(chat_ID, "ACHTUNG! ⚠️ Maximum area reached!!!!! ⚠️")
                        return
                    for area in areas:
                        if area["ID"]==area_id:
                            self.bot.sendMessage(chat_ID, "⚠️ Invalid input. the ID is just present.")
                            return
    
                    self.standardArea["ID"] = area_id
                    del self.user_states[chat_ID]
                    gh_id = state["greenhouse_id"]
                    
                    self.user_states[chat_ID] = {
                        "action": "select_plant",
                        "greenhouse_id": gh_id,
                        "area_id":area_id
                    }
                    self.bot.sendMessage(chat_ID, f"✏️ Please enter the plant to grow in your area.")               
                    return
        
            if state["action"] == "select_plant":   
                    gh_id = state["greenhouse_id"]
                    area_id=state["area_id"]
                    plant=message
                    
                    self.standardArea["ID"]=area_id
                    self.standardArea["plants"]=plant
                    self.standardArea["temperatureDataTopic"]=f"greenhouse{gh_id}/area{area_id}/temperature"
                    self.standardArea["humidityDataTopic"]=f"greenhouse{gh_id}/area{area_id}/humidity"
                    self.standardArea["luminosityDataTopic"]=f"greenhouse{gh_id}/area{area_id}/luminosity"
                    self.standardArea["motionTopic"]=f"greenhouse{gh_id}/area{area_id}/motion"
                    self.standardArea["pumpActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/pump"
                    self.standardArea["lightActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/light"
                    self.standardArea["ventilationActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/ventilation"
                    
                    
                    response = requests.post(f'{self.catalogURL}/greenhouse{gh_id}/area',data=json.dumps(self.standardArea))
                    
                    if response.status_code == 201:
                        self.bot.sendMessage(chat_ID, f"✅ Area {area_id} successfully added to Greenhouse {gh_id}.")
                    else:
                        self.bot.sendMessage(chat_ID, f"❌ Failed to add Area {area_id} to Greenhouse {gh_id}.")
                
                    del self.user_states[chat_ID]
                    return
            
            if state["action"] == "select_greenhouse":
                    gh_id = int(message) 
                    #check of the existence of the grennhouse
                    response=requests.get(f'{self.catalogURL}/greenhouses')
                    responseComplete=response.json()
                    greenhouses=responseComplete["greenhouses"]
                    for greenhouse in greenhouses:
                        if greenhouse["greenhouseID"]==gh_id:
                            self.bot.sendMessage(chat_ID, "⚠️ Invalid input. the ID is just present.")
                            return
    
                    del self.user_states[chat_ID]
                    
                    self.user_states[chat_ID] = {
                        "action": "insert_area_in_the_greenhouse",
                        "greenhouse_id": gh_id
                    }
                    self.bot.sendMessage(chat_ID, f"✏️ Please enter the ID of the first area to add in Greenhouse {gh_id}")
                    return
            
            
            if state["action"] == "insert_area_in_the_greenhouse":
                    area_id = int(message) 
    
                    self.standardArea["ID"] = area_id
                    del self.user_states[chat_ID]
                    gh_id = state["greenhouse_id"]
                    
                    self.user_states[chat_ID] = {
                        "action": "select_plant_new_greenhouse",
                        "greenhouse_id": gh_id,
                        "area_id":area_id
                    }
                    self.bot.sendMessage(chat_ID, f"✏️ Please enter the plant to grow in your first area.")               
                    return
            
            
            
            if state["action"] == "select_plant_new_greenhouse":   
                    gh_id = state["greenhouse_id"]
                    area_id=state["area_id"]
                    plant=message
                    
                    self.standardArea["ID"]=area_id
                    self.standardArea["plants"]=plant
                    self.standardArea["temperatureDataTopic"]=f"greenhouse{gh_id}/area{area_id}/temperature"
                    self.standardArea["humidityDataTopic"]=f"greenhouse{gh_id}/area{area_id}/humidity"
                    self.standardArea["luminosityDataTopic"]=f"greenhouse{gh_id}/area{area_id}/luminosity"
                    self.standardArea["motionTopic"]=f"greenhouse{gh_id}/area{area_id}/motion"
                    self.standardArea["pumpActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/pump"
                    self.standardArea["lightActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/light"
                    self.standardArea["ventilationActuation"]=f"greenhouse{gh_id}/area{area_id}/actuation/ventilation"
                    
                    self.standardGreenhouse["areas"].append(self.standardArea)
                    self.standardGreenhouse["greenhouseID"]=gh_id
                    self.standardGreenhouse["creation_date"]=time.strftime("%Y-%m-%d")
                    
                    response = requests.post(f'{self.catalogURL}/greenhouse',data=json.dumps(self.standardGreenhouse))
                    
                    if response.status_code == 201:
                        self.bot.sendMessage(chat_ID, f"✅ Area {area_id} successfully added to Greenhouse {gh_id}.")
                    else:
                        self.bot.sendMessage(chat_ID, f"❌ Failed to add Area {area_id} to Greenhouse {gh_id}.")
                
                    del self.user_states[chat_ID]
                    return
        
        
            
        if message=="/start":
            self.bot.sendMessage(chat_ID,text="Hi! Welcome to the Telegram Bot for the Smart Garden Project, please select a command")
        elif message=="/deletegreenhouse":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            IDlist=[]
            for greenhouse in greenhouses["greenhouses"]:
                IDlist.append(greenhouse["greenhouseID"])
            
            
            keyboard_buttons = []
            for greenhouse in greenhouses["greenhouses"]:
                gh_id = greenhouse["greenhouseID"]
                button = InlineKeyboardButton(text=f"🏠 Greenhouse {gh_id}", callback_data=f"delete_{gh_id}")
                keyboard_buttons.append([button])  # ogni bottone su una riga diversa

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            self.bot.sendMessage(chat_ID, text="Select a greenhouse to delete:", reply_markup=keyboard)
        
        elif message=="/viewcurrentdata":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            IDlist=[]
            for greenhouse in greenhouses["greenhouses"]:
                IDlist.append(greenhouse["greenhouseID"])
            
            
            keyboard_buttons = []
            for greenhouse in greenhouses["greenhouses"]:
                gh_id = greenhouse["greenhouseID"]
                button = InlineKeyboardButton(text=f"🏠 Greenhouse {gh_id}", callback_data=f"view_greenhouse_{gh_id}")
                keyboard_buttons.append([button])  # ogni bottone su una riga diversa

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            self.bot.sendMessage(chat_ID, text="Select a greenhouse to see current data:", reply_markup=keyboard)
        
        
        elif message=="/deletearea":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            IDlist=[]
            for greenhouse in greenhouses["greenhouses"]:
                IDlist.append(greenhouse["greenhouseID"])
            
            
            keyboard_buttons = []
            for greenhouse in greenhouses["greenhouses"]:
                gh_id = greenhouse["greenhouseID"]
                button = InlineKeyboardButton(text=f"🏠 Greenhouse {gh_id}", callback_data=f"deletearea_{gh_id}")
                keyboard_buttons.append([button])  # ogni bottone su una riga diversa

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            self.bot.sendMessage(chat_ID, text="Select the greenhouse:", reply_markup=keyboard)
        
        elif message=="/sendactuation":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            IDlist=[]
            for greenhouse in greenhouses["greenhouses"]:
                IDlist.append(greenhouse["greenhouseID"])
            
            
            keyboard_buttons = []
            for greenhouse in greenhouses["greenhouses"]:
                gh_id = greenhouse["greenhouseID"]
                button = InlineKeyboardButton(text=f"🏠 Greenhouse {gh_id}", callback_data=f"sendactuation_{gh_id}")
                keyboard_buttons.append([button])  # ogni bottone su una riga diversa

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            self.bot.sendMessage(chat_ID, text="Select the greenhouse to send an actuation:", reply_markup=keyboard)
        
        elif message=="/addarea":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            IDlist=[]
            for greenhouse in greenhouses["greenhouses"]:
                IDlist.append(greenhouse["greenhouseID"])
            
            
            keyboard_buttons = []
            for greenhouse in greenhouses["greenhouses"]:
                gh_id = greenhouse["greenhouseID"]
                button = InlineKeyboardButton(text=f"🏠 Greenhouse {gh_id}", callback_data=f"selectgreenhouse_{gh_id}")
                keyboard_buttons.append([button])  # ogni bottone su una riga diversa

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            self.bot.sendMessage(chat_ID, text="In which greenhouse do you want to add an area?:", reply_markup=keyboard)
            
        
        elif message=="/addgreenhouse":
            response=requests.get(f'{self.catalogURL}/greenhouses')
            if response.status_code == 200:
                greenhouses = response.json()
            else:
                self.bot.sendMessage(chat_ID, text="Server error!!")
            
            self.user_states[chat_ID] = {
                        "action": "select_greenhouse",
                    }
            self.bot.sendMessage(chat_ID, f"✏️🌱 Please enter the ID for your greenhouse.")               
            return
            
    
    
    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        print(f"I sended a callback with {query_data}")
        if query_data.startswith("delete_"):
            gh_id = query_data.replace("delete_", "")
            requests.delete(f'{self.catalogURL}/greenhouse/{gh_id}')
            self.bot.sendMessage(from_id, f"✅ Greenhouse {gh_id} deleted.")
        
        elif query_data.startswith("deletearea_"):
            gh_id = query_data.replace("deletearea_", "")
            response = requests.get(f'{self.catalogURL}/greenhouses/{gh_id}')
            if response.status_code == 200:
                greenhouse = response.json()
                areas = greenhouse["areas"]
                if not areas:
                    self.bot.sendMessage(from_id, f"❌ No areas found in Greenhouse {gh_id}.")
                    return

                keyboard_buttons = []
                for area in areas:
                    area_id = area["ID"]
                    button = InlineKeyboardButton(
                        text=f"Area {area_id}",
                        callback_data=f"confirmdeletearea_{gh_id}_{area_id}"
                    )
                    keyboard_buttons.append([button])

                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                self.bot.sendMessage(from_id, text=f"🌱 Select an area in Greenhouse {gh_id} to delete:", reply_markup=keyboard)
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to retrieve Greenhouse {gh_id} information.")
        
                
        elif query_data.startswith("view_greenhouse_"):
            gh_id = int(query_data.replace("view_greenhouse_", ""))
            response = requests.get(f'{self.catalogURL}/greenhouses/{gh_id}')
            if response.status_code == 200:
                greenhouse = response.json()
                areas = greenhouse["areas"]
                if not areas:
                    self.bot.sendMessage(from_id, f"❌ No areas found in Greenhouse {gh_id}.")
                    return

                keyboard_buttons = []
                for area in areas:
                    area_id = area["ID"]
                    button = InlineKeyboardButton(
                        text=f"Area {area_id}",
                        callback_data=f"view_area_{gh_id}_{area_id}"
                    )
                    keyboard_buttons.append([button])

                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                self.bot.sendMessage(from_id, text=f"🌱 Select an area in Greenhouse {gh_id} to view current data:", reply_markup=keyboard)
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to retrieve Greenhouse {gh_id} information.")
                

        elif query_data.startswith("sendactuation_"):
            gh_id = int(query_data.replace("sendactuation_", ""))
            response = requests.get(f'{self.catalogURL}/greenhouses/{gh_id}')
            if response.status_code == 200:
                greenhouse = response.json()
                areas = greenhouse["areas"]
                if not areas:
                    self.bot.sendMessage(from_id, f"❌ No areas found in Greenhouse {gh_id}.")
                    return

                keyboard_buttons = []
                for area in areas:
                    area_id = area["ID"]
                    button = InlineKeyboardButton(
                        text=f"Area {area_id}",
                        callback_data=f"areaactuation_{gh_id}_{area_id}"
                    )
                    keyboard_buttons.append([button])

                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                self.bot.sendMessage(from_id, text=f"🌱 Select an area in Greenhouse {gh_id} to send an actuation:", reply_markup=keyboard)
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to retrieve Greenhouse {gh_id} information.")
        
        
        elif query_data.startswith("areaactuation_"):
            _, gh_id, area_id = query_data.split("_")
            response = requests.get(f'{self.catalogURL}/greenhouse{gh_id}/areas/{area_id}')
            area=response.json()
            if response.status_code == 200:
                actuation_buttons = [
                    [InlineKeyboardButton(text="💡 Toggle Light", callback_data=f"toggle_light_{gh_id}_{area_id}")],
                    [InlineKeyboardButton(text="💧 Activate Pump", callback_data=f"activate_pump_{gh_id}_{area_id}")],
                    [InlineKeyboardButton(text="🌬️ Start Ventilation", callback_data=f"start_ventilation_{gh_id}_{area_id}")]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=actuation_buttons)
                self.bot.sendMessage(from_id, text="🔘 Select an actuation command:", reply_markup=keyboard)
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to get current data.")
        
        
                
        elif query_data.startswith("toggle_light_"):
            ok,_, gh_id, area_id = query_data.split("_")
            response = requests.get(f'{self.catalogURL}/greenhouse{gh_id}/areas/{area_id}')
            area=response.json()
            if response.status_code == 200:
                if(area["light"]=="off"):
                    area["light"]="on"
                    response = requests.put(f'{self.catalogURL}/greenhouse{gh_id}/area',data=json.dumps(area))
                    if response.status_code==200:
                        self.bot.sendMessage(from_id, f"✅ Light activated.")
                    else:
                        self.bot.sendMessage(from_id, f"❌ Error in the connection.")
                else:
                     self.bot.sendMessage(from_id, f"❌ The light is already ON.")   
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to get current data.")
                
        
        elif query_data.startswith("activate_pump_"):
            ok,_, gh_id, area_id = query_data.split("_")
            response = requests.get(f'{self.catalogURL}/greenhouse{gh_id}/areas/{area_id}')
            area=response.json()
            if response.status_code == 200:
                if(area["pump"]==0):
                    area["pump"]=1
                    response = requests.put(f'{self.catalogURL}/greenhouse{gh_id}/area',data=json.dumps(area))
                    if response.status_code==200:
                        self.bot.sendMessage(from_id, f"✅ Pump activated.")
                    else:
                        self.bot.sendMessage(from_id, f"❌ Error in the connection.")
                else:
                     self.bot.sendMessage(from_id, f"❌ The pump is already ON.")   
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to get current data.")
                
        
        elif query_data.startswith("start_ventilation_"):
            ok,_, gh_id, area_id = query_data.split("_")
            response = requests.get(f'{self.catalogURL}/greenhouse{gh_id}/areas/{area_id}')
            area=response.json()
            if response.status_code == 200:
                if(area["ventilation"]==0):
                    area["ventilation"]=1
                    response = requests.put(f'{self.catalogURL}/greenhouse{gh_id}/area',data=json.dumps(area))
                    if response.status_code==200:
                        self.bot.sendMessage(from_id, f"✅ Ventilation activated.")
                    else:
                        self.bot.sendMessage(from_id, f"❌ Error in the connection.")
                else:
                     self.bot.sendMessage(from_id, f"❌ The ventilation is already ON.")   
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to get current data.")
        
        
        
        elif query_data.startswith("view_area_"):
            ok,_, gh_id, area_id = query_data.split("_")
            response = requests.get(f'{self.catalogURL}/greenhouse{gh_id}/areas/{area_id}')
            area=response.json()
            if response.status_code == 200:
                self.bot.sendMessage(from_id, f"✅ Area {area_id} from Greenhouse {gh_id} current data:\nTEMPERATURE: {area['currentTemperature']}\nHUMIDITY: {area['currentHumidity']}\nLUMINOSITY: {area['currentLuminosity']}\nMOTION DETECTED: {area['motionDetected']}.")
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to get current data.")
                
        
        elif query_data.startswith("confirmdeletearea_"):
            _, gh_id, area_id = query_data.split("_")
            response = requests.delete(f'{self.catalogURL}/greenhouse{gh_id}/area/{area_id}')
            if response.status_code == 204:
                self.bot.sendMessage(from_id, f"✅ Area {area_id} from Greenhouse {gh_id} deleted.")
            else:
                self.bot.sendMessage(from_id, f"❌ Failed to delete Area {area_id} from Greenhouse {gh_id}.")
        
         
                
        elif query_data.startswith("selectgreenhouse_"):
            gh_id = query_data.replace("selectgreenhouse_", "")
            response = requests.get(f'{self.catalogURL}/greenhouses/{gh_id}')
            if response.status_code == 200:
                greenhouse = response.json()
            else:
                self.bot.sendMessage(from_id,text="❌ Server error!!")
                
            self.user_states[from_id] = {
                "action": "insert_area",
                "greenhouse_id": gh_id
            }
            self.bot.sendMessage(from_id, f"✏️ Please enter the ID for the new area to add in Greenhouse {gh_id}.")

        
        
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
        
        print(f"Motion detected with MQTT by Telegram BOT on topic {topic}")
        
        layers=topic.split("/")
        greenhouse=layers[0]
        area=layers[1]
        
        #in areaID only the ID of the area, same for the greenhouse
        areaID=int(area.replace("area", ""))
        greenhouseID=int(greenhouse.replace("greenhouse", ""))
          
        alert_text = f"🚨🚨🚨 Motion detected!\nGreenhouse: {greenhouseID}, Area: {areaID}.\nTopic: {topic} 🚨🚨🚨"
        for chat_id in self.user_states.keys():
            self.bot.sendMessage(chat_id, alert_text)
        
        

if __name__ == "__main__":
    settings = json.load(open('settings.json'))
    telegram = TelegramBOT(settings)
    telegram.registerService()
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    
    #Inidirizzo IP--> http://localhost:30/
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 9097})
    cherrypy.tree.mount(telegram, '/', conf)
    
    try:
        cherrypy.engine.start()
        counter = 0
        while True:
            time.sleep(2)
            counter += 1
            if counter == 20:
                telegram.updateService()
                counter = 0
    except KeyboardInterrupt:
        telegram.stop()
        cherrypy.engine.stop()
        print("Security Stopped")
