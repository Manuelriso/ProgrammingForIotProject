# ProgrammingForIotProject

Project about the Programing for IoT course.

RASPERRY PI CONNECTOR

The Raspberry Pi Connector is a Device Connector that integrates Raspberry Pi board
technology into the platform. Our idea is to have one Raspberry Pi for a certain area [m2] of
the garden, with their own specific environmental conditions, that can be different from each
other. For each area, we will have different topics representing them. (In our project, having
only one Raspberry board and few sensors, we manage initially only one of these areas).
It will be connected to motion, temperature and humidity sensors to get environmental data
about the garden status. 
It provides REST Web Services to handle this environmental data in order to let the Telegram Bot retrieves it at every moment. 

It also acts as an MQTT publisher, sending information about animals (when detected) and environmental data 
(periodically) to our microservices and database. 

area1/sensor1/temperature
area1/sensor1/humidity
area1/senso1/motion


Every time that it detects a presence of something, it will set a light for 10 sec.
