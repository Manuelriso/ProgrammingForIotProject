from MyMQTT import *
import json
import time
import threading
from CatalogClient import *


class PumpController:
    def __init__(self, settings):
        self.settings = settings
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        
        
        # Initialize MyMQTT with notifier
        #NO client ID in the settings.json
        self.mqtt_client = MyMQTT(self.broker, self.port, settings["clientID"], notifier=self)
        #self.mqtt_client.start()

        # Initialize Catalog_Navigator
        self.catalog_navigator = Catalog_Navigator()
        GH_ID= self.catalog_navigator.get_greenhouse_ID()
        Areas_ID= self.catalog_navigator.get_areas_ID()
        devices_ID= self.catalog_navigator.get_devices_ID()
        Services_ID= self.catalog_navigator.get_services_ID()
        
        

        # Get all subscription topics from the catalog
        subscription_topics = self.catalog_navigator.get_all_subscription_topics()

        # Subscribe to each topic individually
        for topic in subscription_topics:
            if topic:  # Ensure topic is not None
                self.mqtt_client.mysubscribe(topic)

    def startSim(self):
        """Start the MQTT client"""
        self.mqtt_client.start()
        print("Pump controller simulation started")

    def stopSim(self):
        """Stop the MQTT client and clean up"""
        self.mqtt_client.unsubscribe()
        self.mqtt_client.stop()
        print("Pump controller simulation stopped")
        
        
    def update_subscriptions(self):
        """Update MQTT subscriptions based on current catalog state"""
        # Get current topics from catalog
        current_topics = set(self.catalog_navigator.get_all_subscription_topics())
        
        # Get currently subscribed topics
        subscribed_topics = set(getattr(self.mqtt_client, 'subscribed_topics', []))
        
        # Unsubscribe from removed topics
        for topic in subscribed_topics - current_topics:
            if topic:  # Ensure topic is not None
                self.mqtt_client.unsubscribe(topic)
                print(f"Unsubscribed from removed topic: {topic}")
        
        # Subscribe to new topics
        for topic in current_topics - subscribed_topics:
            if topic:  # Ensure topic is not None
                self.mqtt_client.mysubscribe(topic)
                print(f"Subscribed to new topic: {topic}")
        
        # Update the subscribed topics list
        self.mqtt_client.subscribed_topics = list(current_topics)
        
            
    # Notify 
    # Notify gy getting the topic that was subscribed to and the payload and then does some processing and then publish and put request to the required key value
    def notify(self, topic, payload):
        try:
            # Parse topic format: greenhouseX/areaY/sensorType
            topic_parts = topic.split('/')
            if len(topic_parts) != 3:
                print(f"Ignoring malformed topic: {topic}")
                return

            # Extract numeric IDs
            try:
                greenhouse_id = int(topic_parts[0].replace("greenhouse", ""))
                area_id = int(topic_parts[1].replace("area", ""))
                sensor_type = topic_parts[2].lower()
            except ValueError:
                print(f"Invalid ID format in topic: {topic}")
                return

            # Parse payload
            try:
                payload_dict = json.loads(payload)
                sensor_value = float(payload_dict.get("value", 0))
                timestamp = payload_dict.get("timestamp", time.time())
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Invalid payload: {payload} - Error: {str(e)}")
                return

            # Process based on sensor type
            pump_value = 0  # Default to off
            
            if sensor_type == "temperature":
                # Example: Turn on pump if temperature too high
                threshold = self.catalog_navigator.searchByThreshold(greenhouse_id, area_id, "tempThreshold")
                if threshold and sensor_value > threshold:
                    pump_value = 1
                    print(f"High temperature ({sensor_value} > {threshold}), activating pump")
                    
            elif sensor_type == "humidity":
                # Example: Turn on pump if humidity too low
                threshold = self.catalog_navigator.searchByThreshold(greenhouse_id, area_id, "humidityThreshold")
                if threshold and sensor_value < threshold:
                    pump_value = 1
                    print(f"Low humidity ({sensor_value} < {threshold}), activating pump")
                    
            
            else:
                print(f"Ignoring unsupported sensor type: {sensor_type}")
                return

            # Create pump actuation topic
            pump_topic = f"greenhouse{greenhouse_id}/area{area_id}/actuation/pump"
            
            # Prepare pump command message
            pump_msg = {
                "bn": f"greenhouse{greenhouse_id}/area{area_id}",
                "e": [{
                    "n": "pump",
                    "v": pump_value,
                    "t": timestamp,
                    "u": "boolean"
                }]
            }

            # Publish pump command
            self.mqtt_client.mypublish(pump_topic, json.dumps(pump_msg))
            print(f"Published pump {pump_value} to {pump_topic}")

            # Update catalog
            self.catalog_navigator.insert_pump_actuation(greenhouse_id, area_id, pump_value)
            
            # Call UpdateActuation through CatalogAPI
            catalog_api = CatalogAPI(self.catalog_navigator, self.settings)
            catalog_api.UpdateActuation(greenhouse_id, area_id, pump=pump_value)

        except Exception as e:
            print(f"Error in notify: {str(e)}")



    
    