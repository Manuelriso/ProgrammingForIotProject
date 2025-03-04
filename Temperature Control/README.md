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