# Azimut Energy

This is a Home Assistant integration for monitoring Azimut Energy battery systems.

## Features

- Real-time battery monitoring
- State of charge tracking
- Voltage and current monitoring
- Power consumption tracking
- Temperature monitoring
- Energy flow tracking

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository to HACS
3. Search for "Azimut Energy" in HACS
4. Click Install
5. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract the `azimut_battery` folder into your `custom_components` directory
3. Restart Home Assistant
4. Add the integration through the Home Assistant UI

## Configuration

1. In Home Assistant, go to Configuration > Integrations
2. Click the "+ Add Integration" button
3. Search for "Azimut Energy"
4. Enter your battery system's host address and port
5. Click Submit

## Available Sensors

- Battery State of Charge
- Battery DC Voltage
- Battery DC Current
- Battery DC Power
- Battery AC Power
- AC/DC Conversion Efficiency
- Battery Temperature
- Energy to Battery
- Energy from Battery

## Support

For support, please open an issue in the GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 