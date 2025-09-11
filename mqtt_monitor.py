#!/usr/bin/env python
"""Example exec module to use the Anker API for connecting to the MQTT server and displaying subscribed topics.

This module will prompt for the Anker account details if not pre-set in the header. Upon successful authentication,
you will see the devices of the user account and you can select a device you want to monitor. Optionally you
can dump the output to a file. The tool will display a usage menu before monitoring starts. While monitoring,
it reacts on key press for the menu options. The menu can be displayed again with 'm'.
"""

import asyncio
from datetime import datetime
from functools import partial
import json
import logging
import logging.handlers
import os
from pathlib import Path
import queue
import tempfile
from typing import Any

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from api import api  # pylint: disable=no-name-in-module
from api.apitypes import Color  # pylint: disable=no-name-in-module
from api.errors import AnkerSolixError  # pylint: disable=no-name-in-module
from api.mqtt import AnkerSolixMqttSession  # pylint: disable=no-name-in-module
from api.mqtttypes import DeviceHexData  # pylint: disable=no-name-in-module
import common
from paho.mqtt.client import Client

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)

# create INLINE logger
INLINE: logging.Logger = logging.getLogger("Inline_logger")
# Set parent to lowest level to allow messages passed to all handlers using their own level
INLINE.setLevel(logging.DEBUG)
# create console handler and set level to info and formatting without newline
handler = common.InlineStreamHandler()
handler.setLevel(logging.INFO)
# No newline in format
handler.setFormatter(logging.Formatter("%(message)s"))
INLINE.addHandler(handler)

VALUES: dict = {}
FOUNDTOPICS: set = set()


async def main() -> None:  # noqa: C901
    """Run Main routine to start the monitor in a loop."""
    mqtt_session: AnkerSolixMqttSession | None = None
    listener = None
    CONSOLE.info("Anker Solix Device MQTT Monitor:")
    try:
        async with ClientSession() as websession:
            user = common.user()
            CONSOLE.info("Trying Api authentication for user %s...", user)
            myapi = api.AnkerSolixApi(
                user,
                common.password(),
                common.country(),
                websession,
                CONSOLE,
            )
            if await myapi.async_authenticate():
                CONSOLE.info("Anker Cloud authentication: OK")
            else:
                # Login validation will be done during first API call
                CONSOLE.info("Anker Cloud authentication: CACHED")
            device_names: list | None = None
            device_selected: dict = {}
            CONSOLE.info("Getting sites and device list...")
            await myapi.update_sites()
            await myapi.get_bind_devices()
            devices = list(myapi.devices.values())
            device_names = [
                (
                    ", ".join(
                        [
                            str(d.get("device_sn")),
                            str(
                                d.get("device_pn") or d.get("product_code") or "Model??"
                            ),
                            str(d.get("device_name") or d.get("name")),
                            "Alias: " + str(d.get("alias_name") or d.get("alias")),
                            "System: "
                            + str(
                                (
                                    (
                                        (
                                            myapi.sites.get(d.get("site_id") or "")
                                            or {}
                                        ).get("site_info")
                                        or {}
                                    ).get("site_name")
                                )
                                or ""
                            ),
                        ]
                    )
                )
                for d in devices
            ]
            if len(device_names) > 0:
                while not device_selected:
                    CONSOLE.info("\nSelect which device to be monitored:")
                    for idx, devicename in enumerate(device_names, start=1):
                        CONSOLE.info("(%s) %s", idx, devicename)
                    selection = input(
                        f"Enter device number ({'1-' if len(device_names) > 1 else ''}{len(device_names)}) or nothing to quit: "
                    )
                    if not selection:
                        return False
                    if selection.isdigit() and 1 <= int(selection) <= len(device_names):
                        device_selected = devices[int(selection) - 1]

                # ask whether dumping messages to file
                response = input(
                    "Do you want to dump MQTT message decoding also to file? (Y/N): "
                )
                if response := str(response).upper() in ["Y", "YES", "TRUE", 1]:
                    model = (
                        device_selected.get("device_pn")
                        or device_selected.get("product_code")
                        or ""
                    )
                    prefix = f"{model}_mqtt_dump"
                    response = input(f"Filename prefix for export ({prefix}): ")
                    filename = f"{response or prefix}_{datetime.now().strftime('%Y-%m-%d__%H_%M_%S')}.txt"
                    # Ensure dump folder exists
                    dumpfolder = (Path(__file__).parent / "mqttdumps").resolve()
                    if not (
                        os.access(dumpfolder.parent, os.W_OK)
                        or os.access(dumpfolder, os.W_OK)
                    ):
                        dumpfolder = Path(tempfile.gettempdir()) / "mqttdumps"
                    Path(dumpfolder).mkdir(parents=True, exist_ok=True)
                    # create a queue for async file logging with CONSOLE logger
                    que = queue.Queue()
                    # add a handler that dumps at INFO level, independent of other logger handler setting
                    qh = logging.handlers.QueueHandler(que)
                    qh.setFormatter(
                        logging.Formatter(
                            fmt="%(asctime)s %(levelname)s: %(message)s",
                            datefmt="%H:%M:%S",
                        )
                    )
                    qh.setLevel(logging.INFO)
                    # Replace color escape sequences for file logging
                    qh.addFilter(ReplaceFilter())
                    # create file handler for async file logging from the queue
                    loop = asyncio.get_running_loop()
                    fh = await loop.run_in_executor(
                        None,
                        partial(
                            logging.FileHandler,
                            filename=Path(
                                dumpfolder / filename,
                            ),
                        ),
                    )
                    # create a listener for messages on the queue and log them to the file handler
                    listener = logging.handlers.QueueListener(que, fh)
                    CONSOLE.info(
                        "\nMQTT message dumping to file: %s",
                        Path.resolve(Path(dumpfolder / filename)),
                    )

                # Start the MQTT session for the selected device
                device_sn = device_selected.get("device_sn")
                device_pn = (
                    device_selected.get("device_pn")
                    or device_selected.get("product_code")
                    or ""
                )
                CONSOLE.info(
                    f"\nStarting MQTT server connection for device {device_sn} (model {device_pn})..."
                )
                # Initialize the session
                mqtt_session = AnkerSolixMqttSession(apisession=myapi.apisession)
                # Connect the MQTT client
                client: Client = await mqtt_session.connect_client_async()
                if not client.is_connected:
                    CONSOLE.error(
                        f"Connection failed to MQTT server {mqtt_session.host}:{mqtt_session.port}"
                    )
                    mqtt_session.cleanup()
                    return False
                CONSOLE.info(
                    f"Connected successfully to MQTT server {mqtt_session.host}:{mqtt_session.port}"
                )
                if listener:
                    # add queue handler to CONSOLE for output logging to file
                    CONSOLE.addHandler(qh)
                    # start the listener
                    listener.start()
                # subscribe root Topic of selected device
                topics = set()
                if prefix := mqtt_session.get_topic_prefix(deviceDict=device_selected):
                    topics.add(f"{prefix}#")
                # Flag to control the key reader loop
                # stop_event = asyncio.Event()

                # Signal handler to set the stop flag
                # def handle_sigint():
                #     """Handle interrupt signals."""
                #     stop_event.set()

                # print the menu before starting
                print_menu()
                try:
                    activetopic = None
                    realtime = True
                    rt_devices = {device_sn}
                    loop = asyncio.get_running_loop()
                    # loop.add_signal_handler(signal.SIGINT, handle_sigint)
                    # loop.add_signal_handler(signal.SIGTERM, handle_sigint)
                    # Start the background poller with subscriptions and update trigger
                    poller_task = asyncio.create_task(
                        mqtt_session.message_poller(
                            topics=topics,
                            trigger_devices=rt_devices,
                            msg_callback=print_message,
                            timeout=60,
                        )
                    )
                    # Start the wait progress printer in background
                    progress_task = asyncio.create_task(print_wait_progress())
                    while True:
                        # Check if a key was pressed
                        if k := await loop.run_in_executor(None, common.getkey):
                            k = k.lower()
                            if k == "m":
                                print_menu()
                            elif k == "u":
                                CONSOLE.info(
                                    f"{Color.RED}Unsubscribing all topics...{Color.OFF}"
                                )
                                topics.clear()
                                activetopic = None
                                if mqtt_session.message_callback() == print_values:
                                    # clear last message from screen and show active subscription
                                    await asyncio.sleep(6)
                                    print_values(
                                        session=mqtt_session,
                                        topic="",
                                        message=None,
                                        data=None,
                                        model=device_pn,
                                    )
                            elif k == "s":
                                CONSOLE.info(
                                    f"{Color.GREEN}Subscribing root topic...{Color.OFF}"
                                )
                                topics.clear()
                                activetopic = None
                                topics.add(f"{prefix}#")
                            elif k == "t":
                                if tl := list(FOUNDTOPICS):
                                    index = (
                                        tl.index(activetopic)
                                        if activetopic in tl
                                        else -1
                                    )
                                    activetopic = tl[
                                        index + 1 if index + 1 < len(tl) else 0
                                    ]
                                    CONSOLE.info(
                                        f"{Color.YELLOW}Toggling subscription to topic {activetopic}...{Color.OFF}"
                                    )
                                    topics.clear()
                                    topics.add(f"{activetopic}")
                                else:
                                    CONSOLE.info(
                                        f"{Color.RED}No topics received yet for toggling!{Color.OFF}"
                                    )
                            elif k == "r":
                                if realtime:
                                    CONSOLE.info(
                                        f"{Color.RED}Disabling real time data trigger, messages will reduce after max. 60 seconds...{Color.OFF}"
                                    )
                                    realtime = False
                                    rt_devices.discard(device_sn)
                                else:
                                    CONSOLE.info(
                                        f"{Color.GREEN}Enabling real time data trigger, message frequency should increase shortly...{Color.OFF}"
                                    )
                                    realtime = True
                                    rt_devices.add(device_sn)
                            elif k == "v":
                                if mqtt_session.message_callback() == print_message:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}Switching to Values view for next message...{Color.OFF}"
                                    )
                                    mqtt_session.message_callback(func=print_values)
                                else:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}Switching to Messages view for next message...{Color.OFF}"
                                    )
                                    mqtt_session.message_callback(func=print_message)
                            elif k == "esc":
                                break
                            await asyncio.sleep(0.5)
                finally:
                    # Cancel the started tasks
                    poller_task.cancel()
                    progress_task.cancel()
                    # Wait for the tasks to finish cancellation
                    try:
                        await poller_task
                    except asyncio.CancelledError:
                        CONSOLE.info("MQTT client poller task cancelled.")
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        CONSOLE.info("Progress printer was cancelled.")
                    client.loop_stop()
                    mqtt_session.cleanup()
                    # ensure the queue listener is closed
                    if listener:
                        listener.stop()
                        # remove queue file handler again before zipping folder
                        CONSOLE.removeHandler(qh)
                        CONSOLE.info(
                            "\nMQTT dump file completed: %s",
                            Path.resolve(Path(dumpfolder / filename)),
                        )
            return True

    except (
        asyncio.CancelledError,
        KeyboardInterrupt,
        ClientError,
        AnkerSolixError,
    ) as err:
        if isinstance(err, ClientError | AnkerSolixError):
            CONSOLE.error("%s: %s", type(err), err)
            CONSOLE.info("Api Requests: %s", myapi.request_count)
            CONSOLE.info(myapi.request_count.get_details(last_hour=True))
        return False
    finally:
        if mqtt_session:
            CONSOLE.info("Disconnecting from MQTT server...")
            client.loop_stop()
            mqtt_session.cleanup()
            # ensure the queue listener is closed
            if listener:
                listener.stop()
                # remove queue file handler again before zipping folder
                CONSOLE.removeHandler(qh)


def print_menu() -> None:
    """Print the key menu."""
    CONSOLE.info("\n%s\nMQTT Monitor key menu:\n%s", 100 * "-", 100 * "-")
    CONSOLE.info(f"[{Color.YELLOW}M{Color.OFF}]enu to show this key list")
    CONSOLE.info(
        f"[{Color.YELLOW}U{Color.OFF}]nsubscribe all topics. This will stop receiving MQTT messages"
    )
    CONSOLE.info(
        f"[{Color.YELLOW}S{Color.OFF}]ubscribe root topic. This will subscribe root only"
    )
    CONSOLE.info(
        f"[{Color.YELLOW}T{Color.OFF}]oggle subscribed topic. If only one topic identified from root topic, toggling is not possible"
    )
    CONSOLE.info(
        f"[{Color.YELLOW}R{Color.OFF}]eal time data trigger toggle ON (Default) or OFF"
    )
    CONSOLE.info(
        f"[{Color.YELLOW}V{Color.OFF}]iew value extraction refresh screen or MQTT message decoding"
    )
    CONSOLE.info(
        f"[{Color.RED}ESC{Color.OFF}] or [{Color.RED}CTRL-C{Color.OFF}] to stop MQTT monitor"
    )
    input(f"Hit [{Color.GREEN}Enter{Color.OFF}] to continue...\n")


async def print_wait_progress() -> None:
    """Print dots and minute markers as progress for message monitoring."""
    # print progress with minute marker while listening
    start = datetime.now()
    minute = 0
    INLINE.info("Listening...")
    while True:
        await asyncio.sleep(5)
        INLINE.info(".")
        if (m := int((datetime.now() - start).total_seconds() / 60)) != minute:
            minute = m
            INLINE.info(f"{m}")


def print_message(
    session: AnkerSolixMqttSession, topic: str, message: Any, data: bytes, model: str
) -> None:
    """Print and decode the received messages."""
    global VALUES, FOUNDTOPICS  # noqa: PLW0602
    if topic:
        FOUNDTOPICS.add(topic)
    timestamp = ""
    if isinstance(message, dict):
        timestamp = datetime.fromtimestamp(
            (message.get("head") or {}).get("timestamp") or 0
        ).strftime("%Y-%M-%d %H:%M:%S ")
    CONSOLE.info(f"\nReceived message on topic: {topic}\n{message}")
    if isinstance(data, bytes):
        CONSOLE.info(f"{timestamp}Device hex data:\n{data.hex(':')}")
        # structure hex data
        hd = DeviceHexData(model=model or "", hexbytes=data)
        CONSOLE.info(hd.decode())
        # extract values to dict
        VALUES.update(hd.values())
    elif data:
        # no encoded data in message, dump object whatever it is
        CONSOLE.info(f"{timestamp}Device data:\n{json.dumps(data, indent=2)}")


def print_values(
    session: AnkerSolixMqttSession, topic: str, message: Any, data: bytes, model: str
) -> None:
    """Print the accumulated and refreshed values including last message timestamp."""
    global VALUES, FOUNDTOPICS  # noqa: PLW0602
    if topic:
        FOUNDTOPICS.add(topic)
    timestamp = ""
    col1 = 25
    col2 = 25
    col3 = 25
    if isinstance(message, dict):
        timestamp = datetime.fromtimestamp(
            (message.get("head") or {}).get("timestamp") or 0
        ).strftime("%Y-%M-%d %H:%M:%S")
    common.clearscreen()
    hd = DeviceHexData(model=model or "", hexbytes=data)
    CONSOLE.info(
        f"Realtime Trigger: {Color.GREEN + ' ON' if len(session.triggered_devices) else Color.RED + 'OFF'}{Color.OFF}, "
        f"Active topic: {Color.GREEN}{str(session.subscriptions or '')[1:-1]}{Color.OFF}"
    )
    CONSOLE.info(f"{session.mqtt_stats!s}")
    if message:
        CONSOLE.info(
            f"{timestamp}: Received message '{Color.YELLOW + hd.msg_header.msgtype.hex(':') + Color.OFF}' on topic: {Color.YELLOW + topic + Color.OFF}"
        )
    if data:
        VALUES.update(hd.values())
    if VALUES:
        CONSOLE.info(f"{100 * '-'}")
        fields = []
        for key, value in VALUES.items():
            # convert timestamps to readable date and time for printout
            if "timestamp" in key and isinstance(value, int):
                value = datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
            fields.append((key, value))
            if len(fields) >= 2:
                # print row
                CONSOLE.info(
                    f"{fields[0][0]:<{col1}}: {fields[0][1]!s:<{col2}} {fields[1][0]:<{col3}}: {fields[1][1]!s}"
                )
                fields.clear()
        if fields:
            CONSOLE.info(f"{fields[0][0]:<{col1}}: {fields[0][1]!s:<{col2}}")
    CONSOLE.info(f"{100 * '-'}\nReceived Topics:")
    for t in FOUNDTOPICS:
        CONSOLE.info(f"{t}")
    CONSOLE.info(f"{100 * '-'}\nReceived Messages:")
    CONSOLE.info(f"{json.dumps(session.mqtt_stats.dev_messages)}")
    if message:
        CONSOLE.info(f"{100 * '-'}\n{message}")
        if isinstance(data, bytes):
            CONSOLE.info(f"Device hex data:\n{data.hex(':')}")
        elif data:
            # no encoded data in message, dump object whatever it is
            CONSOLE.info(f"Device data:\n{json.dumps(data, indent=2)}")


class ReplaceFilter(logging.Filter):
    """Class for custom replacements in a logger handler."""

    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        """Init the class."""
        super().__init__()
        # replace Color escape sequences for logging per default
        if not replacements:
            replacements = {c.value: "" for c in Color}
        self.replacements = replacements

    def filter(self, record):
        """Filter doing the replacements."""
        for old, new in self.replacements.items():
            record.msg = record.msg.replace(old, new)
        return True


# run async main
if __name__ == "__main__":
    try:
        if not asyncio.run(main(), debug=False):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
