# Stiebel-Eltron-CAN-Bus-to-MQTT-Reader
Reads Stiebel Eltron Heatpump CAN Bus data and transmits it over MQTT


This project provides a Python script (`can_reader.py`) to read CAN messages from the `socketcan` interface, interpret them using an **Elster**-specific lookup table (`elster_table.py`), and optionally publish the interpreted values to an MQTT broker (only if the messages indicate a response/answer).

## Features

- Reads CAN data from the `can0` interface on Linux-based systems (like a Raspberry Pi).
- Interprets specific data fields called **Elster indexes**, using an external table `elster_table.py`.
- Publishes interpreted data to an MQTT broker (if desired).
- Allows various command-line parameters to customize behavior, including **verbosity** level, MQTT server credentials, and more.
- Differentiates CAN telegram types (e.g., Request, Answer, Change) and only publishes **Answers** to MQTT by default.

## Prerequisites

1. **Python 3.7+** recommended.
2. [SocketCAN](https://www.kernel.org/doc/Documentation/networking/can.txt) properly configured on your Linux system (e.g., `can0`).
3. **pip** installed to handle Python packages.
4. [`python-can`](https://pypi.org/project/python-can/) library:
   ```bash
   pip install python-can

5. [`paho-mqtt`](https://pypi.org/project/paho-mqtt/) library (for MQTT support):
```bash
pip install paho-mqtt
```

6. The elster_table.py file, which contains:
* lookup_elster_index(index): returns a dictionary with fields like "Name", "EnglishName", "Type", etc.
* interpret_elster_value(raw_value, elster_type): returns a properly interpreted Python value from the raw data.

## Quick Start

1. Clone this repository:
```bash
git clone [https://github.com/michaelhenningersrb/Stiebel-Eltron-CAN-Bus-to-MQTT-Reader](https://github.com/michaelhenningersrb/Stiebel-Eltron-CAN-Bus-to-MQTT-Reader)
cd Stiebel-Eltron-CAN-Bus-to-MQTT-Reader
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

Alternatively, install them manually as per the prerequisites above.

3. Configure your socketcan interface (can0):

```bash
# Example: set up can0 at 500 kbit/s
sudo ip link set can0 up type can bitrate 500000
sudo ifconfig can0 up
```
4. Run the script with your desired parameters:

```bash
python can_reader.py \
  --mqtt-server 192.168.1.50 \
  --mqtt-user myuser \
  --mqtt-pass secret \
  --mqtt-prefix home/elster/ \
  --verbosity 2
```

Adjust the above command to match your environment (e.g., different mqtt-server, no user/password, etc.).

5. Observe the output:

With `--verbosity 2`, each CAN message displays essential details (telegram type, Elster index, interpreted value, etc.).
If `--verbosity 3`, you see more debug info (raw data, message details).

`0` = none
`1` = minimal
`2` = standard
`3` = debug

MQTT messages are published only for answers (telegram_type == 2), unless you modify the code.

## Usage & Parameters
Parameter	Description	Default

## Example Invocations
* Minimal logs, only show short output on answered messages:
```bash
python can_reader.py --verbosity 1
```

* Debug logs, with full MQTT config:
```bash
python can_reader.py \
  --mqtt-server 192.168.1.50 \
  --mqtt-port 1883 \
  --mqtt-user user123 \
  --mqtt-pass p4ssW0rd \
  --mqtt-prefix hvac/elster/ \
  --verbosity 3
```
## Project Structure
* `can_reader.py`
  Main script. Handles:

  1. Parsing command-line arguments.
  2. Connecting to the can0 interface.
  3. Reading CAN messages in a loop.
  4. Determining if a message is a request, answer, or change.
  5. Looking up the Elster index and interpreting the raw value.
  6. Optionally publishing via MQTT (if type == answer).
    
* `elster_table.py`
  
  External file containing:

  1. A dictionary or function to map Elster indexes to metadata (like Name, Type, etc.).
  2. A function (interpret_elster_value) to convert raw integer data into human-readable values (e.g., temperature, pressure, etc.).

* requirements.txt (optional)
  If present, it might contain:

  ```txt
  python-can
  paho-mqtt
  ```

## Contributing
1. Fork the repository on GitHub.
2. Create a new branch for your features or bug fixes.
3. Commit your changes with clear messages.
4. Push your branch to your forked repository.
5. Open a pull request on GitHub.

## License
`MIT`

Enjoy reading the Elster data from your CAN bus! If you have any questions, feel free to open an issue or PR.
