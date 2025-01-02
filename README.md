# TimeFlip 1 Client

A Python client for the TimeFlip device that helps track time using a [Bluetooth Low Energy](https://en.wikipedia.org/wiki/Bluetooth_Low_Energy) connection. TimeFlip is a physical time-tracking device in the shape of a polygon where each face represents a different activity.

I have bought my TimeFlip1 ~5-6 years ago. They have released the TimeFlip2 and dropped the support for TimeFlip1. Hence I started searching for open-source implementations and came across with the [official communication protocol](https://github.com/DI-GROUP/TimeFlip.Docs/blob/master/Hardware/BLE_device_commutication_protocol_v3.0_en.md) and the repo [pytimefliplib](https://github.com/pierre-24/pytimefliplib). 

With the inspiration, I have implemented this library and using it in the [CLI](WIP) tool I've built.

## Installation

WIP

## Usage Examples

```python
import asyncio
from bleak import BleakScanner
from timeflipv1client.timeflip1client import Timeflip1Client

async def main():
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: ad.local_name == "TimeFlip", 10
    )
    if device is None:
        logger.error("could not find device with name '%s'", name)
        raise Exception("Device could not found")
    
    async with Timeflip1Client(device) as client:
        await client.login()
        status = await client.get_status()
        battery_level = await client.battery_level()
        calibration_version = await client.get_current_calibration_version()
        print(
            f"""
                Status of the device {name}: 
                    Batter level: \033[1m{battery_level}\033[0m
                    Locked: \033[1m{status["locked"]}\033[0m
                    Paused: \033[1m{status["paused"]}\033[0m
                    Auto pause time: \033[1m{status["auto_pause_time"]} minutes\033[0m
                    Current calibration version: \033[1m{calibration_version}\033[0m
            """
        )

# Run the async function
asyncio.run(main())
```

## Requirements
- Python 3.13+
- Bluetooth LE support
- bluepy (Linux) or bleak (Windows/MacOS)

## License
MIT