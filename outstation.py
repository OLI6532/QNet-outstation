import json
import logging
import threading
import time
import uuid
#  --- Logger ---
from logging import getLogger, INFO

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

import util.system as util
from util import logf

log = getLogger(__name__)
log.setLevel(INFO)

# Define a custom formatter for pretty output
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logf.LogFormatter())

log.addHandler(ch)

#  --- Configuration ---
"""
If the configuration of the QNet system is changed, update the values below to define the connection properties.
"""
MQTT_BROKER = "qnet.local"
MQTT_PORT = 1883

# Generates a unique ID for this Outstation
DEVICE_ID = "qlite-" + hex(uuid.getnode())[2:]

# GPIO Pin Configuration
RED_LED_PIN = 4
GREEN_LED_PIN = 11
BUTTON_PIN = 26


# --- State Definitions ---
class State:
    IDLE = "IDLE"
    STANDBY = "STANDBY"
    READY = "READY"
    GO = "GO"
    OFFLINE = "OFFLINE"


# --- LED Controller (runs in a separate thread) ---
class LedController(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state = State.IDLE
        self.start()

    def run(self):
        """The main loop for the LED thread"""
        while not self._stop_event.is_set():
            with self._lock:
                state = self._state

            if state in (State.IDLE, State.READY, State.GO):
                # No flashing; let set_state handle the solid output
                time.sleep(0.05)
                continue

            elif state == State.STANDBY:
                GPIO.output(GREEN_LED_PIN, GPIO.LOW)

                for _ in range(25):  # 0.25s in 10ms chunks
                    if self._state != State.STANDBY or self._stop_event.is_set():
                        break
                    GPIO.output(RED_LED_PIN, GPIO.HIGH)
                    time.sleep(0.01)

                for _ in range(25):
                    if self._state != State.STANDBY or self._stop_event.is_set():
                        break
                    GPIO.output(RED_LED_PIN, GPIO.LOW)
                    time.sleep(0.01)

        # Final clean-up on thread stop
        GPIO.output(RED_LED_PIN, GPIO.LOW)
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)

    def set_state(self, new_state):
        """Thread-safe method to change the LED state"""
        with self._lock:
            if self._state != new_state:
                log.info(f"LED Controller changing state to {new_state}")
                self._state = new_state
                # Immediately apply non-flashing states
                if new_state == State.IDLE:
                    GPIO.output(RED_LED_PIN, GPIO.LOW)
                    GPIO.output(GREEN_LED_PIN, GPIO.LOW)
                elif new_state == State.READY:
                    GPIO.output(GREEN_LED_PIN, GPIO.LOW)
                    GPIO.output(RED_LED_PIN, GPIO.HIGH)
                elif new_state == State.GO:
                    GPIO.output(RED_LED_PIN, GPIO.LOW)
                    GPIO.output(GREEN_LED_PIN, GPIO.HIGH)

    def stop(self):
        """Set the stop event to end the LED thread"""
        self._stop_event.set()


#  --- Main Application ---
class OutstationApp:
    def __init__(self):
        log.info("Initialising Outstation application...")
        try:  # Attempt to disable power management
            util.disable_power_save()
            log.info("Power management disabled successfully")
        except ChildProcessError as e:
            log.warning(f"Failed to disable power management: {e.strerror}")

        self.client = mqtt.Client(client_id=DEVICE_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.led_controller = LedController()
        self.current_state = State.IDLE
        self._setup_gpio()
        self._setup_mqtt()

    def _setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RED_LED_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(GREEN_LED_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH)

        # Add interrupt for button press
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=self.button_pressed_callback, bouncetime=200)
        log.info("GPIO setup complete")

        time.sleep(2)  # Give the GPIO time to settle

    def _setup_mqtt(self):
        """Sets up MQTT callbacks and connection"""
        self.status_topic = f"qnet/outstation/{DEVICE_ID}/status"
        self.command_topic = f"qnet/outstation/{DEVICE_ID}/command"

        #  Set Last Will and Testament
        lwt_payload = json.dumps({"online": False})
        self.client.will_set(self.status_topic, payload=lwt_payload, qos=1, retain=True)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        log.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

    def on_connect(self, client: mqtt.Client, userdata, flags, rc, properties=None):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            log.info("Connected to MQTT Broker successfully")
            #  Subscribe to the command topic
            client.subscribe(self.command_topic)
            log.info(f"Subscribed to {self.command_topic}")
            #  Announce online status
            online_payload = json.dumps({"online": True})
            client.publish(self.status_topic, payload=online_payload, qos=1, retain=True)
            log.info(f"Published online status to {self.status_topic}")

            # Once the system is settled, extinguish the LEDs to inform the user it is ready
            # If both LEDs remain on after powering up the device, the user can know there was
            # a problem
            GPIO.output(RED_LED_PIN, GPIO.LOW)
            GPIO.output(GREEN_LED_PIN, GPIO.LOW)
        else:
            log.info(f"Failed to connect, return code: {rc}")

    def on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        log.debug(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
        try:
            payload = json.loads(msg.payload.decode())
            new_state = payload.get("state")
            if new_state and new_state != self.current_state:
                log.debug(f"Received new state command: {new_state}")
                self.current_state = new_state
                self.led_controller.set_state(new_state)
        except json.JSONDecodeError:
            log.info("Error decoding JSON payload.")
        except Exception as e:
            log.info(f"An error occurred in on_message: {e}")

    def button_pressed_callback(self, channel):
        """Interrupt callback for the physical button press."""
        log.debug("Button pressed!")
        if self.current_state == State.STANDBY:
            log.info("Acknowledging STANDBY. Sending READY state to server.")
            ack_payload = json.dumps({"state": State.READY})
            self.client.publish(self.status_topic, payload=ack_payload, qos=1)

    def run(self):
        """Starts the main loop"""
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            log.warning("Shutting down...")
        finally:
            self.led_controller.stop()
            self.led_controller.join()
            GPIO.cleanup()
            #  Publish offline status on clean exit
            offline_payload = json.dumps({"online": False})
            self.client.publish(self.status_topic, payload=offline_payload, qos=1, retain=True)
            self.client.disconnect()
            log.info("Shutdown complete")


if __name__ == '__main__':
    app = OutstationApp()
    app.run()
