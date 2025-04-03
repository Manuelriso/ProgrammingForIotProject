# ProgrammingForIotProject

Project about the Programing for IoT course.

TEMPERATURE CONTROL



The Temperature Control is a control strategy that manages the temperature control
system. Its activity depends on a dynamic threshold, it will send actuation commands to
actuators if sensed temperature and humidity are out of range. It works 

i) as an MQTT
subscriber to receive temperature and humidity data from the garden through a DHT11
sensor;--> area1/sensor1/temperature and are1/sensor1/humidity

ii) as an MQTT publisher to send actuation commands to IoT Devices, in order to
switch on or off some air conditioning systems. ---> area1/actuation/temperature (useful for Other Device Connector)


HOW DO WE GET DINAMIC VALUES FROM THE THRESHOLD MANAGEMENT???? MQTT and then me modify them in the catalog?

The answer is ......

---

**1. `load_catalog()`**  
This method loads the areas from the `catalog.json` file and subscribes to the topics for temperature, humidity, and luminosity for each area. It’s called manually when new areas are added or when the catalog is updated. It ensures that the program subscribes to all necessary topics for all areas.

**Assumption**: The topics in the `catalog.json` file follow the format of `"area1/temperature"`, `"area1/humidity"`, etc.

---

**2. `check_conditions(area_id)`**  
This method checks if the current temperature, humidity, or luminosity in a specific area exceeds the predefined thresholds. If any value exceeds its threshold, it publishes an "ON" actuation command for that area; otherwise, it publishes an "OFF" actuation. This is called after receiving new sensor data.

**Assumption**: The `thresholds` for each area are defined in `catalog.json`.

---

**3. `publish(self, area_id, command)`**  
This method publishes the actuation command ("ON"/"OFF") for a specific area to the corresponding MQTT topic. The topic format follows `"area{area_id}/Temperature/actuation"`, where `area_id` is dynamically inserted based on the area being processed.

**Assumption**: The publish topic follows this format: `"area{area_id}/actuation/temperature"`.

---

**4. `notify(self, topic, payload)`**  
This method handles incoming data from subscribed topics. It parses the payload and updates the current temperature, humidity, or luminosity for the relevant area. After updating the values, it calls `check_conditions()` to make decisions based on the latest sensor data.

**Assumption**: The topic format is like `"area{area_id}/sensor_type/{temperature, humidity, luminosity}"`, where `sensor_type` is dynamically extracted from the topic.

---