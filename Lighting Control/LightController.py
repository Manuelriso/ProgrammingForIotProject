from MyMQTT import *
import json
import time
import threading
from CatalogClient import *
import uuid


class LightController:
    def __init__(self, settings):
        self.settings = settings
        self.broker = settings["brokerIP"]
        self.port = settings["brokerPort"]
        
        # Initialize MyMQTT
        self.mqtt_client = MyMQTT(client_id=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self)
        self.mqtt_client.start()
        # Set the message callback
       # self.mqtt_client.myOnMessageRecieved(None, None,)  

        try:
            # Fetch catalog data
            response = requests.get(f'{self.settings["catalogURL"]}')
            response.raise_for_status()
            catalog_data = response.json()
            
            # Create Catalog_Navigator with the fetched data and settings
            self.catalog_navigator = Catalog_Navigator(settings=self.settings)
            
            # Get current subscription topics from catalog
            current_topics = set(self.catalog_navigator.get_all_subscription_topics())
            
            # Subscribe to each topic individually
            for topic in current_topics:
                if topic:  # Ensure topic is not None
                    self.mqtt_client.mysubscribe(topic)
                    print(f"Subscribed to new topic: {topic}")
        except Exception as e:
            print(f"Error initializing pump controller: {e}")
            # Initialize with empty catalog navigator if there's an error
            self.catalog_navigator = Catalog_Navigator(settings=self.settings)

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
        """Update MQTT subscriptions based on current catalog state via REST API"""
        try:
            # Step 1: Get the full catalog via REST
            response = requests.get(f'{self.settings["catalogURL"]}')
            #response.raise_for_status()
            catalog_data = response.json()

            # Step 2: Create Catalog_Navigator with the fetched data
            navigator = Catalog_Navigator(self.settings)

            # Step 3: Get current subscription topics from catalog
            current_topics = set(navigator.get_all_subscription_topics())

            # Step 4: Get currently subscribed topics from MQTT client
            subscribed_topics = set(getattr(self.mqtt_client, 'subscribed_topics', []))

            # Step 5: Unsubscribe from removed topics
            for topic in subscribed_topics - current_topics:
                if topic:
                    self.mqtt_client.unsubscribe(topic)
                    print(f"[updated] Unsubscribed from removed topic: {topic}")

            # Step 6: Subscribe to new topics
            for topic in current_topics - subscribed_topics:
                if topic:
                    self.mqtt_client.mysubscribe(topic)
                    print(f"[updated] Subscribed to new topic: {topic}")

            # Step 7: Update local record of subscribed topics
            self.mqtt_client.subscribed_topics = list(current_topics)

        except requests.exceptions.RequestException as e:
            print(f"Failed to update subscriptions: {e}")
        except Exception as e:
            print(f"Error updating subscriptions: {e}")
            
    # Notify 
    # Notify gy getting the topic that was subscribed to and the payload and then does some processing and then publish and put request to the required key value
    def notify(self, topic, payload):
        #try:
            # Parse topic and payload
        parsed_payoload= json.loads(payload)
        parsed_topic = parsed_payoload['bn']
        topic_parts = parsed_topic.split('/')
        print(f"Received topic: {parsed_topic}")
        print(f"Received payload: {parsed_payoload}")
        if len(topic_parts) != 3:
            print(f"Ignoring malformed topic: {topic}")
            return

        try:
            greenhouse_id = int(topic_parts[0].replace("greenhouse", ""))
            area_id = int(topic_parts[1].replace("area", ""))
            sensor_type = topic_parts[2].lower()
        except ValueError:
            print(f"Invalid ID format in topic: {topic}")
            return

        try:
            payload_dict = json.loads(payload)
            
            sensor_value = payload_dict["e"][0]["v"]
            #print(f"Received payload: {sensor_value}")
            timestamp = payload_dict.get("timestamp", time.time())
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Invalid payload: {payload} - Error: {str(e)}")
            return

            # Get thresholds from catalog once
        thresholds = {
            "luminosity": self.catalog_navigator.searchByThreshold(greenhouse_id, area_id, "luminosityThreshold")
        }

        # Validate thresholds
        if None in thresholds.values():
            print(f"Missing thresholds for greenhouse {greenhouse_id}, area {area_id}")
            return

            # Determine pump state based on sensor type
        lum_value = "off"
        if sensor_type == "luminosity" and sensor_value > thresholds["luminosity"]:
            print(f"High luminosity ({sensor_value} > {thresholds['luminosity']}), activating light")
            lum_value = "off"
        elif sensor_type == "luminosity" and sensor_value < thresholds["luminosity"]:
            print(f"Low luminosity ({sensor_value} <= {thresholds['luminosity']}), deactivating light")
            lum_value = "on"
        elif sensor_type not in ["luminosity"]:
            print(f"Ignoring unsupported sensor type: {sensor_type}")
            return

            # Prepare and publish pump command
        lum_topic = f"greenhouse{greenhouse_id}/area{area_id}/actuation/light"
        lum_msg = {
            "bn": f"greenhouse{greenhouse_id}/area{area_id}",
            "e": [{
                "n": "pump",
                "v": lum_value,
                "t": timestamp,
                "u": "boolean"
            }]
        }

        self.mqtt_client.mypublish(lum_topic, lum_msg)
        print(f"Published pump {lum_value} to {lum_topic}")

        # Update catalog through API
        catalog_api = CatalogAPI(self.catalog_navigator, self.settings)
        update_result = catalog_api.UpdateActuation(greenhouse_id, area_id, lum_value)
        
        if "error" in update_result.get("message", "").lower():
            print(f"Failed to update catalog: {update_result['message']}")

        #except Exception as e:
            #print(f"Error in notify: {str(e)}")


    
    