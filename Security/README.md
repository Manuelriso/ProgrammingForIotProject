# ProgrammingForIotProject

Project about the Programing for IoT course.

SECURITY

The Security microservice is a control strategy that manages the greenhouse/garden
security, preventing thefts or damage from animals. It works 
i) as an MQTT subscriber to receive movement data from motion sensors; --> area1/sensor1/motion

At that topic, i will receive a JSON of the format "motion":"on"

ii) as an MQTT publisher to send alarm/alerts
to IoT devices. This microservice will send an alert every time that the motion sensor detects
the presence of some external entities in the garden.--> area1/motion/alert

What is sent to the alert topic is the json "alert":"on"

Every time there's a motion alert, in the catalog we increase by 1 the motion detection of that specific area

**Detailed descritption**

### **Overview of SecurityController**  
The `SecurityController` microservice manages security by detecting motion and triggering alerts. It subscribes to motion sensor topics and publishes alerts when motion is detected.  

- **Automatically Called Functions:**  
  - `notify(topic, payload)`: Automatically triggered when motion data is received.  
  - `check_motion(area_id)`: Called internally by `notify()` to decide whether to publish an alert.  

- **Manually Called Functions:**  
  - `load_catalog()`: Must be called manually when a new area is added to update subscriptions.  
  - `mystart()`: Starts the MQTT client and subscribes to topics.  
  - `mystop()`: Stops the MQTT client.  

---

### **Brief Description of Each Function**  
- **`publish(self, area_id)`**  
  Publishes an alert to `{area}/motion/alert` when motion is detected.  

- **`check_motion(self, area_id)`**  
  Checks if motion is detected and calls `publish()` to send an alert.  

- **`notify(self, topic, payload)`**  
  Automatically processes incoming motion sensor data, extracts the area ID, updates motion status, and calls `check_motion()`.
