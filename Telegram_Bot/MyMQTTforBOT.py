import paho.mqtt.client as PahoMQTT
import json
class MyMQTT:
    def __init__(self, clientID, broker, port, notifier=None):
        self.broker = broker
        self.port = port
        #we need to give a notifier that it will use if it's a subscriber (if not no need)
        self.notifier = notifier
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID,True)  
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
        #######################
        self.connected = False
        #######################
 
    def myOnConnect (self, paho_mqtt, userdata, flags, rc):
        print ("Connected to %s with result code: %d" % (self.broker, rc))
        ##########################
        if rc == 0:
            self.connected = True  # ✅ Marca como conectado
        else:
            print("⚠️ Error al conectar: ", rc)
        ##########################

    def myOnMessageReceived (self, paho_mqtt , userdata, msg):
        # A new message is received
        # now we call the method notify from the notifier class, so when a message will be received
        # ok i need to go to on.message = myOnMessageReceived, and say ok I need to take my notifier object and its notify method
        # it will go to self.notifier = notifier and look if it has a notify method
        self.notifier.notify(msg.topic, msg.payload) #instead msg.payload we could put json.loads(msg)
        

    def myPublish(self, topic, msg):
        #########################
        if not self.connected:
            print("ERROR: No conectado al broker, no se puede publicar")
            return {"status_code": 503, "error": "No conectado al broker"}
        print(f"[DEBUG] Publishing to {topic} with msg={msg} (type: {type(msg)})")
        #########################
        try:
            info = self._paho_mqtt.publish(topic, json.dumps(msg), 2)
        ##################
            # Paho devuelve un objeto MQTTMessageInfo con un atributo .rc
            if info.rc == 0:
                return {"status_code": 200}
            else:
                return {"status_code": 500, "error": f"Publish failed with rc={info.rc}"}

        except Exception as e:
            return {"status_code": 501, "error": str(e)}
       ##################

 
    def mySubscribe (self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2) 
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        self._topic = topic
        print ("subscribed to %s" % (topic))
 
    def start(self):
        #manage connection to broker
        self._paho_mqtt.connect(self.broker , self.port)
        self._paho_mqtt.loop_start()
        ####
        #time.sleep(1)
        # Esperar hasta 5 segundos que se conecte
        import time
        timeout = 5
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        if not self.connected:
            raise Exception("No se pudo conectar al broker MQTT")
        ####


    def unsubscribe(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber 
            self._paho_mqtt.unsubscribe(self._topic)
            
    def stop (self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber 
            self._paho_mqtt.unsubscribe(self._topic)
 
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
