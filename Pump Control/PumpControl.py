from MyMQTT import *
import json

class PumpController:
    def __init__(self, broker, port, client_id, pub_topic_template, catalog_file):
        self.broker = broker
        self.client = MyMQTT(client_id, self.broker, port, self)
        self.catalog_file = catalog_file
        
        # Initialize thresholds and current values, will be updated dynamically
        self.threshold = {}
        self.current_values = {}

        # Initialize list of topics
        self.topics = []

        # The template for the actuation topic, dynamically modified per area
        self.pub_topic_template = pub_topic_template

    def load_catalog(self):
        """ Load areas from catalog.json and subscribe to their topics """
        with open(self.catalog_file, 'r') as f:
            catalog = json.load(f)

        for area in catalog[0]['areas']:
            area_id = area['ID']
            humidity_thresh = area['humidityThreshold']
            temperature_thresh = area['temperatureThreshold']

            self.threshold[area_id] = {
                "temperature": temperature_thresh,
                "humidity": humidity_thresh
            }
            
            self.current_values[area_id] = {
                "temperature": None,
                "humidity": None
            }

            # Create topics dynamically for each area
            temp_data_topic = area['temperatureDataTopic']
            hum_data_topic = area['humidityDataTopic']

            if temp_data_topic:
                self.topics.append(temp_data_topic)
            if hum_data_topic:
                self.topics.append(hum_data_topic)

            for topic in self.topics:
                self.client.mysubscribe(topic)
                print(f"Subscribed to {topic}")

    def mystart(self):
        """ Start the MQTT client and load catalog """
        self.client.start()
        self.load_catalog()

    def mystop(self):
        """ Stop the MQTT client """
        self.client.unsubscribe()
        self.client.stop()

    def publish(self, area_id, command):
        """ Publish actuation message to control the pumps """
        pub_topic = self.pub_topic_template.replace("{area}", f"area{area_id}")
        message = {"actuation": command, "area": area_id}
        self.client.mypublish(pub_topic, message)
        print(f"Published to {pub_topic}: {message}")

    def check_conditions(self, area_id):
        """ Check if humidity or temperature thresholds are exceeded and control pumps accordingly """
        temp = self.current_values[area_id]["temperature"]
        hum = self.current_values[area_id]["humidity"]

        if temp is None or hum is None:
            return  # Wait until we have all values

        if hum < self.threshold[area_id]["humidity"] or temp > self.threshold[area_id]["temperature"]:
            self.publish(area_id, "ON")  # Turn ON the pumps
        else:
            self.publish(area_id, "OFF")  # Turn OFF the pumps

    def notify(self, topic, payload):
        """ Handle incoming data from sensors """
        parsed_payload = json.loads(payload)
        topic_parts = topic.split('/')
        area_id = int(topic_parts[0][4:])  # Extract area ID
        sensor_type = topic_parts[1]  # 'temperature' or 'humidity'

        if sensor_type == "temperature":
            self.current_values[area_id]["temperature"] = parsed_payload["temperature"]
            print(f"Received Temperature Data for Area {area_id}: {self.current_values[area_id]['temperature']}°C")
        elif sensor_type == "humidity":
            self.current_values[area_id]["humidity"] = parsed_payload["humidity"]
            print(f"Received Humidity Data for Area {area_id}: {self.current_values[area_id]['humidity']}%")
        
        self.check_conditions(area_id)

if __name__ == "__main__":
    clientID = "PumpController1234"
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    catalog_file = "catalog.json"
    pub_topic_template = "{area}/actuation/pump"
    
    pump_control = PumpController(broker, port, clientID, pub_topic_template, catalog_file)
    pump_control.mystart()