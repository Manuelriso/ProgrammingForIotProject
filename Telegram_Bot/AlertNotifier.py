# AlertNotifier.py
from MyMQTTforBOT import MyMQTT
import requests
from requests.exceptions import RequestException

############################# ALERT NOTIFIER #######################
class AlertNotifier:
########################### INITIALIZATION ######################
    def __init__(self, mqtt_client: MyMQTT, catalog_url, greenhouse_user_map, greenhouse_map_lock):

        # self.botapp = bot
        self.mqtt = mqtt_client
        self.greenhouse_user_map = greenhouse_user_map 
        self.greenhouse_map_lock = greenhouse_map_lock 
        self.subscribed_topics = set()
        self.catalog_url = catalog_url
        if not self.catalog_url.endswith('/'):
            self.catalog_url += '/'
        self.enqueue_method = None

########################### MQTT SUBSCRIPTION METHODS ######################
    def subscribe_to_topic(self, topic):
        if topic not in self.subscribed_topics:
            self.mqtt.mySubscribe(topic)
            self.subscribed_topics.add(topic)

    def subscribe_to_multiple(self, topics):
        new_topics = set(topics) - self.subscribed_topics
        if new_topics:
            self.mqtt.subscribe_multiple(new_topics)
            self.subscribed_topics.update(new_topics)

    def unsubscribe_from_topic(self, topic):
        if topic in self.subscribed_topics:
            self.mqtt.unsubscribe(topic)
            self.subscribed_topics.remove(topic)

    def unsubscribe_all(self):
        self.mqtt.unsubscribe_all()
        self.subscribed_topics.clear()

############################# SUBSCRIPTION MANAGEMENT ######################
    # Method to be used by the bot to update subscriptions based on user actions
    def update_subscriptions(self, action, greenhouse_id=None, area_id=None, tematic="motion"):
        if action == 'create':
                topic = self.build_topic(greenhouse_id, area_id, tematic)
                self.subscribe_to_topic(topic)
        elif action == 'delete':
            if greenhouse_id and area_id:
                topic = self.build_topic(greenhouse_id, area_id, tematic)
                self.unsubscribe_from_topic(topic)
            elif greenhouse_id:
                # Desuscribirse de todos los topics que empiecen con greenhouse_id
                topics = [t for t in self.subscribed_topics if t.startswith(f"greenhouse{greenhouse_id}/")]
                for topic in topics:
                    self.unsubscribe_from_topic(topic)
        elif action == 'refresh':
            # Desuscribirse de todo
            self.unsubscribe_all()
            # Obtener lista completa del catálogo y suscribirse
            topics = self.build_topics_list_from_catalog()
            self.subscribe_to_multiple(topics)
        print(f"Updating subscriptions: {action}, greenhouse_id: {greenhouse_id}, area_id: {area_id}")
    
    def build_topic(self, greenhouse_id, area_id,tematic):
        return f"greenhouse{greenhouse_id}/area{area_id}/{tematic}"

################################### ALERT PROCESSING ######################
    ### Payload will be of this format:
    # MqttMotion = {
    #         "bn": f"greenhouse1/area1/motion",
    #         "e": [{
    #                 "n": "motion",
    #                 "v": 1,
    #                 "t": time.time(),
    #                 "u": "boolean"
    #             }]
    # }
    def notify(self, msg, payload):
        base_name = payload.get("bn", "")
        print(f" msg: {msg}, datatype of msg: {type(msg)}, datatype of payload: {type(payload)}")
        events = payload.get("e", [])
        GH_ID, AREA_ID = self.get_ids(base_name)
        # if not GH_ID or not AREA_ID:
        #     return
        # # async with greenhouse_map_lock:
        #     # Ensure the greenhouse and area exist in the map
        # if GH_ID not in self.greenhouse_user_map or AREA_ID not in self.greenhouse_user_map[GH_ID]["areas"]:
        #     print(f"Greenhouse {GH_ID} or Area {AREA_ID} not found in the map.")
        #     return

        for event in events:
            situation = event.get("n")
            timestamp = event.get("t")
            unit = event.get("u")
            if situation == "motion":
                value_received = event.get("v") # A 1 or 0
                print(f"Received motion event: {situation} with value {value_received} for GH_ID: {GH_ID}, AREA_ID: {AREA_ID}, timestamp: {timestamp}, unit: {unit}")
                if value_received == 1: # and it already wasn't == last value
                    destinatario = self.get_user_from_id(GH_ID)
                    print("about to acces the notify__user method")
                    self.notify_user(
                        gh_id=GH_ID,
                        area_id=AREA_ID,
                        user_affected=destinatario,
                        alerttype=situation,
                        timestamp=timestamp,
                        unit=unit
                    )
            else: 
                print(f"Unexpected event type: {situation} in topic {base_name}")
                continue

    def notify_user(self, gh_id, area_id, user_affected, alerttype, timestamp, unit): #Sends the alert to the queue of the bot
        print("Something happened, notifying user...")
        if not self.enqueue_method:
            raise ValueError("Enqueue method must be set before using AlertNotifier") 
        self.enqueue_method({
            "chat_id": user_affected,
            "gh_id": gh_id,
            "area_id": area_id,
            "alerttype": alerttype,
            "timestamp": timestamp,
            "unit": unit
        })
        print("Enqueued alert")

############################ AUXILIARY METHODS AND FUNCTIONS ######################
    def get_ids(self, info):
        # Esperamos que 'bn' sea algo como: "greenhouse1/area1/motion"
        parts = info.split("/")
        if len(parts) >= 3:
            gh_id = parts[0].replace("greenhouse", "")  # greenhouse1 -> 1
            area_id = parts[1].replace("area", "")  # area1 -> 1
            return gh_id, area_id
        else:
            print(f"Unexpected format in topic: {info}")
            return None, None  # O podés lanzar una excepción si querés validar
    
    def get_user_from_id(self, gh_id):
        try:
            response = requests.get(f"{self.catalog_url}greenhouses/{gh_id}")
            if response.status_code == 200:
                telegram_id = response.json().get("telegram_ID", [])
                return telegram_id
            return None
        except requests.exceptions.RequestException:
            return None
        
    #Creates a dictionary of the topics, that are all the greenhouses and areas present in the catalog.
    #Their format is like this: "motionTopic": "greenhouse1/area1/motion",
    def build_topics_list_from_catalog(self) -> dict:
        try:
            response = requests.get(f"{self.catalog_url}greenhouses", timeout=10)
            all_greenhouses = response.json().get("greenhouses", [])
            topics = set() #insted of list to avoid duplicates
            for greenhouse in all_greenhouses:
                gh_id = greenhouse.get("greenhouseID")
                for area in greenhouse.get("areas", []):
                    area_id = area.get("ID")
                    motion_topic = area.get("motionTopic")
                    # topics.update({
                    #     # f"greenhouse{greenhouse['greenhouseID']}_area{area['ID']}_temperature": area.get("temperatureDataTopic"),
                    #     # f"greenhouse{greenhouse['greenhouseID']}_area{area['ID']}_humidity": area.get("humidityDataTopic"),
                    #     # f"greenhouse{greenhouse['greenhouseID']}_area{area['ID']}_luminosity": area.get("luminosityDataTopic"),
                    #     f"greenhouse{greenhouse['greenhouseID']}_area{area['ID']}_motion": area.get("motionTopic"),
                    #     })
                    if gh_id and area_id and motion_topic:
                        topics.add(motion_topic)
            return list(topics) # .values() no
        except (RequestException, ValueError) as e:
            print(f"Error fetching topics: {e}")
            return {}