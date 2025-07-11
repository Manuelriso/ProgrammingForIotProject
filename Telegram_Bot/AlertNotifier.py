# AlertNotifier.py
from MyMQTTforBOT import MyMQTT
import requests
from requests.exceptions import RequestException
from time import sleep
from sharedUtils import normalize_state_to_int, get_ids
import json

############################# ALERT NOTIFIER #######################
class AlertNotifier:
########################### INITIALIZATION ######################
    def __init__(self, mqtt_client: MyMQTT, catalog_url):
        self.mqtt = mqtt_client
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
            for topic in new_topics:
                self.subscribe_to_topic(topic)

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
        print(f"Updating subscriptions: action={action}, greenhouse_id={greenhouse_id}, area_id={area_id}")
        if action == 'create':
            topic = self.build_topic(greenhouse_id, area_id, tematic)
            self.subscribe_to_topic(topic)
        elif action == 'delete':
            if greenhouse_id and area_id:
                topic = self.build_topic(greenhouse_id, area_id, tematic)
                self.unsubscribe_from_topic(topic)
            elif greenhouse_id:
                # Unsubscribe from all topics starting with greenhouse_id
                topics = [t for t in self.subscribed_topics if t.startswith(f"greenhouse{greenhouse_id}/")]
                for topic in topics:
                    self.unsubscribe_from_topic(topic)
        elif action == 'refresh':
            # Unsubscribe from all topics
            self.unsubscribe_all()
            # Fetch the complete list from the catalog and subscribe
            topics = self.build_topics_list_from_catalog()
            self.subscribe_to_multiple(topics)
    
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
    
    def notify(self, msgtopic, payload):
        try:
            # Caso 1: Payload tipo SenML (light, temeperature, humidity, motionNEW.)
            if "bn" in payload and "e" in payload:
                base_name = payload.get("bn", "")
                events = payload.get("e", [])
                gh_id, area_id = get_ids(base_name)

                for event in events:
                    situation = event.get("n")
                    timestamp = event.get("t")
                    unit = event.get("u")
                    if situation == "motion":
                        value_received = event.get("v")
                        destinatario = self.get_user_from_id(gh_id)
                        sleep (0.2)
                        self.notify_user(
                            gh_id=gh_id,
                            area_id=area_id,
                            user_affected=destinatario,
                            alerttype=situation,
                            timestamp=timestamp,
                            unit=unit,
                            value_received=value_received
                        )
                    else:
                        print(f"Unexpected event type: {situation} in topic {base_name}")
                return
            else:
                print(f"[!] Unsupported payload format: {payload}, {payload.datatype}")
        except Exception as e:
            print(f"[!] Error in notify(): {e}")

    def notify_user(self, gh_id, area_id, user_affected, alerttype, timestamp, unit, value_received): #Sends the alert to the queue of the bot
        print("Something happened, sending data to queue: ", user_affected, "value received: ", value_received)
        if not self.enqueue_method:
            raise ValueError("Enqueue method must be set before using AlertNotifier") 
        self.enqueue_method({
            "chat_id": user_affected,
            "bn": f"greenhouse{gh_id}/area{area_id}/motion",
            "e": [{
                "n": alerttype,
                "v": value_received,  # 1 or 0
                "t": timestamp,
                "u": unit
            }]
        })

############################ AUXILIARY METHODS ######################    
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
            # print(f"Status Code: {response.status_code}")
            # print(f"Content-Type: {response.headers.get('Content-Type')}")
            if response.status_code == 200:
                try:
                    all_greenhouses = response.json().get("greenhouses", [])
                except ValueError:
                    print("Warning: Unexpected Content-Type, attempting manual JSON parsing.")
                    all_greenhouses = json.loads(response.text)
                
                topics = set() #insted of list to avoid duplicates
                for greenhouse in all_greenhouses:
                    gh_id = greenhouse.get("greenhouseID")
                    for area in greenhouse.get("areas", []):
                        area_id = area.get("ID")
                        motion_topic = area.get("motionTopic")
                        if gh_id and area_id and motion_topic:
                            topics.add(motion_topic)
                return list(topics) # .values() no
            print(f"Error: Received status code {response.status_code}")
            return {}
        except (RequestException, ValueError) as e:
            print(f"Error fetching topics: {e}")
            return {}