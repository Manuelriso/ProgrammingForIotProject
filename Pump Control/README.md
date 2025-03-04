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