from MyMQTT import *
import json

class TempController:

    def __init__(self, broker, port, client_id, pub_topic_template, catalog_file):
        self.broker = broker
        self.client = MyMQTT(client_id, self.broker, port, self)
        self.catalog_file = catalog_file
        
        # Initialize thresholds and current values, will be updated dynamically
        self.threshold = {}
        self.current_values = {}

        # Initialize list of topics
        self.topics = []

        # The template for the actuation topic, this will be dynamically modified to include the area and sensor type
        # Example: "area1/temperature/actuation"
        self.pub_topic_template = pub_topic_template

    def load_catalog(self):
        """ Load areas from catalog.json and subscribe to their topics """
        with open(self.catalog_file, 'r') as f:
            catalog = json.load(f)

        # Loop through each area in the catalog
        for area in catalog[0]['areas']:
            area_id = area['ID']
            humidity_thresh = area['humidityThreshold']
            temperature_thresh = area['temperatureThreshold']
            luminosity_thresh = area['luminosityThreshold']
            plants = area['plants']

            # Initialize thresholds and current values for each area
            self.threshold[area_id] = {
                "temperature": temperature_thresh,
                "humidity": humidity_thresh,
                "luminosity": luminosity_thresh
            }

            self.current_values[area_id] = {
                "temperature": None,
                "humidity": None,
                "luminosity": None
            }

            # Create topics dynamically for each area
            temp_data_topic = area['temperatureDataTopic']
            hum_data_topic = area['humidityDataTopic']
            lum_data_topic = area['luminosityDataTopic']

            # Add the topics to the list of topics to subscribe to
            if temp_data_topic:  # Only subscribe if the topic exists
                self.topics.append(temp_data_topic)
            if hum_data_topic:
                self.topics.append(hum_data_topic)
            if lum_data_topic:
                self.topics.append(lum_data_topic)

            # Subscribe to each topic dynamically
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

    def publish(self, area_id, sensor_type, command):
        """ Publish actuation message for a specific area """
        # Build the topic dynamically based on the area ID and sensor type 
        pub_topic = self.pub_topic_template.replace("{area}", f"area{area_id}").replace("{sensor_type}", sensor_type)
        message = {"actuation": command, "area": area_id}
        self.client.mypublish(pub_topic, message)
        print(f"Published to {pub_topic}: {message}")

    def check_conditions(self, area_id):
        """ Check if current temperature, humidity, or luminosity exceeds threshold for the given area and act accordingly """
        temp = self.current_values[area_id]["temperature"]
        hum = self.current_values[area_id]["humidity"]
        lum = self.current_values[area_id]["luminosity"]

        if temp is None or hum is None or lum is None:
            return  # Wait until we have all values

        if temp > self.threshold[area_id]["temperature"] or hum > self.threshold[area_id]["humidity"] or lum > self.threshold[area_id]["luminosity"]:
            self.publish(area_id, "Temperature", "ON")  # Turn ON the system (e.g., air conditioning, lights)
        else:
            self.publish(area_id, "Temperature", "OFF")  # Turn OFF the system

    def notify(self, topic, payload):
        """ Handle the incoming data from subscribed topics """
        parsed_payload = json.loads(payload)

        # Extract area ID and sensor type from the topic following the format 'area2/sensor1/temperature', etc.
        topic_parts = topic.split('/')
        area_id = int(topic_parts[0][4:])  # Extract area number from the topic (e.g., 'area1') to get the area ID
        sensor_type = topic_parts[1]  # 'temperature', 'humidity', or 'luminosity'

        # Handle temperature data
        if sensor_type == "temperature":
            self.current_values[area_id]["temperature"] = parsed_payload["temperature"]
            print(f"Received Temperature Data for Area {area_id}: {self.current_values[area_id]['temperature']}°C")

        # Handle humidity data
        elif sensor_type == "humidity":
            self.current_values[area_id]["humidity"] = parsed_payload["humidity"]
            print(f"Received Humidity Data for Area {area_id}: {self.current_values[area_id]['humidity']}%")

        # Handle luminosity data
        elif sensor_type == "luminosity":
            self.current_values[area_id]["luminosity"] = parsed_payload["luminosity"]
            print(f"Received Luminosity Data for Area {area_id}: {self.current_values[area_id]['luminosity']} lux")

        # Check conditions for the specific area after receiving new data
        self.check_conditions(area_id)


if __name__ == "__main__":
    clientID = "MohamedHussien1234"
    broker = "mqtt.eclipseprojects.io"
    port = 1883
    catalog_file = "catalog.json"  # Path to catalog.json file

    # Template for the actuation topic, this will be dynamically modified to include the area and sensor type
    pub_topic_template = "{area}/{sensor_type}/actuation"

    temp_control = TempController(broker, port, clientID, pub_topic_template, catalog_file)
    temp_control.mystart()