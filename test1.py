
import paho.mqtt.client as mqtt
import json

# Define the callback functions for connection and message received
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        ("Connected to MQTT broker")
        client.subscribe("HELLO-TOPIC")
    else:
        print("MQTT Offline")

def on_message(client, userdata, msg):
    print(json.dumps(msg.payload.decode()))

# Create an MQTT client object and set the callback functions
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
try:
    client.connect("localhost", 1883, 60)
except:
    print("MQTT Offline")

# Start the MQTT client loop to process incoming messages
client.loop_forever()
