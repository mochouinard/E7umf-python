# E7umf Python Library for UHF-U1-CU-71 RFID Reader

![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)
![Python: 3.6+](https://img.shields.io/badge/Python-3.6%2B-blue.svg)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux-green.svg)

This Python library, `E7umf.py`, provides a native interface to control the [UHF-U1-CU-71 RFID reader](https://en1.fongwah.com/products/UHF-U1-CU-71%20reader) from Fongwah Technology Co., Ltd. Developed by Marc O. Chouinard, it was created by reverse-engineering the USB communication protocol of the “UHF Reader Config V1.1.exe” application in the manufacturer’s SDK, which likely uses the proprietary E7umf library. The library adapts the E7umf interface (`uhf.h`) to Python with AI assistance, ensuring compatibility with the official E7umf documentation. Primarily tested on Linux, it offers a cross-platform solution, though Windows support is untested.

## Table of Contents

- [Introduction](#introduction)
- [Disclaimer](#disclaimer)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Usage Notes](#usage-notes)
- [Naming Rationale](#naming-rationale)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Contributing](#contributing)

## Introduction

This Python library supports key RFID operations, including reading, writing, and securing tags, with function names and usage mirroring the C-style conventions of the E7umf SDK for compatibility. A more Pythonic implementation (e.g., object-oriented design, snake_case methods) is a potential future enhancement. Write operations are fully accessible in the library, but the test script disables them by default to prevent accidental tag modifications, requiring explicit activation via a `--write` flag.

Marc O. Chouinard, a Linux user and open-source advocate, received the UHF-U1-CU-71 reader for free for testing and developed this library to provide an open-source alternative to the proprietary SDK, sharing it with the community. Users are encouraged to consult the *USB E7umf Library Function Manual* in the Fongwah SDK for complete documentation of the underlying API.

## Disclaimer

**Marc O. Chouinard is not responsible for any damages, data loss, or other consequences arising from the use of this library.** Users assume all risks associated with operating the UHF-U1-CU-71 reader and modifying RFID tags, particularly with write operations that may permanently alter or lock tags. Always test with disposable tags and verify functionality before applying critical changes.

## Features

- **Connect/Disconnect**: Establish and terminate USB connections to the RFID reader.
- **Read/Write Tags**: Access tag memory banks (EPC, TID, USER, reserved) for reading and writing.
- **Reader Control**: Manage the reader’s buzzer and LEDs for user feedback.
- **Security Operations**: Set access passwords and lock tag memory banks for enhanced security.
- **Inventory Scan**: Detect and read EPCs from multiple tags in the reader’s field.

## Requirements

- **Python**: 3.6 or higher
- **PyUSB**: `pip install pyusb`
- **libusb**: e.g., `sudo apt-get install libusb-1.0-0-dev` (Ubuntu)
- **Operating System**: Tested on Linux; Windows support is possible but untested
- **Hardware**: UHF-U1-CU-71 RFID reader connected via USB

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/mochouinard/E7umf-python
cd E7umf-python
```

### 2. Install Dependencies
```bash
pip install pyusb
```

### 3. Configure USB Permissions (Linux)
To run without `sudo`, create a udev rule for the RFID reader (Vendor ID: 0x0e6a, Product ID: 0x0317):
```bash
sudo nano /etc/udev/rules.d/50-uhf-rfid.rules
```
Add, replacing `your-username` with your Linux username (e.g., `marc`):
```plaintext
SUBSYSTEM=="usb", ATTRS{idVendor}=="0e6a", ATTRS{idProduct}=="0317", MODE="0666", OWNER="your-username"
```
Reload rules:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 4. Windows Setup (Untested)
Install the libusb driver using [Zadig](https://zadig.akeo.ie/):
- Connect the UHF-U1-CU-71 reader.
- In Zadig, select the device (Vendor ID: 0x0e6a, Product ID: 0x0317).
- Install the libusb driver.
*Note*: Windows compatibility requires testing.

## Quick Start

Read an EPC tag with this example:

```python
from E7umf import uhf_connect, uhf_disconnect, uhf_read

# Connect to the reader
icdev = uhf_connect(100, 115200)
if icdev <= 0:
    print("Failed to connect!")
    exit(1)

# Read EPC from a tag
pData = bytearray(50)
st = uhf_read(icdev, 1, 0, 8, pData)
if st == 0:
    print(f"EPC: {pData[:32].hex()}")
else:
    print(f"Read failed, error code: {st}")

# Disconnect
uhf_disconnect(icdev)
```

Run the test script to demo all functions:
```bash
python E7umf.py
```
Enable write operations (use with caution):
```bash
python E7umf.py --write
```

**Critical Warning**: The `--write` flag enables write operations (`uhf_setAccessPassword`, `uhf_lockMemory`, `uhf_write`) in the test script, using a hard-coded password (e.g., `0x123456789ABCDEF0`) without user input. This can *permanently alter or lock RFID tags*, potentially rendering them unusable. **Do not use `--write` unless you understand the risks, have tested with disposable tags, and are prepared for irreversible changes like permalocking.** Refer to the *USB E7umf Library Function Manual* in the SDK for details.

## API Reference

The library mirrors the E7umf SDK’s C-style API (e.g., `uhf_connect`, `uhf_read`) for compatibility with the *USB E7umf Library Function Manual*. A Pythonic redesign (e.g., object-oriented, snake_case methods) is a future goal. Below is each function’s details.

| Function | Description | Parameters | Return Value |
|----------|-------------|------------|--------------|
| `uhf_connect(port, baud)` | Connects to the reader via USB. | `port`: 100 (USB)<br>`baud`: Ignored | >0 (handle) on success, negative on failure (e.g., -32: device not found, -1: error) |
| `uhf_disconnect(icdev)` | Disconnects from the reader. | `icdev`: Device handle | 0 on success, error (e.g., 32: invalid handle, -13: USB error) |
| `uhf_read(icdev, infoType, address, rlen, pData)` | Reads a tag’s memory bank. | `icdev`: Handle<br>`infoType`: Bank (1: EPC, 2: TID, 3: USER, 4: reserved)<br>`address`: Start address (words)<br>`rlen`: Words to read<br>`pData`: Buffer (min rlen*4 bytes) | 0 on success, error (e.g., -2: invalid infoType, -6: comm failure) |
| `uhf_write(icdev, infoType, address, wlen, pData)` | Writes to a tag’s memory bank. | `icdev`: Handle<br>`infoType`: Bank<br>`address`: Start address (words)<br>`wlen`: Words to write<br>`pData`: Data (wlen*4 bytes) | 0 on success, error |
| `uhf_action(icdev, action, time)` | Controls buzzer/LEDs. | `icdev`: Handle<br>`action`: 1 (beep), 2 (red LED), 4 (green LED), 8 (yellow LED), or combo<br>`time`: Duration (10ms units) | 0 on success, error |
| `uhf_setAccessPassword(icdev, AccessPassword)` | Sets tag’s access password. | `icdev`: Handle<br>`AccessPassword`: 8-byte binary array | 0 on success, error |
| `uhf_lockMemory(icdev, lockSetting)` | Locks tag memory/passwords. | `icdev`: Handle<br>`lockSetting`: 6-byte ASCII (e.g., “002002”) | 0 on success, error |
| `uhf_inventory(icdev, tagCount, dataLen, pData)` | Scans multiple tags’ EPCs. | `icdev`: Handle<br>`tagCount`: 2-byte buffer<br>`dataLen`: 2-byte buffer<br>`pData`: EPC data buffer | 0 on success, error |

### Common Error Codes
| Code | Description |
|------|-------------|
| 0    | Success |
| -2   | Invalid parameter |
| -6   | Communication failure/invalid response |
| -13  | USB error |
| 32   | Invalid/unconnected handle |
| 4, 160 | Inventory errors (e.g., no tags, protocol issue) |

### Example: Password and Memory Lock
```python
from E7umf import uhf_connect, uhf_disconnect, uhf_setAccessPassword, uhf_lockMemory

icdev = uhf_connect(100, 115200)
if icdev <= 0:
    print("Failed to connect!")
    exit(1)

# Set access password
password = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
st = uhf_setAccessPassword(icdev, password)
print(f"Password set: {password.hex()}" if st == 0 else f"Password set failed, error: {st}")

# Lock EPC memory (password-protected write)
lockSetting = bytes([0x30, 0x32, 0x30, 0x30, 0x30, 0x32])  # "020002"
st = uhf_lockMemory(icdev, lockSetting)
print("EPC locked: writable with password" if st == 0 else f"Lock failed, error: {st}")

uhf_disconnect(icdev)
```

**Warning**: Hard-coded values in write operations can *permanently modify tags*. Test with disposable tags and review the SDK manual.

## Usage Notes

- **Write Operations**: The library allows unrestricted write functions (`uhf_setAccessPassword`, `uhf_lockMemory`, `uhf_write`). The test script disables them unless `--write` is used, but the flag applies hard-coded values (e.g., password `0x123456789ABCDEF0`, lock setting `002002`) without user input. **Use write functions or `--write` with extreme caution, as they risk irreversible tag changes, including permalocking. Test with non-critical tags and consult the *USB E7umf Library Function Manual*.**
- **Serial Support**: Only USB (port=100) is supported. Serial port support (e.g., COM1) is unimplemented but feasible with a serial device. Contributions are welcome.
- **Tag Selection**: Functions like `uhf_setAccessPassword` and `uhf_lockMemory` target one tag. Multiple tags may cause unpredictable results. Use `uhf_inventory` or ensure one tag is in range.
- **Password Format**: Access passwords are 8-byte binary arrays (e.g., `0x123456789ABCDEF0`). Some tags may expect ASCII (e.g., `b"12345678"`); test your tags.
- **API Design**: C-style names (e.g., `uhf_connect`) match the E7umf SDK for compatibility. A Pythonic redesign is a future goal.
- **Linux Testing**: Tested on Linux. Windows requires libusb setup and testing.
- **Safety**: Test writes on disposable tags. Verify tag behavior (e.g., default password, lock state). Backup critical data. Avoid permalock until tested.
- **SDK Manual**: The *USB E7umf Library Function Manual* in the SDK provides detailed function specs.

## Naming Rationale

`E7umf.py` reflects the original `E7umf.dll` from the Fongwah SDK, aligning with the API’s branding. The repository, `E7umf-python`, indicates its Python focus. Alternative names (e.g., `uhf_rfid.py`, `e7umf.py` lowercase) are valid, but `E7umf.py` maintains SDK consistency. Rename the file and update imports if desired.

## License

Licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.en.html). Redistribute and modify under this license, keeping derivatives open source.

**Note**: The E7umf library, “UHF Reader Config V1.1.exe,” and SDK are proprietary, owned by Fongwah Technology Co., Ltd. This library is an independent implementation via reverse-engineering, not affiliated with Fongwah. Verify legal compliance with the SDK’s terms. Consult a legal expert if unsure.

## Acknowledgements

- **Author**: Marc O. Chouinard ([@mochouinard](https://x.com/mochouinard))
- **Product**: UHF-U1-CU-71 reader provided for free for testing
- **Community**: Thanks to [PyUSB](https://pyusb.github.io/pyusb/) and [Wireshark](https://www.wireshark.org/)

## Contributing

Contributions are welcome! To contribute:
1. Open an [issue](https://github.com/mochouinard/E7umf-python/issues) to discuss ideas.
2. Fork the repository, make changes, and submit a [pull request](https://github.com/mochouinard/E7umf-python/pulls).
3. Follow Python PEP 8 and include tests.

Ideas for contributions:
- Serial port support for COM connections.
- User-configurable passwords in the test script.
- Windows compatibility testing.
- Pythonic interface redesign.
- Multi-tag selection enhancements.
