# AlertNotifier.py
from MyMQTTforBOT import MyMQTT
import requests
from requests.exceptions import RequestException
from sharedUtils import normalize_state_to_int

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
        print(f"Updating subscriptions: action={action}, greenhouse_id={greenhouse_id}, area_id={area_id}")
    
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
    # OR THIS:
    # {"motion": "on"}
    #
    
    def notify(self, msgtopic, payload):
        try:
            # Caso 1: Payload tipo SenML (light, temeperature, humidity, etc.)
            if "bn" in payload and "e" in payload:
                base_name = payload.get("bn", "")
                events = payload.get("e", [])
                gh_id, area_id = self.get_ids(base_name)

                for event in events:
                    situation = event.get("n")
                    timestamp = event.get("t")
                    unit = event.get("u")
                    if situation == "motion":
                        value_received = event.get("v")
                        destinatario = self.get_user_from_id(gh_id)
                        print("about to access the notify_user method (SenML)")
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

            # Caso 2: Payload simple tipo {"motion": "on"}
            elif "motion" in payload:
                gh_id, area_id = self.get_ids(msgtopic)
                print("Processing simple payload", "gh_id:", gh_id, "area_id:", area_id)
                if gh_id is None or area_id is None:
                    print(f"[!] Invalid topic: {msgtopic}")
                    return
                value_raw = payload.get("motion")
                value_received = normalize_state_to_int(value_raw)
                destinatario = self.get_user_from_id(gh_id)
                print("about to access the notify_user method (Simple payload)") ########
                self.notify_user(
                    gh_id=gh_id,
                    area_id=area_id,
                    user_affected=destinatario,
                    alerttype="motion",
                    timestamp=None,
                    unit=None,
                    value_received=value_received
                )
                return
            else:
                print(f"[!] Unsupported payload format: {payload}, {payload.datatype}")
        except Exception as e:
            print(f"[!] Error in notify(): {e}")

    def notify_user(self, gh_id, area_id, user_affected, alerttype, timestamp, unit, value_received): #Sends the alert to the queue of the bot
        print("Something happened, notifying user...")
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
        print("Enqueued alert")

############################ AUXILIARY METHODS ######################
    def get_ids(self, info):
        # Esperamos que 'bn' sea algo como: "greenhouse1/area1/motion"
        parts = info.split("/")
        if len(parts) >= 3:
            gh_id = parts[0].replace("greenhouse", "")  # greenhouse1 -> 1
            area_id = parts[1].replace("area", "")  # area1 -> 1
            return gh_id, area_id
        else:
            print(f"Unexpected format in topic: {info}")
            return None, None 
    
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
                    if gh_id and area_id and motion_topic:
                        topics.add(motion_topic)
            return list(topics) # .values() no
        except (RequestException, ValueError) as e:
            print(f"Error fetching topics: {e}")
            return {}