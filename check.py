#!/usr/bin/env python3

"""
Netspot Alarm Check

This program checks if the Netspot Control service has any new alarm messages available. If multiple alarms are
received, then the program shows the results for the one with the highest probability value.

Running the application needs two arguments. The address for the server and port number the server is listening to.

For example, connecting to the localhost server on port 2000:
python3 check.py 127.0.0.1 2000

By default, the application asks the server to send all alarms since the last time the program was run. Alarms request
is also limited to the 50 most recent available since the previous run. This behavior can be changed by giving an
optional argument --within <minutes>, where <minutes> is the number of minutes from the current time backward, we
request the server to send alarms.

The program exits with code 1 if alarms are available, with 0 if not, and 2 on errors.
"""
import json
import sys
import time
from argparse import ArgumentParser

import requests

DEFAULT_DEVICE_NAME = "Example Smart Device"


def get_last_time():
    """Reads last_time.txt and returns timestamp from there or 0 for known errors"""
    try:
        file = open("last_time.txt")
        timestamp = int(file.readline().rstrip())
        file.close()
        return timestamp
    except (FileNotFoundError, ValueError):
        return 0


def set_last_time():
    """Writes the current timestamp to the last_time.txt file"""
    file = open("last_time.txt", "w")
    file.write(str(time.time_ns()))
    file.close()


def netspot_alarm_check(address, port, minutes=None):
    """
    Check for Netspot Alarm Messages

    This function sends alarms request to the server in *address* using the *port*.

    Parameters
    ----------
    address : str
        Server address
    port : int
        Connect to this port
    minutes : float or None
        Optional time limit in minutes.

    Returns
    -------
    (True, Message)
        If alarms were received. Message is dict for message with the highest probability.
    (True, None)
        If alarms were not received but request was okay.
    (False, Message)
        If request fails. The message is str containing reason for the failure.
    """

    # Get or make timestamp for alarms request
    if minutes is None:
        timestamp = get_last_time()
    else:
        timestamp = time.time_ns() - int(minutes * 6e10)

    # Making the request
    url = f"http://{address}:{port}/v1/netspots/alarms"
    params = {"time": timestamp, "last": 50}
    try:
        reply = requests.get(url, params)
    except requests.RequestException as e:
        return False, str(e)

    # Checking the reply
    if reply.status_code == 200:
        # Request was okay, save current time to be used with next request
        set_last_time()

        # Handling messages
        messages = reply.json()
        if len(messages) == 0:
            # No alarms
            return True, None
        # Find messages with the highest probability
        highest_probability = 0.0
        most_urgent_message = ""
        for message in messages:
            if message["probability"] >= highest_probability:
                highest_probability = message["probability"]
                most_urgent_message = message
        return True, most_urgent_message

    # Server responded with error. Return status code and content in the message
    return (
        False,
        f"Server responded with {reply.status_code}:\n{reply.content.decode('utf-8')}",
    )


def main():
    """
    Application start point.

    Checks arguments and calls the netspot_alarm_check.

    Returns
    -------
    int
        0 No alarms
        1 Alarms received
        2 Application error
    """
    parser = ArgumentParser(description="Netspot Alarm Check")
    parser.add_argument("address", type=str, help="Server address")
    parser.add_argument("port", type=int, help="Connect to this port")
    parser.add_argument(
        "-d",
        "--device",
        nargs="?",
        type=str,
        metavar="NAME",
        dest="device",
        default=DEFAULT_DEVICE_NAME,
        help=f"Name of the device for the DHT message. Default: {DEFAULT_DEVICE_NAME}",
    )
    parser.add_argument(
        "-w",
        "--within",
        nargs="?",
        type=float,
        metavar="MINUTES",
        dest="minutes",
        help="Only receive alarms that are newer than this time limit.",
    )
    args = parser.parse_args()

    (success, message) = netspot_alarm_check(
        args.address, args.port, args.minutes
    )

    if success:
        if message is None:
            return 0
        # We have an alarm message. Let us create DHT message from it.
        dht_message = {
            "Topic": "SIFIS: Netspot Alarm Results",
            "Device": args.device,
            "Statistic": message["stat"],
            "Status": message["status"],
            "Probability": message["probability"],
            "Time:": message["time"],
        }
        dht_message_json = json.dumps(dht_message, separators=(",", ":"))
        print(dht_message_json)
        return 1
    print("Could not receive alarms:", message, file=sys.stdout)
    return 2


if __name__ == "__main__":
    sys.exit(main())
