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