# USB Communication Protocol for UHF-U1-CU-71 RFID Reader

## Disclaimer

This document was developed through reverse engineering by analyzing USB communication between the UHF-U1-CU-71 RFID reader and the “UHF Reader Config V1.1.exe” application from the Fongwah Technology Co., Ltd. SDK, using Wireshark USB packet captures and insights from the *USB E7umf Library Function Manual*. While effort has been made to ensure accuracy, there is a possibility of errors or incomplete details due to the nature of reverse engineering. We welcome any feedback, corrections, or updates to refine and enhance the accuracy of this protocol description.

## Introduction

This document details the USB communication protocol for the UHF-U1-CU-71 RFID reader from Fongwah Technology Co., Ltd. The protocol was reverse-engineered by analyzing the USB communication of the “UHF Reader Config V1.1.exe” application included in the manufacturer’s SDK, using Wireshark’s USB packet capture. The reader operates as a USB Human Interface Device (HID) with specific endpoints for sending commands and receiving responses, enabling operations such as reading/writing tags, controlling the reader, and securing tag memory.

The protocol uses a custom HID interface over USB, with commands sent to the OUT endpoint and responses received from the IN endpoint. Commands are structured with a report ID, command type, and parameters, often in ASCII format, while responses include status indicators, echoed commands, and data. All messages are transmitted in 64-byte packets, with multi-packet messages using continuation markers. This document provides a comprehensive description of each operation, including bitfield mappings and detailed encoding/decoding instructions, without referencing implementation code.

Users are encouraged to consult the *USB E7umf Library Function Manual* in the Fongwah SDK for additional context on command parameters, error codes, and RFID-specific behaviors.

## Table of Contents

- [Introduction](#introduction)
- [USB Device Configuration](#usb-device-configuration)
- [General Protocol Structure](#general-protocol-structure)
  - [Command Structure](#command-structure)
  - [Response Structure](#response-structure)
  - [Multi-Packet Messages](#multi-packet-messages)
- [Command and Response Details](#command-and-response-details)
  - [1. Connect/Disconnect](#1-connectdisconnect)
  - [2. Read Tag Data](#2-read-tag-data)
  - [3. Write Tag Data](#3-write-tag-data)
  - [4. Control Buzzer and LEDs](#4-control-buzzer-and-leds)
  - [5. Set Access Password](#5-set-access-password)
  - [6. Lock Memory](#6-lock-memory)
  - [7. Inventory Scan](#7-inventory-scan)
  - [8. Get USB Settings](#8-get-usb-settings)
  - [9. Set USB Settings](#9-set-usb-settings)
- [Additional Notes](#additional-notes)
  - [Tag Selection](#tag-selection)
  - [Error Handling](#error-handling)
  - [Timeouts](#timeouts)
  - [Data Formats](#data-formats)
  - [SDK Reference](#sdk-reference)

## USB Device Configuration

The UHF-U1-CU-71 reader is configured as a USB HID device with the following properties:

- **Vendor ID**: 0x0e6a (Megawin Technology Co., Ltd.)
- **Product ID**: 0x0317 (RFID Reader)
- **Interface**: Custom HID (Interface 1)
- **Endpoints**:
  - **OUT Endpoint**: 0x03 (EP 3 OUT) – Host sends commands to the reader.
  - **IN Endpoint**: 0x82 (EP 2 IN) – Host receives responses from the reader.
- **Packet Size**: 64 bytes (fixed for HID transfers)
- **Timeout**: Typically 2000ms for commands and responses

### Setup Process
- The host must claim Interface 1 and detach any kernel drivers (e.g., on Linux) to establish communication.
- USB control transfers configure the device, selecting the active configuration and interface.
- No explicit “connect” command is sent; connection is implicit upon successful USB setup.
- Disconnection involves releasing Interface 1 and disposing of USB resources, without a specific command.

## General Protocol Structure

The protocol uses 64-byte packets for all USB HID communication, with commands sent to the OUT endpoint (0x03) and responses received from the IN endpoint (0x82). Commands and responses follow structured formats, often incorporating ASCII characters for command types and parameters.

### Command Structure
Commands are 64-byte packets with the following general format:

- **Byte 0**: Report ID or continuation marker
  - Common report IDs: 0x02 (default), 0x03 (buzzer/LED, inventory), 0x04 (get USB settings), 0x06 (set USB settings), 0x08 (read/write/security).
  - Continuation marker: 0x82 for multi-packet messages, 0x02 for the final packet.
- **Byte 1**: Protocol marker, typically 0x02, or command-specific identifier (e.g., 0x41 for read/write/security).
- **Bytes 2–N**: Command type and parameters
  - Command type: Often ASCII (e.g., 0x52 ‘R’ for read, 0x57 ‘W’ for write).
  - Parameters: ASCII digits/hex (e.g., bank, address, length) or binary (e.g., password).
- **Remaining Bytes**: Padded with 0x00 to 64 bytes, unless part of a multi-packet message.

### Response Structure
Responses are 64-byte packets (or multiple) with:

- **Byte 0**: Response length (e.g., 0x06, 0x08, 0x14, 0x23) or continuation marker (0x3F for additional data).
- **Byte 1**: Protocol marker, typically 0x02, echoing the command.
- **Bytes 2–N**: Status, command echo, and data
  - Status: 0x00 for success, non-zero for errors, or multi-byte status (e.g., inventory).
  - Command echo: Repeats command type (e.g., 0x52 ‘R’, 0x57 ‘W’).
  - Data: ASCII hex (e.g., tag data) or binary (e.g., settings), often followed by “<OK” (0x3C, 0x4F, 0x4B) for success.
- **Remaining Bytes**: Padded with 0x00 or additional data in multi-packet responses.

### Multi-Packet Messages
- **Commands**:
  - For commands >64 bytes, the first packet starts with 0x82, subsequent packets use 0x82, and the final packet uses 0x02.
  - Example: A 128-byte command sends `[0x82, <63 bytes>]`, `[0x02, <65 bytes>]`.
- **Responses**:
  - Responses >64 bytes start with 0x3F (63) in the first packet, indicating more data.
  - The host reads until 0x3F is absent or packets are <64 bytes.
  - Concatenate packets, discarding padding, to reconstruct the full response.

## Command and Response Details

Below are detailed descriptions of each operation’s command and response, including encoding/decoding instructions and bitfield mappings where applicable.

### 1. Connect/Disconnect
- **Purpose**: Establishes or terminates the USB connection.
- **Command**:
  - **Connect**: No explicit command; the host performs USB control transfers:
    - Enumerate the device (Vendor ID: 0x0e6a, Product ID: 0x0317).
    - Select configuration (typically Configuration 1).
    - Claim Interface 1.
    - Detach kernel drivers if needed (e.g., on Linux).
  - **Disconnect**: No command; release Interface 1 and dispose of USB resources.
- **Response**: None; success is indicated by USB stack completion.
- **Decoding**:
  - Monitor USB control transfer status (e.g., libusb’s `libusb_claim_interface` return code).
  - Errors (e.g., device not found, permission denied) are reported by the USB stack.

### 2. Read Tag Data
- **Purpose**: Reads data from a tag’s memory bank (EPC, TID, USER, reserved).
- **Command**:
  - **Report ID**: 0x08
  - **Format**: `[0x08, 0x02, 0x41, 0x52, <bank>, 0x2C, <address>, <address2>, 0x2C, <length>]`
    - Byte 0: 0x08 (report ID)
    - Byte 1: 0x02 (protocol marker)
    - Byte 2: 0x41 (ASCII ‘A’)
    - Byte 3: 0x52 (ASCII ‘R’ for read)
    - Byte 4: Bank (ASCII digit: 0x31 ‘1’ for EPC, 0x32 ‘2’ for TID, 0x33 ‘3’ for USER, 0x34 ‘4’ for reserved)
    - Byte 5: 0x2C (ASCII ‘,’ separator)
    - Bytes 6–7: Start address (1–2 ASCII hex digits, e.g., 0x30 ‘0’ or 0x30 0x32 ‘02’)
    - Byte 8: 0x2C (ASCII ‘,’)
    - Byte 9: Length in words (ASCII digit, e.g., 0x38 ‘8’ for 8 words, 0x41 ‘A’ for 10)
    - Remaining: 0x00 padding
  - **Encoding**:
    - Convert bank to ASCII digit (1–4 → 0x31–0x34).
    - Convert address to 1–2 ASCII hex digits (e.g., 2 → 0x32, 16 → 0x31 0x36).
    - Convert length to ASCII (1–9 → 0x31–0x39, 10 → 0x41, etc.).
    - Example: Read 8 words from EPC, address 0:
      - Bank: 1 → 0x31
      - Address: 0 → 0x30
      - Length: 8 → 0x38
      - Command: `[0x08, 0x02, 0x41, 0x52, 0x31, 0x2C, 0x30, 0x2C, 0x38, <55 bytes 0x00>]`
- **Response**:
  - **Success Format**: `[length, 0x02, 0x41, 0x00, 0x52, <data>]`
    - Byte 0: Length (e.g., 0x08 for no data, 0x14 for 16 bytes, 0x24 for 32 bytes)
    - Bytes 1–2: 0x02, 0x41
    - Byte 3: 0x00 (success)
    - Byte 4: 0x52 (echo ‘R’)
    - Bytes 5+: Data (ASCII hex, 2 bytes per data byte, e.g., 16 bytes → 32 ASCII chars)
  - **Failure Format**: `[0x08, 0x02, 0x41, <error>, 0x52]`
    - Byte 3: Error code (non-zero, e.g., 0x01 for general failure)
  - **Decoding**:
    - Check Byte 3 for 0x00 (success).
    - If successful, extract data from Byte 5:
      - Convert ASCII hex pairs to binary (e.g., 0x31 0x32 → 0x12).
      - Data length is (response length – 5) / 2 bytes.
    - Example: Response `[0x14, 0x02, 0x41, 0x00, 0x52, 0x31, 0x32, 0x33, 0x34, ...]`:
      - Length: 0x14 (20 bytes)
      - Success: Byte 3 = 0x00
      - Data: Bytes 5–20 (16 bytes → 8 bytes binary after ASCII hex conversion)
      - Decode: `0x31 0x32 0x33 0x34` → `0x12 0x34`

### 3. Write Tag Data
- **Purpose**: Writes data to a tag’s memory bank.
- **Command**:
  - **Report ID**: 0x08
  - **Format**: `[0x08, 0x02, 0x41, 0x57, <bank>, 0x2C, <address>, <address2>, 0x2C, <length>, 0x2C, <data>]`
    - Byte 0: 0x08
    - Byte 1: 0x02
    - Byte 2: 0x41
    - Byte 3: 0x57 (ASCII ‘W’)
    - Byte 4: Bank (0x31–0x34)
    - Byte 5: 0x2C
    - Bytes 6–7: Start address (1–2 ASCII hex digits)
    - Byte 8: 0x2C
    - Byte 9: Length in words (ASCII digit)
    - Byte 10: 0x2C
    - Bytes 11+: Data (ASCII hex, 8 bytes per word)
    - Remaining: 0x00 padding or continuation packets
  - **Encoding**:
    - Bank, address, length: As in read command.
    - Data: Convert binary to ASCII hex (1 byte → 2 ASCII chars, e.g., 0x35 → 0x33 0x35).
    - Example: Write 6 words to EPC, address 2, data 0x35 repeated:
      - Bank: 1 → 0x31
      - Address: 2 → 0x30 0x32
      - Length: 6 → 0x36
      - Data: 24 bytes (6 words * 4 bytes) → 48 ASCII hex chars
      - Command: `[0x08, 0x02, 0x41, 0x57, 0x31, 0x2C, 0x30, 0x32, 0x2C, 0x36, 0x2C, 0x33, 0x35, 0x33, 0x35, ...]`
- **Response**:
  - **Success Format**: `[0x08, 0x02, 0x41, 0x00, 0x57, 0x3C, 0x4F, 0x4B]`
    - Bytes 0–4: `[0x08, 0x02, 0x41, 0x00, 0x57]`
    - Bytes 5–7: 0x3C, 0x4F, 0x4B (ASCII “<OK”)
  - **Failure Format**: `[0x08, 0x02, 0x41, <error>, 0x57]`
  - **Decoding**:
    - Check Byte 3 for 0x00.
    - Verify Bytes 5–7 for “<OK” (0x3C, 0x4F, 0x4B).
    - Example: `[0x08, 0x02, 0x41, 0x00, 0x57, 0x3C, 0x4F, 0x4B]` → Success

### 4. Control Buzzer and LEDs
- **Purpose**: Activates the reader’s buzzer or LEDs (red, green, yellow).
- **Command**:
  - **Report ID**: 0x03
  - **Format**: `[0x03, 0x02, 0x55, <action>, <time>]`
    - Byte 0: 0x03
    - Byte 1: 0x02
    - Byte 2: 0x55 (ASCII ‘U’)
    - Byte 3: Action bitfield (0x01: beep, 0x02: red LED, 0x04: green LED, 0x08: yellow LED, or bitwise OR)
    - Byte 4: Duration (10ms units, e.g., 0x32 for 500ms)
    - Remaining: 0x00 padding
  - **Encoding**:
    - Action: Combine bits (e.g., beep + green LED = 0x01 | 0x04 = 0x05).
    - Time: Integer (1–255 → 10–2550ms).
    - Example: Beep and green LED for 500ms:
      - Action: 0x05
      - Time: 50 (0x32)
      - Command: `[0x03, 0x02, 0x55, 0x05, 0x32, <59 bytes 0x00>]`
- **Response**:
  - **Format**: `[0x06, 0x02, 0x55, <status_high>, <status_low>]`
    - Byte 0: 0x06 (length)
    - Bytes 1–2: 0x02, 0x55
    - Bytes 3–4: Status (2-byte big-endian, 0x0000 for success)
  - **Decoding**:
    - Combine Bytes 3–4 (big-endian) for status (e.g., 0x00 0x00 → 0).
    - Example: `[0x06, 0x02, 0x55, 0x00, 0x00]` → Success

### 5. Set Access Password
- **Purpose**: Sets the tag’s 32-bit access password for securing operations.
- **Command**:
  - **Report ID**: 0x08
  - **Format**: `[0x08, 0x02, 0x41, 0x53, <password>]`
    - Byte 0: 0x08
    - Byte 1: 0x02
    - Byte 2: 0x41
    - Byte 3: 0x53 (ASCII ‘S’)
    - Bytes 4–11: 8-byte binary password (two 4-byte integers)
    - Remaining: 0x00 padding
  - **Encoding**:
    - Password: 8 bytes, treated as two 4-byte integers (little-endian).
    - Example: Password 0x123456789ABCDEF0:
      - Bytes 4–7: 0x12, 0x34, 0x56, 0x78
      - Bytes 8–11: 0x9A, 0xBC, 0xDE, 0xF0
      - Command: `[0x08, 0x02, 0x41, 0x53, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0, <52 bytes 0x00>]`
- **Response**:
  - **Success Format**: `[0x08, 0x02, 0x41, 0x00, 0x53, 0x3C, 0x4F, 0x4B]`
    - Bytes 0–4: `[0x08, 0x02, 0x41, 0x00, 0x53]`
    - Bytes 5–7: “<OK”
  - **Failure Format**: `[0x08, 0x02, 0x41, <error>, 0x53]`
  - **Decoding**:
    - Check Byte 3 for 0x00 and Bytes 5–7 for “<OK”.
    - Example: `[0x08, 0x02, 0x41, 0x00, 0x53, 0x3C, 0x4F, 0x4B]` → Success

### 6. Lock Memory
- **Purpose**: Locks tag memory banks (EPC, TID, USER) or passwords (Kill, Access).
- **Command**:
  - **Report ID**: 0x08
  - **Format**: `[0x08, 0x02, 0x41, 0x4C, <lockSetting>]`
    - Byte 0: 0x08
    - Byte 1: 0x02
    - Byte 2: 0x41
    - Byte 3: 0x4C (ASCII ‘L’)
    - Bytes 4–9: 6-byte ASCII lock setting (e.g., “002002”)
    - Remaining: 0x00 padding
  - **Encoding**:
    - Lock setting: 6 ASCII chars (3 for mask, 3 for action), representing 12-bit fields.
    - Example: Lock User bank (“002002”):
      - Bytes 4–9: 0x30, 0x30, 0x32, 0x30, 0x30, 0x32
      - Command: `[0x08, 0x02, 0x41, 0x4C, 0x30, 0x30, 0x32, 0x30, 0x30, 0x32, <54 bytes 0x00>]`
  - **Bitfield Mapping**:
    - **Mask Field** (Bytes 4–6, ASCII “002” → 0x002):
      - 12 bits, specifying which memory/passwords to apply the action.
      - | Bit | 11–10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
        |-----|-------|---|---|---|---|---|---|---|---|---|---|
        | Field | Reserved | Kill Password Skip/Write | Access Password Skip/Write | EPC Skip/Write | TID Skip/Write | User Skip/Write |
        | Value | 00 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 |
      - 0: Ignore action (retain current lock).
      - 1: Apply action.
      - Example: “002” (0x002) → `000000000010` (apply action to User bank only, bit 1).
    - **Action Field** (Bytes 7–9, ASCII “002” → 0x002):
      - 12 bits, defining lock behavior.
      - | Bit | 11–10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
        |-----|-------|---|---|---|---|---|---|---|---|---|---|
        | Field | Reserved | Kill Password Read/Write | Kill Permalock | Access Password Read/Write | Access Permalock | EPC Write | EPC Permalock | TID Write | TID Permalock | User Write | User Permalock |
        | Value | 00 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 |
      - Memory (EPC, TID, User):
        - Write=0, Permalock=0: Writable.
        - Write=0, Permalock=1: Permanently writable.
        - Write=1, Permalock=0: Writable with password.
        - Write=1, Permalock=1: Not writable (locked).
      - Passwords (Kill, Access):
        - Read/Write=0, Permalock=0: Readable/writable.
        - Read/Write=0, Permalock=1: Permanently readable/writable.
        - Read/Write=1, Permalock=0: Readable/writable with password.
        - Read/Write=1, Permalock=1: Not readable/writable.
      - Example: “002” (0x002) → `000000000010` (User: Write=1, Permalock=0 → writable with password).
  - **Decoding Lock Setting**:
    - Convert Bytes 4–6 (ASCII hex) to 12-bit mask:
      - Read as 3 hex chars (e.g., “002” → 0x002).
      - Convert to binary (e.g., 0x002 → `000000000010`).
      - Check bits for skip/write flags.
    - Convert Bytes 7–9 (ASCII hex) to 12-bit action:
      - Same process (e.g., “002” → User Write=1).
    - Apply mask to action for each field (e.g., User bit 1=1 → apply Write=1, Permalock=0).
- **Response**:
  - **Success Format**: `[0x08, 0x02, 0x41, 0x00, 0x4C, 0x3C, 0x4F, 0x4B]`
    - Bytes 0–4: `[0x08, 0x02, 0x41, 0x00, 0x4C]`
    - Bytes 5–7: “<OK”
  - **Failure Format**: `[0x08, 0x02, 0x41, <error>, 0x4C]`
  - **Decoding**:
    - Check Byte 3 for 0x00 and Bytes 5–7 for “<OK”.

### 7. Inventory Scan
- **Purpose**: Detects and reads EPCs from multiple tags.
- **Initial Command**:
  - **Report ID**: 0x03
  - **Format**: `[0x03, 0x02, 0x55, 0x80]`
    - Byte 0: 0x03
    - Byte 1: 0x02
    - Byte 2: 0x55
    - Byte 3: 0x80 (initial inventory)
    - Remaining: 0x00 padding
  - **Encoding**: Fixed command.
- **Initial Response**:
  - **Format**: `[0x06, 0x02, 0x55, <status_high>, <status_low>]`
    - Byte 0: 0x06
    - Bytes 1–2: 0x02, 0x55
    - Byte 4: Tag count (0x00 if none)
  - **Decoding**:
    - Extract Byte 4 as tag count.
    - Example: `[0x06, 0x02, 0x55, 0x00, 0x02]` → 2 tags
- **Follow-Up Command** (per tag, if count > 0):
  - **Format**: `[0x03, 0x02, 0x55, 0x91]`
    - Byte 3: 0x91 (tag data query)
    - Remaining: 0x00 padding
  - **Encoding**: Fixed command, sent `count` times.
- **Follow-Up Response**:
  - **Format**: `[0x23, 0x02, 0x55, 0x91, <data>]`
    - Byte 0: 0x23 (length, typically 35 bytes)
    - Bytes 1–3: 0x02, 0x55, 0x91
    - Bytes 6–7: Tag count (2-byte big-endian)
    - Bytes 8+: Tag data (format: `<length>, <read_count>, <EPC>`)
      - Length: 1 byte (EPC length + 1)
      - Read count: 1 byte
      - EPC: Variable length (length – 1 bytes)
  - **Decoding**:
    - Verify Byte 0 = 0x23, Bytes 1–3 = 0x02, 0x55, 0x91.
    - Extract tag count: Bytes 6–7 (big-endian, e.g., 0x00 0x02 → 2).
    - For each tag:
      - Read Byte 8+i as length (n).
      - Read Byte 9+i as read count.
      - Read Bytes 10+i to 9+i+n as EPC (n – 1 bytes).
      - Advance i by n + 1 for the next tag.
    - Example: `[0x23, 0x02, 0x55, 0x91, <data>, 0x00, 0x01, 0x0D, 0x01, <12-byte EPC>]`
      - Tag count: 0x0001 (1 tag)
      - Length: 0x0D (13 bytes, 12-byte EPC + 1)
      - Read count: 0x01
      - EPC: 12 bytes (Bytes 10–21)

### 8. Get USB Settings
- **Purpose**: Retrieves the reader’s USB configuration (e.g., keyboard emulation, key delays).
- **Command**:
  - **Report ID**: 0x04
  - **Format**: `[0x04, 0x02, 0x92, 0x00, 0x02]`
    - Byte 0: 0x04
    - Bytes 1–4: 0x02, 0x92, 0x00, 0x02
    - Remaining: 0x00 padding
  - **Encoding**: Fixed command.
- **Response**:
  - **Format**: `[0x07, 0x02, 0x92, 0x00, 0x00, 0x02, <settings>, <key_delay>]`
    - Byte 0: 0x07 (length)
    - Bytes 1–5: 0x02, 0x92, 0x00, 0x00, 0x02
    - Byte 6: Settings bitfield (1 byte)
    - Byte 7: Key delay (10ms units)
  - **Bitfield Mapping (Settings, Byte 6)**:
    - | Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
      |-----|---|---|---|---|---|---|---|---|
      | Field | Add Enter | Add Tab | Reserved | Reserved | Reserved | COM Auto | HID/CDC Auto | USB Keyboard |
      | Value | 0/1 | 0/1 | 0 | 0 | 0 | 0/1 | 0/1 | 0/1 |
    - **Fields**:
      - USB Keyboard: Enables keyboard emulation (tag data sent as keystrokes).
      - HID/CDC Auto: Automatic data sending via HID or CDC interface.
      - COM Auto: Automatic data sending via serial (if supported).
      - Add Enter: Appends Enter key after tag data.
      - Add Tab: Appends Tab key after tag data.
      - Reserved: Must be 0.
  - **Decoding**:
    - Verify Bytes 0–5: `[0x07, 0x02, 0x92, 0x00, 0x00, 0x02]`.
    - Read Byte 6 bitfield:
      - Bit 0: USB Keyboard (1 = enabled)
      - Bit 1: HID/CDC Auto
      - Bit 2: COM Auto
      - Bit 6: Add Tab
      - Bit 7: Add Enter
    - Read Byte 7 as key delay (e.g., 0x05 → 50ms).
    - Example: `[0x07, 0x02, 0x92, 0x00, 0x00, 0x02, 0xC1, 0x05]`
      - Settings: 0xC1 (11000001) → USB Keyboard, Add Enter enabled
      - Key delay: 0x05 (50ms)

### 9. Set USB Settings
- **Purpose**: Configures the reader’s USB settings.
- **Command**:
  - **Report ID**: 0x06
  - **Format**: `[0x06, 0x02, 0x92, 0x00, 0x02, <settings>, <key_delay>]`
    - Byte 0: 0x06
    - Bytes 1–4: 0x02, 0x92, 0x00, 0x02
    - Byte 5: Settings bitfield
    - Byte 6: Key delay (10ms units)
    - Remaining: 0x00 padding
  - **Encoding**:
    - Settings bitfield: As in Get USB Settings.
    - Key delay: Integer (e.g., 0x05 for 50ms).
    - Example: Enable keyboard, 50ms delay:
      - Settings: 0x01 (00000001)
      - Key delay: 0x05
      - Command: `[0x06, 0x02, 0x92, 0x00, 0x02, 0x01, 0x05, <57 bytes 0x00>]`
- **Response**: Same as Get USB Settings, reflecting updated values.
  - **Decoding**: As in Get USB Settings, verify settings match.

## Additional Notes

### Tag Selection
- Commands like read, write, setAccessPassword, and lockMemory target a single tag in the reader’s RF field.
- If multiple tags are present, the reader may select one unpredictably (e.g., based on signal strength or recent inventory).
- Use the inventory scan to identify tags and ensure only one is in range for targeted operations.
- The SDK manual may provide details on tag singulation protocols (e.g., EPC Gen2 anti-collision).

### Error Handling
- Error responses typically include a non-zero error code in Byte 3 (e.g., 0x01 for general failure).
- Common errors:
  - No tag in range
  - Invalid parameters (e.g., bank, address)
  - Communication timeout
  - Tag authentication failure (e.g., wrong password)
- Specific error codes are operation-dependent; consult the SDK manual for mappings.
- Example: Read failure: `[0x08, 0x02, 0x41, 0x01, 0x52]` → Error 0x01

### Timeouts
- A 2000ms timeout is typical for commands and responses, but some operations (e.g., inventory) may respond faster.
- Adjust timeouts based on application needs (e.g., shorter for real-time, longer for reliability).
- Responses arriving after the timeout are discarded, potentially causing incomplete multi-packet data.

### Data Formats
- **ASCII Hex**:
  - Used for read/write parameters (bank, address, length, data).
  - Convert ASCII pairs to binary (e.g., 0x33 0x35 → 0x35).
  - Example: Data “1234” (0x31 0x32 0x33 0x34) → 0x12 0x34.
- **Binary**:
  - Used for passwords, USB settings, and some inventory data.
  - Read directly, respecting endianness (e.g., little-endian for passwords, big-endian for tag counts).
- **Endianness**:
  - Tag counts (inventory): Big-endian (e.g., 0x00 0x02 → 2).
  - Passwords: Little-endian per 4-byte integer.
  - Verify with SDK manual for specific fields.

### SDK Reference
- The *USB E7umf Library Function Manual* in the Fongwah SDK provides detailed specifications for:
  - Memory bank IDs and ranges (EPC, TID, USER, reserved).
  - Lock setting bitfield semantics (EPC Gen2 lock states).
  - Error codes and their operation-specific meanings.
  - Tag selection and singulation.
- Cross-reference this manual to validate parameters and interpret complex responses (e.g., inventory data).

---

This protocol enables full control of the UHF-U1-CU-71 reader via USB HID, supporting all RFID operations provided by the SDK’s configuration software. For further details, refer to the Fongwah SDK’s *USB E7umf Library Function Manual*.
