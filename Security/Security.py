import json
from MyMQTT import *

class SecurityController:
    def __init__(self, broker, port, client_id, catalog_file):
        self.broker = broker
        self.client = MyMQTT(client_id, self.broker, port, self)
        self.catalog_file = catalog_file
        
        # Initialize list of topics
        self.topics = []
        self.alert_topic_template = "{area}/motion/alert"

    def load_catalog(self):
        """ Load areas from catalog.json and subscribe to their motion sensor topics """
        with open(self.catalog_file, 'r') as f:
            catalog = json.load(f)
        
        for area in catalog[0]['areas']:
            area_id = area['ID']
            motion_data_topic = f"area{area_id}/sensor1/motion"
            
            # Subscribe to motion detection topics
            self.topics.append(motion_data_topic)
            self.client.mysubscribe(motion_data_topic)
            print(f"Subscribed to {motion_data_topic}")

    def mystart(self):
        """ Start the MQTT client and load catalog """
        self.client.start()
        self.load_catalog()
    
    def mystop(self):
        """ Stop the MQTT client """
        self.client.unsubscribe()
        self.client.stop()
    
    def publish_alert(self, area_id):
        """ Publish an alert message for a specific area """
        alert_topic = self.alert_topic_template.replace("{area}", f"area{area_id}")
        message = {"alert": "Motion detected", "area": area_id}
        self.client.mypublish(alert_topic, message)
        print(f"Published alert to {alert_topic}")
    
    def notify(self, topic, payload):
        """ Handle incoming data from motion sensors """
        parsed_payload = json.loads(payload)
        topic_parts = topic.split('/')
        area_id = int(topic_parts[0][4:])  # Extract area number from the topic (e.g., 'area1')
        
        if parsed_payload.get("motion_detected", False):
            print(f"Motion detected in Area {area_id}, sending alert...")
            self.publish_alert(area_id)

if __name__ == "__main__":
    clientID = "SecurityController1234"
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    catalog_file = "catalog.json"

    security_control = SecurityController(broker, port, clientID, catalog_file)
    security_control.mystart()