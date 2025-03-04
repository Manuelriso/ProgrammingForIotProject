# ProgrammingForIotProject

Project about the Programing for IoT course.

Other Device Connector


Other Device Connector is a Device Connector that integrates a board into the platform.
This device simulates a luminosity sensor. For each Raspberry Pi Connector there will be
also one of this. It provides REST Web Services to retrieve the status of connected
appliances. 

It also works as an MQTT subscriber, receiving actuation commands from other
actors (microservices and/or from the user through telegram bot), to manage the water pump,
air conditioning, etc. from the Pump Control and from the Temperature Control --> area1/actuation/pump and area1/actuation/air

As a MQTT publisher it sends the data to the database and the microservices that need them. -->area1/sensor1/luminosity(useful for the Lighting Control and also to store in the Thingspeak database)