# SECURITY

The Security microservice is a control strategy that manages the entire garden
It works as
- as an MQTT subscriber to receive movement data from motion sensors; --> greenhouse1/area1/motion

At that topic, i will receive a JSON based on SensorML

- as an MQTT publisher to send alerts for the actuators.
This microservice will send an alert every time that the motion sensor detects the presence of some external entities in the garden.--> greenhouse1/area1/motion/alert



## Motion detection

Every time there's a motion alert, in the catalog we increase by 1 the motion detection of that specific area

