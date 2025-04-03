# ProgrammingForIotProject

Project about the Programing for IoT course.

PUMP CONTROL

The Pump Control is a control strategy that manages the pumping system, to create the
optimal environment for plant growth. According to some humidity (and temperature)
thresholds it sets on the watering pumps or sets them off. It works 

i) as an MQTT subscriber
to receive temperature and humidity data from the garden through a DHT11 sensor;--> area1/sensor1/humidity and area1/sensor1/temperature

ii) as
an MQTT publisher to send actuation commands to IoT Devices, dis/activating pumps as
needed.--> area1/actuation/pump and area1/actuation/air (useful for the Other Device Connector microservice)


**Detailed Description**

### **Pump Controller Microservice Overview**  
The **Pump Controller** microservice manages the watering pumps based on humidity and temperature data received from the garden sensors. If the measured values exceed or drop below the thresholds, the system activates or deactivates the pumps accordingly.  

### **Function Descriptions:**  

- **`load_catalog(self)`** *(Should be called manually when new areas are added)*  
  Reads the catalog file to extract temperature and humidity thresholds for each area and subscribes to the corresponding topics.  

- **`publish(self, area_id, command)`** *(Usually called automatically by `check_conditions()`, but can be called manually if needed)*  
  Sends an actuation message to turn the pumps ON or OFF for a specific area.  

- **`check_conditions(self, area_id)`** *(Called automatically inside `notify()` after receiving new sensor data)*  
  Evaluates the received temperature and humidity values against the thresholds. If conditions require watering, it publishes an actuation command to activate the pump. Otherwise, it turns it off.  

- **`notify(self, topic, payload)`** *(Called automatically when new MQTT messages arrive)*  
  Parses incoming messages, updates the stored sensor values, and calls `check_conditions()` to decide whether to activate or deactivate the pumps.  

