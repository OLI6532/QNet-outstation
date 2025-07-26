# QNet-outstation

All QNet Outstations run this small Python application that handles connections to the MQTT Broker and interfacing with the onboard GPIO of the Raspberry Pi.

There are two types of QNet model:
- **Q-Lite** – Uses a Raspberry Pi Zero
- **Q-Pro** – Uses a Raspberry Pi 3B

> [!NOTE]  
> **Q-Lite** models must be configured to connect to the network wirelessly due to the lack of onboard physical network interface.

The Python application is agnostic of the hardware model and can be run on either type.

## Installation and Setup
The system is tested and working on Bookworm Raspberry Pi OS. Other OS versions are likely to work but are untested.

### Physical GPIO Wiring
The default wiring of the GPIO devices is:
- `RED_LED`: 4
- `GREEN_LED`: 11
- `BUTTON_PIN`: 16
- `RELAY_SWITCH`: Unassigned

These pins are chosen because of their proximity to a ground pin, allowing for a 2x1 2.54 mm dupont connector to be wired to each device.

The `RELAY_SWITCH` output is provisioned for future use and currently serves no purpose.

