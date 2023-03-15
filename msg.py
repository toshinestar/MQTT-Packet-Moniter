import paho.mqtt.client as mqtt
import json
import time

topic = "HELLO-TOPIC"
# Define the callback functions for connection and message received
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(topic)
    else:
        print("MQTT Offline")

def on_message(client, userdata, msg):
    global last_message_time
    last_message_time = time.time()
    print(json.loads(msg.payload))

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
client.loop_start()

# Set the freshDataTime to the desired value in seconds
freshDataTime = 10

# Initialize the last message time to the current time
last_message_time = time.time()

# Loop until the program is terminated
while True:
# Check if the last message time is older than freshDataTime seconds
    if time.time() - last_message_time > freshDataTime:
        print("Label=OFFLINE")
        time.sleep(1)
# In the on_message callback function, we update the last_message_time global variable to the current time whenever a message is received.

# In the main loop, we check if the time since the last message is older than freshDataTime seconds. If it is, we print "Label=OFFLINE". We then sleep for 1 second before checking again.

# Note that we're using client.loop_start() instead of client.loop_forever() to start the MQTT client loop. This allows us to run the main loop in parallel and check the message reception time at regular intervals.
