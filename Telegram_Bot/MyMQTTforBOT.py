import paho.mqtt.client as PahoMQTT
import json
import time

class MyMQTT:
    def __init__(self, clientID, broker, port, notifier=None):
        self.broker = broker
        self.port = port
        #we need to give a notifier that it will use if it's a subscriber (if not no need)
        self.notifier = notifier
        self.clientID = clientID
        self._topics = set()  ####### All the topics subscribed
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
            print("⚠️ Error by connecting: ", rc)
        ##########################

    # def myOnMessageReceived (self, paho_mqtt , userdata, msg):
    #     # A new message is received
    #     # now we call the method notify from the notifier class, so when a message will be received
    #     # ok i need to go to on.message = myOnMessageReceived, and say ok I need to take my notifier object and its notify method
    #     # it will go to self.notifier = notifier and look if it has a notify method
    #     self.notifier.notify(msg.topic, msg.payload) #instead msg.payload we could put json.loads(msg)
 
    def myOnMessageReceived(self, paho_mqtt, userdata, msg):
        payload_str = msg.payload.decode('utf-8')
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            print("Error decoding JSON payload:", payload_str)
            return
        if self.notifier and hasattr(self.notifier, 'notify'):
            self.notifier.notify(msg.topic, payload) 
        else:
            print("Notifier is not set or doesn't have a notify method.")

    def myPublish(self, topic, msg, qos=2):
        if qos not in [0, 1, 2]: #####
            raise ValueError("QoS must be 0, 1, or 2")
        #########################
        if not self.connected:
            print("ERROR: Not connected to the broker, cannot publish")
            return {"status_code": 503, "error": "Not connected to the broker"}
        # print(f"[DEBUG] Publishing to {topic} with msg={msg} (type: {type(msg)})")
        #########################
        try:
            info = self._paho_mqtt.publish(topic, json.dumps(msg), qos)
        ##################
            # Paho returns an MQTTMessageInfo object with an .rc attribute
            if info.rc == 0:
                return {"status_code": 200}
            else:
                return {"status_code": 500, "error": f"Publish failed with rc={info.rc}"}
        except Exception as e:
            return {"status_code": 501, "error": str(e)}
        ##################

    def mySubscribe(self, topic, qos=2):
        if qos not in [0, 1, 2]: #####
            raise ValueError("QoS must be 0, 1, or 2")
        if topic in self._topics:  #####
            print(f"Already subscribed to {topic}")
            return
        self._paho_mqtt.subscribe(topic, qos)
        self._isSubscriber = True
        self._topics.add(topic) #####
        self._topic = topic  ####
        print ("Bot subscribed to %s" % (topic))
 
    def start(self,timeout=5):
        #manage connection to broker
        self._paho_mqtt.connect(self.broker , self.port)
        self._paho_mqtt.loop_start()
        ####
        #time.sleep(1)
        # Esperar hasta 5 segundos que se conecte
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        if not self.connected:
            raise Exception("Could not connect to the MQTT broker")
        ####

    def subscribe_multiple(self, topics, batch_size=10): ####
        topics = list(topics)
        # Split topics into batches to avoid overwhelming the broker
        for i in range(0, len(topics), batch_size):
            batch = topics[i:i + batch_size]
            for topic in batch:
                self.mySubscribe(topic)

    def unsubscribe(self, topic=None): ######
        if self._isSubscriber:
            if topic is None:
                topic = self._topic  # if no topic is passed, use the last saved one
            if topic in self._topics:
                self._paho_mqtt.unsubscribe(topic)
                self._topics.remove(topic)
                print(f"Bot unsubscribed from {topic}")
                if topic == self._topic:
                    self._topic = next(iter(self._topics), "")  # update the last topic
            else:
                print(f"Not subscribed to {topic}")

    def unsubscribe_all(self): #########
        if self._isSubscriber:
            for topic in list(self._topics):
                self._paho_mqtt.unsubscribe(topic)
                print(f"Unsubscribed from {topic}")
            self._topics.clear()
            self._topic = ""
            
    def stop (self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber 
            # self._paho_mqtt.unsubscribe(self._topic)
            self.unsubscribe_all() ##################
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()

