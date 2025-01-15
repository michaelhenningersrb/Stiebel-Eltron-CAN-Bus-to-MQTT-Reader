#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
can_reader.py

This script reads CAN messages (socketcan) from the `can0` interface,
determines an "Elster" index from each message, and interprets the data
using an external table (elster_table.py).

Additionally, it publishes interpreted values to an MQTT broker,
but only if the telegram is of type 'answer' (telegram_type == 2).

Command-line parameters:
    --mqtt-server  : Hostname/IP of the MQTT broker (default: localhost)
    --mqtt-port    : MQTT broker port (default: 1883)
    --mqtt-user    : MQTT username (optional)
    --mqtt-pass    : MQTT password (optional)
    --mqtt-prefix  : Prefix for MQTT topics (default: 'elster/')
    --verbosity    : Console logging level (0=none, 1=minimal, 2=standard, 3=debug)
                     By default, it is set to 2.

Examples:
    python can_reader.py --mqtt-server 192.168.1.50 --mqtt-user myuser --mqtt-pass secret --verbosity 2
    python can_reader.py --verbosity 1
    python can_reader.py --mqtt-prefix "home/elster/" --verbosity 3

Verbosity levels:
    0: No logs except critical errors
    1: Minimal logs (e.g., partial info)
    2: Standard logs
    3: Very detailed/verbose logs
"""

import sys
import argparse
import can
import paho.mqtt.client as mqtt

# We assume elster_table.py provides:
#   lookup_elster_index(index) -> returns a dictionary with "Name", "EnglishName", "Type", ...
#   interpret_elster_value(raw_value, elster_type) -> returns an interpreted numeric/string value.
from elster_table import (
    lookup_elster_index,
    interpret_elster_value
)

def parse_telegram(msg, mqtt_client=None, mqtt_prefix="elster/", verbosity=2):
    """
    Parse a CAN message (msg) to:
      - Extract the Elster index from specific bytes (3+4).
      - Lookup the index in our Elster table.
      - Interpret the raw data with the correct type.

    If the telegram is recognized as an 'answer' (telegram_type == 2),
    publish it to MQTT (if mqtt_client is provided).

    :param msg: can.Message object received from the socketcan interface
    :param mqtt_client: paho MQTT client instance (or None if not in use)
    :param mqtt_prefix: string prefix for MQTT topics
    :param verbosity: integer (0..3) controlling console output detail
    """
    data = msg.data

    # Check minimal length
    if len(data) < 5:
        if verbosity >= 2:
            print(f"[Invalid] Too few bytes: {data.hex()}")
        return

    # The Elster index is composed of bytes 3+4 (big-endian).
    elster_index = (data[3] << 8) | data[4]

    # Optional raw value from bytes 5+6, if available
    raw_val = 0
    if len(data) >= 7:
        raw_val = (data[5] << 8) | data[6]

    # Telegram type: lower nibble of byte 0
    telegram_type = data[0] & 0x0F
    address_high = data[0] & 0xF0
    address_low = data[1]
    can_id = (address_high * 8) + address_low

    # Lookup index in the Elster table
    entry = lookup_elster_index(elster_index)
    elster_name = entry["Name"]
    elster_type = entry["Type"]
    english_name = entry.get("EnglishName", elster_name)

    # Interpret the raw value
    interpreted_value = interpret_elster_value(raw_val, elster_type)

    # Map telegram_type to a label
    type_dict = {1: "[Request]", 2: "[Answer]", 9: "[Change]"}
    type_str = type_dict.get(telegram_type, "[Unknown]")

    # Logging output based on verbosity
    if verbosity >= 2:
        print(f"{type_str} CAN-ID: {can_id:03X} | "
              f"Elster-Index: 0x{elster_index:04X} ({elster_name}) | "
              f"Value: {interpreted_value} | Type: {elster_type}")

    elif verbosity == 1 and telegram_type == 2:
        # For minimal logging, only log "answers" briefly
        print(f"Ans 0x{elster_index:04X} -> {interpreted_value}")

    if verbosity >= 3:
        # Extra debug info
        print(f"  [DEBUG] Raw message: {msg}")
        print(f"  [DEBUG] data(hex): {data.hex()}")
        print(f"  [DEBUG] raw_val: {raw_val}")

    # Only publish if telegram_type == 2 (Answer)
    if mqtt_client is not None and telegram_type == 2:
        topic = f"{mqtt_prefix}{english_name}"
        mqtt_client.publish(topic, str(interpreted_value))

def main():
    """
    Main function:
      - Parse command-line arguments
      - Establish MQTT connection
      - Read from CAN interface (socketcan)
      - For each message, parse and possibly publish to MQTT.
    """
    parser = argparse.ArgumentParser(
        description="Reads CAN messages from 'can0' and publishes them via MQTT, only if type is 'Answer'."
    )
    parser.add_argument("--mqtt-server", default="localhost", help="MQTT broker hostname/IP")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-user", default=None, help="MQTT username (optional)")
    parser.add_argument("--mqtt-pass", default=None, help="MQTT password (optional)")
    parser.add_argument("--mqtt-prefix", default="elster/", help="MQTT topic prefix")
    parser.add_argument("--verbosity", type=int, default=2,
                        help="Console output detail level (0=none, 1=minimal, 2=standard, 3=debug)")

    args = parser.parse_args()

    # Minimal start-up message if verbosity >= 1
    if args.verbosity >= 1:
        print("Starting CAN reader & Elster interpretation ...")
        print("=" * 70)
        print(f"MQTT server: {args.mqtt_server}:{args.mqtt_port}, user={args.mqtt_user}")

    # Set up MQTT client
    mqtt_client = mqtt.Client()
    if args.mqtt_user and args.mqtt_pass:
        mqtt_client.username_pw_set(args.mqtt_user, args.mqtt_pass)

    try:
        mqtt_client.connect(args.mqtt_server, args.mqtt_port, 60)
        mqtt_client.loop_start()  # runs in the background
    except Exception as e:
        if args.verbosity >= 1:
            print(f"[MQTT] Could not connect: {e}")
            print("Continuing without MQTT ...")
        mqtt_client = None

    # Set up the SocketCAN interface (e.g., "can0")
    try:
        bus = can.interface.Bus(channel='can0', bustype='socketcan')

        while True:
            msg = bus.recv(timeout=1)
            if msg is None:
                continue

            parse_telegram(msg,
                           mqtt_client=mqtt_client,
                           mqtt_prefix=args.mqtt_prefix,
                           verbosity=args.verbosity)
    except KeyboardInterrupt:
        if args.verbosity >= 1:
            print("\nInterrupted by user (Ctrl+C).")

    finally:
        if args.verbosity >= 1:
            print("\nExiting.")
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()

if __name__ == "__main__":
    main()
