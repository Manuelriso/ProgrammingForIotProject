# ProgrammingForIotProject

Project about the Programing for IoT course.

Lighting Control


The Lighting Control microservice is a control strategy that manages the lighting system in
the garden’s dependencies.It’s going to receive continuous notions about the illuminance in
the garden, and will make decisions based on the perfect illuminance values needed by the
garden, fixed with a threshold. It works
i) as an MQTT subscriber to receive data about light in the garden through a luminosity sensor
(simulated by the Device connector); ---> area1/sensor1/luminosity 

ii) as an MQTT publisher to send actuation commands to the respective IoT Devices.