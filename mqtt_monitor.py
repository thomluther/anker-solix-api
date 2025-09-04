#!/usr/bin/env python
"""Example exec module to use the Anker API for connecting to the MQTT server and displaying subscribed topics.

This module will prompt for the Anker account details if not pre-set in the header. Upon successful authentication,
you will see the devices of the user account and you can select a device you want to monitor.
"""

import asyncio
from datetime import datetime, timedelta
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

# import keyboard # requires root on unix/linux
from api import api  # pylint: disable=no-name-in-module
from api.apitypes import DeviceHexData, Color  # pylint: disable=no-name-in-module
from api.errors import AnkerSolixError  # pylint: disable=no-name-in-module
from api.mqtt import AnkerSolixMqttSession  # pylint: disable=no-name-in-module
import common
from paho.mqtt.client import Client

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)


async def main() -> (  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    None
):
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
                    elif selection.isdigit() and 1 <= int(selection) <= len(
                        device_names
                    ):
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
                CONSOLE.info(
                    "\nStarting MQTT server connection for %s...",
                    device_selected.get("device_sn"),
                )
                mqtt_session = AnkerSolixMqttSession(apisession=myapi.apisession)
                # register our message callback function for mqtt session
                mqtt_session.message_callback(func=print_message)
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
                    # add queue handler to CONSOLE
                    CONSOLE.addHandler(qh)
                    # start the listener
                    listener.start()
                # subscribe root Topic
                if prefix := mqtt_session.get_topic_prefix(deviceDict=device_selected):
                    mqtt_session.subscribe(f"{prefix}#")
                # Start the loop to process network traffic and callbacks
                client.loop_start()
                # cmdprefix = mqtt_session.get_topic_prefix(deviceDict=device_selected, publish=True)
                # cmdpayload = json.dumps({})
                try:
                    start = datetime.now()
                    minute = 0
                    message, response = mqtt_session.publish(
                        deviceDict=device_selected,
                        hexbytes=mqtt_session.get_command_data(
                            command="update_trigger", parameters={"timeout": 120}
                        ),
                    )
                    CONSOLE.info(f"Published message: {response!s}\n{message!s}")
                    while True:
                        # print progress with minute marker while listening
                        print(".", end="", flush=True)  # noqa: T201
                        await asyncio.sleep(10)
                        if (
                            m := int((datetime.now() - start).total_seconds() / 60)
                        ) != minute:
                            minute = m
                            print(f"{m}", end="", flush=True)  # noqa: T201
                        # Check if a key was pressed
                        # event = keyboard.read_event() # requires root on unix
                        # if event.event_type == keyboard.KEY_DOWN:
                        #     if event.name == 'u':
                        #         CONSOLE.info(
                        #             f"'u' pressed to request updates for topic {prefix}"
                        #         )
                        # publish mqtt message to trigger update?
                        # topic to send the update command for mqtt data from device
                        # payload is actually unknown
                        # response = client.publish(topic=f"{cmdprefix}req", payload=cmdpayload)
                        # CONSOLE.info(
                        #     f"Published topic {cmdprefix}req, payload {cmdpayload!s}:\n{response!s}"
                        # )
                except (KeyboardInterrupt, asyncio.CancelledError):
                    CONSOLE.info("\nDisconnecting from MQTT server...")
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
                    return False
            return True

    except (
        asyncio.CancelledError,
        KeyboardInterrupt,
        ClientError,
        AnkerSolixError,
    ) as err:
        if mqtt_session:
            CONSOLE.info("\nDisconnecting from MQTT server...")
            client.loop_stop()
            mqtt_session.cleanup()
            # ensure the queue listener is closed
            if listener:
                listener.stop()
                # remove queue file handler again before zipping folder
                CONSOLE.removeHandler(qh)
        if isinstance(err, ClientError | AnkerSolixError):
            CONSOLE.error("%s: %s", type(err), err)
            CONSOLE.info("Api Requests: %s", myapi.request_count)
            CONSOLE.info(myapi.request_count.get_details(last_hour=True))
        return False


def print_message(topic: str, message: Any, data: bytes, model: str) -> None:
    """Print and decode the received messages."""
    timestamp = ""
    if isinstance(message, dict):
        timestamp = datetime.fromtimestamp(
            (message.get("head") or {}).get("timestamp") or 0
        ).strftime("%Y-%M-%d %H:%M:%S ")
    CONSOLE.info(f"\nReceived message on topic: {topic}\n{message}")
    if data:
        CONSOLE.info(f"{timestamp}Device hex data:\n{data.hex(':')}")
        # structure hex data
        CONSOLE.info(DeviceHexData(model=model or "", hexbytes=data).decode())


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
