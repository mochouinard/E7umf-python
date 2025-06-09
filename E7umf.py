# E7umf.py - Python Library for UHF-U1-CU-71 RFID Reader
#
# Description:
#   This Python library provides an interface to control the UHF-U1-CU-71 RFID reader
#   from Fongwah Technology Co., Ltd. It supports connecting via USB, reading/writing
#   tag memory (EPC, TID, USER, reserved), controlling buzzer/LEDs, setting access
#   passwords, locking memory, and scanning multiple EPCs. Reverse-engineered from the
#   proprietary E7umf SDK and "UHF Reader Config V1.1.exe" for compatibility.
#
# Author:
#   Marc O. Chouinard (@mochouinard, https://github.com/mochouinard)
#
# License:
#   GNU General Public License v3.0 (GPL-3.0)
#   See https://www.gnu.org/licenses/gpl-3.0.en.html for details.
#   This is an independent implementation, not affiliated with Fongwah Technology Co., Ltd.
#   Verify compliance with the proprietary E7umf SDK terms.
#
# Requirements:
#   - Python 3.6 or higher
#   - PyUSB (install via: pip install pyusb)
#   - libusb (e.g., sudo apt-get install libusb-1.0-0-dev on Ubuntu)
#   - UHF-U1-CU-71 RFID reader connected via USB
#
# Platform:
#   Tested on Linux; Windows support is possible but untested.
#
# Warning:
#   Use with caution! Write operations (uhf_setAccessPassword, uhf_lockMemory, uhf_write)
#   can permanently alter or lock RFID tags, risking data loss or tag unusability.
#   Test with disposable tags first. Consult the USB E7umf Library Function Manual
#   in the Fongwah SDK for full details. The author is not responsible for damages.
#
# Usage:
#   See README.md and example in this script for guidance. Run 'python E7umf.py --write'
#   to enable write operations in the test script (use with extreme caution).
#
# Repository:
#   https://github.com/mochouinard/E7umf-python
#

import usb.core
import usb.util
import time
import sys
import argparse

# Device constants from USB descriptor
VENDOR_ID = 0x0e6a  # Megawin Technology Co., Ltd
PRODUCT_ID = 0x0317  # RFID Reader
ENDPOINT_OUT = 0x03  # EP 3 OUT
ENDPOINT_IN = 0x82   # EP 2 IN
INTERFACE = 1        # Target Interface 1 (Custom HID)

# Global variables
usb_device = None
debug_mode = False

def toHexChar(value):
    """
    Convert number to hex char, per C code.
    """
    return (value + 55) if value >= 10 else (value + 48)

def binaryToHex(source, length):
    """
    Convert binary data to hex string, per C code.
    """
    if length <= 0 or not source:
        return None
    result = bytearray(length * 2)
    for i in range(length):
        value = source[i]
        result[i * 2] = toHexChar(value >> 4)
        result[i * 2 + 1] = toHexChar(value & 0xF)
    return result

def asciiToHex(source, length):
    """
    Convert hex string to binary, per C code.
    """
    if length <= 0 or not source or len(source) < length * 2:
        return None
    result = bytearray(length)
    for i in range(length):
        try:
            high = source[2 * i]
            low = source[2 * i + 1]
            if not (48 <= high <= 57 or 65 <= high <= 70 or 97 <= high <= 102) or \
               not (48 <= low <= 57 or 65 <= low <= 70 or 97 <= low <= 102):
                return None
            result[i] = int(chr(high) + chr(low), 16)
        except ValueError:
            return None
    return result

def uhf_connect(port, baud):
    """
    Connect reader.
    Parameters:
        port: 100 for USB, 0 for COM1, 1 for COM2, 2 for COM3, etc.
        baud: Baud rate (9600-115200), relevant for serial but ignored for USB
    Return Value:
        >0 is device handle, otherwise connect failed
    """
    global usb_device
    try:
        if port != 100:  # Only USB supported in this implementation
            print("Error: Only USB (port=100) is supported in this implementation")
            return -1
        usb_device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if usb_device is None:
            print("Error: Device not found. Ensure the RFID Reader is connected.")
            return -32
        for config in usb_device:
            for intf in config:
                if usb_device.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        usb_device.detach_kernel_driver(intf.bInterfaceNumber)
                    except usb.core.USBError as e:
                        print(f"Error: Could not detach kernel driver: {e}")
                        return -1
        try:
            usb_device.set_configuration()
        except usb.core.USBError as e:
            print(f"Error: Error setting configuration: {e}")
            return -1
        try:
            usb.util.claim_interface(usb_device, INTERFACE)
        except usb.core.USBError as e:
            print(f"Error: Error claiming interface {INTERFACE}: {e}")
            return -1
        if debug_mode:
            print("Device connected successfully")
        return id(usb_device)  # Return a unique handle (object ID)
    except Exception as e:
        print(f"Error connecting device: {e}")
        return -1

def uhf_disconnect(icdev):
    """
    Disconnect reader.
    Parameters:
        icdev: Handle of reader
    Return Value:
        =0 correct, other error
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        usb.util.release_interface(usb_device, INTERFACE)
        usb.util.dispose_resources(usb_device)
        if debug_mode:
            print("Device disconnected successfully")
        usb_device = None
        return 0
    except usb.core.USBError as e:
        print(f"Error disconnecting device: {e}")
        return -13

def send_command(device, data):
    """
    Internal function to send USB command.
    """
    if device is None:
        print("Error: Device not connected")
        return False
    try:
        bytes_written = 0
        while bytes_written < len(data):
            chunk = data[bytes_written:bytes_written + 64]
            if len(data) > 64 and bytes_written + 64 < len(data):
                chunk = b'\x82' + chunk[1:]  # Continuation marker
            elif len(data) > 64:
                chunk = b'\x02' + chunk[1:]  # End marker
            written = device.write(ENDPOINT_OUT, chunk, timeout=2000)
            if debug_mode:
                print(f"Sent command chunk: {chunk.hex()} (Bytes written: {written})")
            bytes_written += 64
        return True
    except usb.core.USBError as e:
        print(f"Error sending command: {e}")
        return False

def read_response(device, timeout=2000):
    """
    Internal function to read USB response.
    """
    if device is None:
        print("Error: Device not connected")
        return None
    try:
        response = bytearray()
        start_time = time.time()
        while True:
            chunk = device.read(ENDPOINT_IN, 64, timeout=timeout)
            chunk_bytes = chunk.tobytes()
            response.extend(chunk_bytes)
            if debug_mode:
                print(f"Received response chunk: {chunk_bytes.hex()} (Length: {len(chunk_bytes)})")
            if chunk_bytes[0] != 63 or (time.time() - start_time) * 1000 > timeout:
                break
            if len(chunk_bytes) < 64:
                break
        if debug_mode:
            print(f"Full response: {response.hex()} (Length: {len(response)})")
        if len(response) == 0:
            return None
        return response
    except usb.core.USBError as e:
        if e.errno == 110:
            if debug_mode:
                print("No data received within timeout period")
            return None
        print(f"Error reading response: {e}")
        return None

def uhf_read(icdev, infoType, address, rlen, pData):
    """
    Read data from UHF tag.
    Parameters:
        icdev: Handle of reader
        infoType: 1: EPC, 2: TID, 3: USER, 4: reserved
        address: Start address
        rlen: Length of the data to read (will get rlen*4 bytes data)
        pData: Buffer to store data read
    Return Value:
        =0 read data correctly, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        if infoType not in [1, 2, 3, 4]:
            print("Error: Invalid infoType, must be 1 (EPC), 2 (TID), 3 (USER), or 4 (reserved)")
            return -2
        command = bytearray(256)
        command[1] = 2
        command[2:4] = b'AR'
        command[4] = infoType + 48  # ASCII digit
        command[5] = 44  # Comma
        if address >= 0x10:
            command[6] = toHexChar(address >> 4)
            command[7] = toHexChar(address & 0xF)
            command[8] = 44
            command[9] = rlen + 55 if rlen >= 10 else rlen + 48
            command[0] = 9
            command_length = 10
        else:
            command[6] = toHexChar(address)
            command[7] = 44
            command[8] = rlen + 55 if rlen >= 10 else rlen + 48
            command[0] = 8
            command_length = 9
        if send_command(usb_device, command[:command_length]):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 6 and response[4] == ord('R'):
                data_length = min(rlen * 4, len(pData))
                for i in range(data_length):
                    pData[i] = response[5 + i] if 5 + i < len(response) else 0
                if debug_mode:
                    print(f"Read data: {response[5:5+data_length].hex()}")
                return 0
            else:
                print("Error: Invalid or no response for read operation")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_read: {e}")
        return -13

def uhf_write(icdev, infoType, address, wlen, pData):
    """
    Write UHF tag.
    Parameters:
        icdev: Handle of reader
        infoType: 1: EPC, 2: TID, 3: USER, 4: reserved
        address: Start address
        wlen: Length of the data to write (will write wlen*4 bytes data)
        pData: Data for write
    Return Value:
        =0 write data correctly, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        if infoType not in [1, 2, 3, 4]:
            print("Error: Invalid infoType, must be 1 (EPC), 2 (TID), 3 (USER), or 4 (reserved)")
            return -2
        command = bytearray(256)
        command[1] = 2
        command[2:4] = b'AW'
        command[4] = infoType + 48
        command[5] = 44
        if address >= 0x10:
            command[6] = toHexChar(address >> 4)
            command[7] = toHexChar(address & 0xF)
            command[8] = 44
            command[9] = wlen + 55 if wlen >= 10 else wlen + 48
            command[10] = 44
            command[11:11 + wlen * 4] = pData[:wlen * 4]
            command_length = 11 + wlen * 4
        else:
            command[6] = toHexChar(address)
            command[7] = 44
            command[8] = wlen + 55 if wlen >= 10 else wlen + 48
            command[9] = 44
            command[10:10 + wlen * 4] = pData[:wlen * 4]
            command_length = 10 + wlen * 4
        command[0] = command_length - 1
        if send_command(usb_device, command[:command_length]):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 1 and response[0] == 8:
                if debug_mode:
                    print(f"Write data: {pData[:wlen*4].hex()} - Success")
                return 0
            else:
                print("Error: Invalid or no response for write operation")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_write: {e}")
        return -13

def uhf_action(icdev, action, time):
    """
    Control buzzer and led.
    Parameters:
        icdev: Handle of reader
        action: 1: Beep, 2: Red led on, 4: Green led on, 8: Yellow led on
        time: Unit: 10ms
    Return Value:
        =0 Correct execution, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        if action not in [1, 2, 4, 8] and not (0 < action <= 15):
            print("Error: Invalid action, must be 1 (Beep), 2 (Red led), 4 (Green led), 8 (Yellow led), or combination")
            return -2
        command = bytearray([4, 2, 145, action, time])
        if send_command(usb_device, command):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 4 and response[0] == 3 and response[1] == 2 and response[2] == 145 and response[3] == 0:
                if debug_mode:
                    print(f"Action (beep/led) executed: action={action}, time={time*10}ms")
                return 0
            else:
                print("Error: Invalid or no response for action")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_action: {e}")
        return -13

def uhf_setAccessPassword(icdev, AccessPassword):
    """
    Set Access Password.
    Parameters:
        icdev: Handle of reader
        AccessPassword: Access password of tag (8 bytes, as two 4-byte integers)
    Return Value:
        =0 Correct execution, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        if not isinstance(AccessPassword, (bytes, bytearray)) or len(AccessPassword) != 8:
            print("Error: AccessPassword must be an 8-byte array (two 4-byte integers)")
            return -2
        command = bytearray(12)
        command[0] = 11  # Length
        command[1] = 2   # Protocol marker
        command[2:4] = b'AP'
        command[4:8] = AccessPassword[:4]  # First 4 bytes
        command[8:12] = AccessPassword[4:8]  # Second 4 bytes
        if send_command(usb_device, command):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 5 and response[0] == 4 and response[1] == 2 and response[2] == 65 and response[3] == 0 and response[4] == 80:
                if debug_mode:
                    print(f"Set Access Password: {AccessPassword.hex()} - Success")
                return 0
            else:
                print("Error: Invalid or no response for set access password")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_setAccessPassword: {e}")
        return -13

def uhf_lockMemory(icdev, lockSetting):
    """
    Lock Memory.
    Parameters:
        icdev: Handle of reader
        lockSetting: Lock setting, 6 bytes ASCII character
    Return Value:
        =0 Correct execution, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        if not isinstance(lockSetting, (bytes, bytearray)) or len(lockSetting) != 6:
            print("Error: lockSetting must be a 6-byte ASCII character array")
            return -2
        command = bytearray(11)
        command[0] = 10  # Length
        command[1] = 2   # Protocol marker
        command[2:4] = b'AL'
        command[4:10] = lockSetting  # 6-byte ASCII setting, per PDF
        if send_command(usb_device, command):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 8 and response[0] == 8 and response[4] == 76 and response[6] == 79 and response[7] == 75:
                if debug_mode:
                    print(f"Lock Memory: {lockSetting.hex()} - Success")
                return 0
            else:
                print("Error: Invalid or no response for lock memory")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_lockMemory: {e}")
        return -13

def uhf_inventory(icdev, tagCount, dataLen, pData):
    """
    Multiple EPC reads.
    Parameters:
        icdev: Handle of reader
        tagCount: EPC count read
        dataLen: Length of the pData
        pData: Data read (data1_length(1 byte), EPC1_readcount(1 byte), EPC1(data1_length-1 bytes), ...)
    Return Value:
        =0 read data correctly, <>0 error (absolute value is error code)
    """
    global usb_device
    if usb_device is None or id(usb_device) != icdev:
        print("Error: Invalid or unconnected device handle")
        return 32
    try:
        command = bytearray([3, 2, 85, 0x80])
        if send_command(usb_device, command):
            response = read_response(usb_device, timeout=2000)
            if response and len(response) >= 5:
                count = response[4]
                tagCount[0] = count & 0xFF
                tagCount[1] = (count >> 8) & 0xFF
                if count == 0:
                    dataLen[0] = 0
                    dataLen[1] = 0
                    if debug_mode:
                        print("Inventory: 0 tags detected")
                    return 0
                command[3] = 145  # 0x91
                current_offset = 0
                for i in range(count):
                    result = send_command(usb_device, command)
                    if not result:
                        print("Error: Failed to send inventory follow-up command")
                        return -6
                    response = read_response(usb_device, timeout=2000)
                    if not response:
                        return -6
                    if response[0] == 4:
                        return 4
                    if response[1] != 160:
                        return 160
                    byte_count = 2 * response[5] - 8
                    last_byte = response[response[0] - 1]
                    if current_offset < len(pData):
                        pData[current_offset] = byte_count + 1
                    if current_offset + 1 < len(pData):
                        pData[current_offset + 1] = last_byte
                    hex_data = binaryToHex(response, byte_count)
                    if hex_data:
                        data_length = min(byte_count, len(pData) - current_offset - 2)
                        for j in range(data_length):
                            pData[current_offset + 2 + j] = hex_data[j] if j < len(hex_data) else 0
                    current_offset += byte_count + 2
                dataLen[0] = current_offset & 0xFF
                dataLen[1] = (current_offset >> 8) & 0xFF
                if debug_mode:
                    print(f"Inventory: {count} tags, data length: {current_offset}, data: {pData[:current_offset].hex()}")
                return 0
            else:
                print("Error: Invalid or no response for inventory")
                return -6
        return -6
    except Exception as e:
        print(f"Error in uhf_inventory: {e}")
        return -13

# Test script for standalone execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UHF RFID Library Test Script")
    parser.add_argument('--write', action='store_true', help="Enable write operations (setAccessPassword, lockMemory, write)")
    args = parser.parse_args()

    print("UHF RFID Library Test Script")
    print("---------------------------")
    print(f"Write operations {'enabled' if args.write else 'disabled'} (use --write to enable)")

    # Enable debug mode for testing
    debug_mode = True

    # Connect to device
    icdev = uhf_connect(100, 115200)
    if icdev <= 0:
        print("Failed to connect. Exiting.")
        sys.exit(1)
    print(f"Connected with handle: {icdev}")

    # Test uhf_action (beep and green LED for 500ms)
    st = uhf_action(icdev, 1 | 4, 50)
    print(f"uhf_action (beep + green LED) result: {st}")
    time.sleep(1)

    if args.write:
        # Test uhf_setAccessPassword
        password = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
        st = uhf_setAccessPassword(icdev, password)
        print(f"uhf_setAccessPassword result: {st}")
        time.sleep(0.5)

        # Test uhf_lockMemory
        lockSetting = bytes([0x30, 0x30, 0x32, 0x30, 0x30, 0x32])  # Lock user bank, per PDF
        st = uhf_lockMemory(icdev, lockSetting)
        print(f"uhf_lockMemory result: {st}")
        time.sleep(0.5)
    else:
        print("Skipping uhf_setAccessPassword (write operation disabled)")
        print("Skipping uhf_lockMemory (write operation disabled)")

    # Test uhf_inventory
    tagCount = bytearray(2)
    dataLen = bytearray(2)
    pData = bytearray(50)
    print("Starting inventory scan... (5 seconds)")
    start_time = time.time()
    while time.time() - start_time < 5:
        st = uhf_inventory(icdev, tagCount, dataLen, pData)
        if st == 0:
            count = tagCount[0] + (tagCount[1] << 8)
            length = dataLen[0] + (dataLen[1] << 8)
            print(f"uhf_inventory result: {st}, Tags: {count}, Data length: {length}")
            if count > 0:
                offset = 0
                for i in range(count):
                    if offset + 2 > length:
                        break
                    epc_len = pData[offset]
                    epc_count = pData[offset + 1]
                    epc = pData[offset + 2:offset + epc_len + 1]
                    print(f"Tag {i + 1}: EPC Length: {epc_len}, Read Count: {epc_count}, EPC: {epc.hex()}")
                    offset += epc_len + 1
        time.sleep(0.5)

    # Test uhf_read (EPC, address 0, length 8)
    readData = bytearray(50)
    st = uhf_read(icdev, 1, 0, 8, readData)
    print(f"uhf_read (EPC) result: {st}, Data: {readData[:32].hex()}")
    time.sleep(0.5)

    if args.write:
        # Test uhf_write (EPC, address 2, length 6)
        writeData = bytearray(50)
        for i in range(50):
            writeData[i] = 0x35
        st = uhf_write(icdev, 1, 2, 6, writeData)
        print(f"uhf_write (EPC) result: {st}")
        time.sleep(0.5)
    else:
        print("Skipping uhf_write (write operation disabled)")

    # Disconnect
    st = uhf_disconnect(icdev)
    print(f"uhf_disconnect result: {st}")
    print("Test complete.")
