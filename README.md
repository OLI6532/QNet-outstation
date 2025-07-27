# QNet-outstation

## Features

All QNet Outstations run this Python application to handle connections to the MQTT Broker and interfacing with the
onboard GPIO of the Raspberry Pi.

The MQTT broker disseminates messages between the server and Outstations.

There are two types of QNet model:

- **Q-Lite** – Is based on a Raspberry Pi Zero
- **Q-Pro** – Is based a Raspberry Pi 3B

> [!NOTE]  
> **Q-Lite** models must be configured to connect to the network wirelessly due to the lack of onboard physical network
> interface.

The Python application is agnostic of the hardware model and can be run on either type.

## Installation and Setup

### Physical GPIO Wiring

The default wiring of the GPIO devices is:

- `RED_LED`: Pin 4
- `GREEN_LED`: Pin 11
- `BUTTON_PIN`: Pin 16
- `RELAY_SWITCH`: Unassigned

These pins are chosen because of their proximity to a ground pin, allowing for a 2x1 2.54 mm dupont connector to be
wired to each IO device.

The `RELAY_SWITCH` output is provisioned for future use and currently serves no purpose.

### Initialisation Process

1. The application starts and the LED Controller and MQTT Client classes are both instantiated.
2. The device connects to the broker to announce itself as online.
3. The device enters the `IDLE` state and waits to receive commands from the server.

A system service should be configured to start the application automatically, after the network interface services (`network.target`) have started.

### MQTT Message Structure
There are two message types (topics) that are used between Outstations and the Broker: **status** and **command** messages. 

#### Status Messages
Status messages are always sent from an Outstation to the broker to announce connection or disconnections from the broker. Every Outstation on startup sends a connected status message and sets the LWT message to announce the disconnection on its behalf:
```json lines
{
  "state": "IDLE",
  "online": true // or false
}
```

#### Command Messages
Command messages are used to inform the system of a change in state. These messages are bidirectional however the only state command an Outstation would send is the `READY` command.

```json lines
{
  "state": "GO"
}
```

## Additional Setup

### Disabling Wi-Fi Power Save Mode

Some Raspberry Pi Wi-Fi models put the Wi-Fi chip into power-saving mode after a few seconds of inactivity which can
lead to noticeable delays when using QNet.

To check if Power Save Mode is enabled:

```bash
iw wlan0 get power_save
```

To disable Power Save Mode:

```bash
sudo iw wlan0 set power_save off
```

This will improve latency across wireless QNet and make them more responsive.

A function is provided by default within the application to execute this command once the script starts.