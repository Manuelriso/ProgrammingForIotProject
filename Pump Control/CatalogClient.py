import json
import requests
from datetime import datetime
import cherrypy
import time


class Catalog_Navigator:
    def __init__(self, settings):
        self.settings = settings
        # Initialize with default structure

        self.data = {"greenhouses": [], "devices": [], "services": []}

            
        # If we have settings and no data, try to fetch from catalogURL

        try:
            response = requests.get(f'{self.settings["catalogURL"]}/greenhouses')
            fetched_data = response.json()
            # print(f"Fetched data from {self.settings['catalogURL']}: {fetched_data}")
                # Only update if the fetched data has the expected structure
            self.data=fetched_data
            print("Catalog data loaded successfully from REST API.")
        except Exception as e:
            print(f"Error loading catalog: {e}")
             #Keep the default structure


    def get_catalog(self):
        """Return the catalog data."""
        try:
            response = requests.get(f'{self.settings["catalogURL"]}/greenhouses')
            fetched_data = response.json()
            # print(f"Fetched data from {self.settings['catalogURL']}: {fetched_data}")
                # Only update if the fetched data has the expected structure
            self.data=fetched_data
            print("Catalog data loaded successfully from REST API.")
        except Exception as e:
            print(f"Error loading catalog: {e}")
                #Keep the default structure
        return self.data     
  
    # Search for a topic by its name, areaid and ghID
    def searchByTopic(self, greenhouse_id, area_id, topic_key):
    # Search for the greenhouse with the given ID
        for greenhouse in self.data["greenhouses"]:
            if greenhouse["greenhouseID"] == greenhouse_id:
                # Search for the area with the given area ID
                for area in greenhouse["areas"]:
                    if area["ID"] == area_id:
                        # If the topic_key exists in the area, return the topic value
                        if topic_key in area:
                            return area[topic_key]
                        else:
                            return None  # Topic key not found in the area
                return None  # Area ID not found in the greenhouse
        return None  # Greenhouse ID not found

    # Search for a threshold by its name,  areaid and ghID
    def searchByThreshold(self, greenhouse_id, area_id, threshold_key):
        # Search for the greenhouse with the given ID
        for greenhouse in self.data["greenhouses"]:
            if greenhouse["greenhouseID"] == greenhouse_id:
                # Search for the area with the given ID
                for area in greenhouse["areas"]:
                    if area["ID"] == area_id:
                        # Return the threshold value if key exists
                        if threshold_key in area:
                            return area[threshold_key]
                        else:
                            return None  # Threshold key not found
                return None  # Area ID not found
        return None  # Greenhouse ID not found

      
    # Search for devices that offer a specific service type
    def searchByServiceName(self, service_name):
        # Loop through the list of services
        for service in self.data["services"]:
            if service["serviceName"] == service_name:
                return service  # Return the full service dictionary
        return None  # Service name not found
    
    #get all the areas IDs in a list 
    def get_areas_ID(self):
        area_ids = []
        for greenhouse in self.data["greenhouses"]:
            for area in greenhouse["areas"]:
                area_ids.append(area["ID"])
        return area_ids
      
    #get all the GH IDs in a list   
    def get_greenhouse_ID(self):
        greenhouse_ids = []
        for greenhouse in self.data["greenhouses"]:
            greenhouse_ids.append(greenhouse["greenhouseID"])
        return greenhouse_ids
    
    #get all the devices IDs in a list 
    def get_devices_ID(self):
        device_ids = []
        for device in self.data["devices"]:
            device_ids.append(device["ID"])
        return device_ids
    
    #get all the service IDs in a list 
    def get_services_ID(self):
        service_ids = []
        for service in self.data["services"]:
            service_ids.append(service["ID"])
        return service_ids


    def insert_pump_actuation(self, greenhouse_id, area_id, value):
        # Validate input
        if value not in [0, 1]:
            return {"message": "Invalid value. Must be 0 or 1."}

        # Search for the greenhouse
        for greenhouse in self.data["greenhouses"]:
            if greenhouse["greenhouseID"] == greenhouse_id:
                # Search for the area
                for area in greenhouse["areas"]:
                    if area["ID"] == area_id:
                        # Update the pump value
                        area["pump"] = value
                        return {
                            "message": f"Pump actuation updated to {value} in greenhouse {greenhouse_id}, area {area_id}."
                        }
                return {"message": f"Area ID {area_id} not found in greenhouse {greenhouse_id}"}
        return {"message": f"Greenhouse ID {greenhouse_id} not found"}
    
    
    def update_sub_topics(self, previous_greenhouse_ids):
        current_greenhouse_ids = self.get_greenhouse_ID()

        # Convert both lists to sets
        current_set = set(current_greenhouse_ids)
        previous_set = set(previous_greenhouse_ids)

        # Determine added and removed greenhouses
        added_greenhouses = current_set - previous_set
        removed_greenhouses = previous_set - current_set

        updated_topics = []

        for greenhouse in self.data["greenhouses"]:
            gh_id = greenhouse["greenhouseID"]

            if gh_id in added_greenhouses or gh_id in removed_greenhouses:
                for area in greenhouse["areas"]:
                    updated_topics.extend([
                        area["temperatureDataTopic"],
                        area["humidityDataTopic"],
                        area["luminosityDataTopic"],
                        area["motionTopic"]
                    ])

        return updated_topics

    def update_pub_topics(self, previous_greenhouse_ids):
        current_greenhouse_ids = self.get_greenhouse_ID()

        # Convert both lists to sets
        current_set = set(current_greenhouse_ids)
        previous_set = set(previous_greenhouse_ids)

        # Determine added and removed greenhouses
        added_greenhouses = current_set - previous_set
        removed_greenhouses = previous_set - current_set

        updated_pub_topics = []

        for greenhouse in self.data["greenhouses"]:
            gh_id = greenhouse["greenhouseID"]

            if gh_id in added_greenhouses or gh_id in removed_greenhouses:
                for area in greenhouse["areas"]:
                    updated_pub_topics.extend([
                        area["pumpActuation"],
                        area["lightActuation"],
                        area["ventilationActuation"]
                    ])

        return updated_pub_topics
    
    def get_all_subscription_topics(self):
        topics = []
        for greenhouse in self.data["greenhouses"]:
            for area in greenhouse["areas"]:
                topics.extend([
                    area.get("temperatureDataTopic"),
                    area.get("humidityDataTopic"),
                    area.get("luminosityDataTopic"),
                    #area.get("motionTopic")
                ])
        return topics
    
    def get_all_pub_topics(self):
        topics = []
        for greenhouse in self.data["greenhouses"]:
            for area in greenhouse["areas"]:
                topics.extend([
                    area.get("pumpActuation"),
                    area.get("lightActuation"),
                    area.get("ventilationActuation")
                ])
        return topics


    
    # Print the entire catalog as a JSON string
    def printAll(self):
        return json.dumps(self.data, indent=2)  # Convert catalog data to a nicely formatted JSON string



############################################################################################################

# CatalogAPI class exposes methods as RESTful endpoints
class CatalogAPI(object):
    exposed = True  # Make the class methods exposed to CherryPy
    
    def __init__(self, catalog_navigator, settings):
        # Initialize with an instance of Catalog_Navigator for handling catalog operations
        self.catalog_navigator = catalog_navigator
        self.settings = settings
        self.catalogURL = settings['catalogURL']
        self.serviceInfo = settings['serviceInfo']

    
    # Handle POST requests for inserting a new service
    def registerService(self):
        self.serviceInfo['last_updated'] = time.time()  # Use proper timestamp
        try:
            requests.post(f'{self.catalogURL}/service',json=self.serviceInfo )
        except requests.exceptions.RequestException as e:
            return {"message": f"Failed to register service: {e}"}
        
    def updateService(self):
        self.serviceInfo['last_updated'] = time.time()
        requests.put(f'{self.catalogURL}/service', data=json.dumps(self.serviceInfo))   
    
    # Handle PUT requests for updating an actuation

    def UpdateActuation(self, greenhouseID, areaID, pump):
        #try:
        # 1. Get the entire catalog
        c = Catalog_Navigator(self.settings)
        catalog = c.get_catalog()

        # 3. Update the pump value
        for greenhouse in catalog["greenhouses"]:
            if greenhouse["greenhouseID"] == greenhouseID:
                # Search for the correct area by ID
                for area in greenhouse["areas"]:
                    if area["ID"] == areaID:
                        # Update the pump value
                        area["pump"] = pump   
                             
        # 5. Make the PUT request to update the area
        for greenhouse in catalog["greenhouses"]:
            update = requests.put(f"{self.catalogURL}/greenhouse", data=json.dumps(greenhouse))
            print(f"Update status code: {update.status_code}")
            if update.status_code == 200:
                print("Catalog updated successfully")
            else:
                print("Failed to update catalog")
        
        print(f"Pump actuation updated to {pump} in greenhouse {greenhouseID}, area {areaID}")
        return {
            "message": "Actuation updated successfully",
            "updated_area": areaID
        }
            
        # except requests.exceptions.RequestException as e:
        #     print(f"Error updating actuation: {e}")
        #     return {"message": f"Failed to update actuation: {e}"}
    

    
    

