#!/usr/bin/env python
"""Example exec module to use the Anker API for connecting to the MQTT server and displaying subscribed topics.

This module will prompt for the Anker account details if not pre-set in the header. Upon successful authentication,
you will see the devices of the user account and you can select a device you want to monitor. Optionally you
can dump the output to a file. The tool will display a usage menu before monitoring starts. While monitoring,
it reacts on key press for the menu options. The menu can be displayed again with 'm'.
"""

import argparse
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
from api.api import AnkerSolixApi  # pylint: disable=no-name-in-module
from api.apitypes import Color  # pylint: disable=no-name-in-module
from api.errors import AnkerSolixError  # pylint: disable=no-name-in-module
from api.mqtt import AnkerSolixMqttSession  # pylint: disable=no-name-in-module
from api.mqtttypes import DeviceHexData  # pylint: disable=no-name-in-module
import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE
# enable debug mode for the console handler
# CONSOLE.handlers[0].setLevel(logging.DEBUG)

# use INLINE logger from common module
INLINE: logging.Logger = common.INLINE


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Anker Solix MQTT Monitor - Monitor MQTT messages and commands of Anker Solix devices in real-time"
    )
    parser.add_argument(
        "--device-sn", "-dev", type=str, help="Define device SN to be monitored"
    )
    parser.add_argument(
        "--realtime-trigger",
        "-rt",
        action="store_true",
        help="Enable MQTT real-time data trigger at startup",
    )
    parser.add_argument(
        "--status-request",
        "-sr",
        action="store_true",
        help="Issue immediate MQTT status request after startup",
    )
    parser.add_argument(
        "--value-display",
        "-vd",
        action="store_true",
        help="Initially show MQTT value display instead of MQTT messages display",
    )
    parser.add_argument(
        "--filedump",
        "-fd",
        action="store_true",
        help="Enable console dump into file",
    )
    parser.add_argument(
        "--dump-prefix",
        "-dp",
        type=str,
        default="",
        help="Define dump filename prefix",
    )
    parser.add_argument(
        "--runtime",
        "-r",
        type=int,
        default=0,
        choices=range(1, 60),
        metavar="[1-60]",
        help="Optional runtime in minutes (default: Until cancelled)",
    )
    args = parser.parse_args()
    # Validate argument combinations
    if args.dump_prefix and not args.filedump:
        parser.error("--dump-suffix requires -filedump to be specified")
    return args


class AnkerSolixMqttMonitor:
    """Define the class for the monitor."""

    def __init__(self, args: argparse.Namespace | None = None) -> None:
        """Initialize."""
        # Parse command line arguments if not provided
        if not isinstance(args, argparse.Namespace):
            args = parse_arguments()
        self.api: AnkerSolixApi | None = None
        self.device_selected: dict = {}
        self.device_sn: str | None = args.device_sn
        self.found_topics: set = set()
        self.loop: asyncio.AbstractEventLoop
        self.filedump: bool = args.filedump
        self.realtime_trigger: bool = args.realtime_trigger
        self.status_request: bool = args.status_request
        self.value_display: bool = args.value_display
        self.fileprefix: str | None = args.dump_prefix
        self.endtime: datetime | None = (
            (datetime.now() + timedelta(minutes=args.runtime)) if args.runtime else None
        )

    async def main(self) -> None:  # noqa: C901
        """Run Main routine to start the monitor in a loop."""
        mqtt_session: AnkerSolixMqttSession | None = None
        listener = None
        self.loop = asyncio.get_running_loop()
        CONSOLE.info("Anker Solix Device MQTT Monitor:")
        try:
            async with ClientSession() as websession:
                user = common.user()
                CONSOLE.info("Trying Api authentication for user %s...", user)
                self.api = AnkerSolixApi(
                    user,
                    common.password(),
                    common.country(),
                    websession,
                    CONSOLE,
                )
                if await self.api.async_authenticate():
                    CONSOLE.info("Anker Cloud authentication: OK")
                else:
                    # Login validation will be done during first API call
                    CONSOLE.info("Anker Cloud authentication: CACHED")
                device_names: list | None = None
                self.device_selected: dict = {}
                CONSOLE.info("Getting sites and device list...")
                await self.api.update_sites()
                await self.api.get_bind_devices()
                devices = list(self.api.devices.values())
                device_names = [
                    (
                        ", ".join(
                            [
                                str(d.get("device_sn")),
                                str(
                                    d.get("device_pn")
                                    or d.get("product_code")
                                    or "Model??"
                                ),
                                str(d.get("device_name") or d.get("name")),
                                "Alias: " + str(d.get("alias_name") or d.get("alias")),
                                "System: "
                                + str(
                                    (
                                        (
                                            (
                                                self.api.sites.get(
                                                    d.get("site_id") or ""
                                                )
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
                    if (not self.device_sn or d.get("device_sn") == self.device_sn)
                ]
                if self.device_sn:
                    if device_names:
                        # specified device found
                        self.device_selected = self.api.devices.get(self.device_sn)
                        CONSOLE.info(
                            f"Monitoring device: ({Color.YELLOW}{device_names[0]}{Color.OFF})"
                        )
                    else:
                        CONSOLE.info(
                            f"Specified device {Color.CYAN}{self.device_sn}{Color.OFF} not found for account {Color.YELLOW}{self.api.apisession.email}{Color.OFF}"
                        )
                        return False
                elif len(device_names) > 0:
                    while not self.device_selected:
                        CONSOLE.info("\nSelect which device to be monitored:")
                        for idx, devicename in enumerate(device_names, start=1):
                            CONSOLE.info(
                                f"({Color.YELLOW}{idx}{Color.OFF}) {devicename}"
                            )
                        selection = input(
                            f"Enter device number ({Color.YELLOW}{'1-' if len(device_names) > 1 else ''}{len(device_names)}{Color.OFF}) or {Color.CYAN}nothing{Color.OFF} to quit: "
                        )
                        if not selection:
                            return False
                        if selection.isdigit() and 1 <= int(selection) <= len(
                            device_names
                        ):
                            self.device_selected = devices[int(selection) - 1]
                else:
                    CONSOLE.info("No owned Anker Solix devices found for your account.")
                    return False

                if not (self.device_sn or self.filedump):
                    # ask whether dumping messages to file
                    response = input(
                        f"Do you want to dump MQTT message decoding also to file? ({Color.YELLOW}Y{Color.OFF}/{Color.CYAN}N{Color.OFF}): "
                    )
                    self.filedump = bool(
                        str(response).upper() in ["Y", "YES", "TRUE", 1]
                    )
                if self.filedump:
                    model = (
                        self.device_selected.get("device_pn")
                        or self.device_selected.get("product_code")
                        or ""
                    )
                    prefix = f"{model}_mqtt_dump"
                    if not (self.fileprefix or self.device_sn):
                        self.fileprefix = input(
                            f"Filename prefix for export ({Color.CYAN}{prefix}{Color.OFF}): "
                        )
                    filename = f"{self.fileprefix or prefix}_{datetime.now().strftime('%Y-%m-%d__%H_%M_%S')}.txt"
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
                    fh = await self.loop.run_in_executor(
                        None,
                        partial(
                            logging.FileHandler,
                            filename=Path(
                                dumpfolder / filename,
                            ),
                            encoding="utf-8",
                        ),
                    )
                    # create a listener for messages on the queue and log them to the file handler
                    listener = logging.handlers.QueueListener(que, fh)
                    CONSOLE.info(
                        f"\nMQTT message dumping to file: {Color.CYAN}{Path.resolve(Path(dumpfolder / filename))}{Color.OFF}"
                    )

                # Start the MQTT session for the selected device
                device_sn = self.device_selected.get("device_sn")
                device_pn = (
                    self.device_selected.get("device_pn")
                    or self.device_selected.get("product_code")
                    or ""
                )
                CONSOLE.info(
                    f"\nStarting MQTT server connection for device {device_sn} (model {device_pn})..."
                )
                # Initialize the session
                if not (
                    (mqtt_session := await self.api.startMqttSession())
                    and mqtt_session.is_connected()
                ):
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
                if prefix := mqtt_session.get_topic_prefix(
                    deviceDict=self.device_selected
                ):
                    topics.add(f"{prefix}#")
                # Command messages (app to device)
                if cmd_prefix := mqtt_session.get_topic_prefix(
                    deviceDict=self.device_selected, publish=True
                ):
                    topics.add(f"{cmd_prefix}#")
                try:
                    activetopic = None
                    realtime = self.realtime_trigger
                    rt_devices = set()
                    if self.device_sn:
                        # start realtime trigger if defined
                        if self.realtime_trigger:
                            rt_devices.add(device_sn)
                        if self.value_display:
                            CONSOLE.info(
                                f"{Color.YELLOW}Starting with Values view...{Color.OFF}"
                            )
                    else:
                        # print the menu before starting if interactive
                        self.print_menu()
                    CONSOLE.info(
                        f"Starting MQTT message listener, real time data trigger is: {Color.GREEN + 'ON' if realtime else Color.RED + 'OFF'}{Color.OFF}"
                    )
                    # Start the background poller with subscriptions and update trigger
                    poller_task = self.loop.create_task(
                        mqtt_session.message_poller(
                            topics=topics,
                            trigger_devices=rt_devices,
                            msg_callback=self.print_values
                            if self.value_display
                            else self.print_message,
                            timeout=60,
                        )
                    )
                    # Start the wait progress printer in background
                    progress_task = self.loop.create_task(self.print_wait_progress())
                    # get running loop to run blocking code
                    loop = asyncio.get_running_loop()
                    # individual status request at startup
                    if self.status_request and self.device_sn:
                        # delay to wait for subscription to complete for receiving the message
                        await asyncio.sleep(2)
                        if mqtt_session.status_request(
                            deviceDict=self.device_selected,
                            wait_for_publish=2,
                        ).is_published():
                            CONSOLE.info(
                                f"{Color.CYAN}\nPublished immediate status request, status message(s) should appear shortly...{Color.OFF}"
                            )
                    while True:
                        # Check if a key was pressed
                        if k := await loop.run_in_executor(None, common.getkey):
                            k = k.lower()
                            if k in ["m", "k"]:
                                self.print_menu()
                            elif k == "u":
                                CONSOLE.info(
                                    f"{Color.RED}\nUnsubscribing all topics...{Color.OFF}"
                                )
                                topics.clear()
                                activetopic = None
                                if mqtt_session.message_callback() == self.print_values:
                                    # clear last message from screen and show active subscription
                                    await asyncio.sleep(6)
                                    self.print_values(
                                        session=mqtt_session,
                                        topic="",
                                        message=None,
                                        data=None,
                                        model=device_pn,
                                    )
                            elif k == "s":
                                CONSOLE.info(
                                    f"{Color.GREEN}\nSubscribing root topics...{Color.OFF}"
                                )
                                topics.clear()
                                activetopic = None
                                topics.add(f"{prefix}#")
                                topics.add(f"{cmd_prefix}#")
                            elif k == "t":
                                if tl := list(self.found_topics):
                                    index = (
                                        tl.index(activetopic)
                                        if activetopic in tl
                                        else -1
                                    )
                                    activetopic = tl[
                                        index + 1 if index + 1 < len(tl) else 0
                                    ]
                                    CONSOLE.info(
                                        f"{Color.YELLOW}\nToggling subscription to topic {activetopic}...{Color.OFF}"
                                    )
                                    topics.clear()
                                    topics.add(f"{activetopic}")
                                else:
                                    CONSOLE.info(
                                        f"{Color.RED}\nNo topics received yet for toggling!{Color.OFF}"
                                    )
                            elif k == "r":
                                if realtime:
                                    CONSOLE.info(
                                        f"{Color.RED}\nDisabling real time data trigger, messages will reduce after max. 60 seconds...{Color.OFF}"
                                    )
                                    realtime = False
                                    rt_devices.discard(device_sn)
                                else:
                                    CONSOLE.info(
                                        f"{Color.GREEN}\nEnabling real time data trigger, message frequency should increase shortly...{Color.OFF}"
                                    )
                                    realtime = True
                                    rt_devices.add(device_sn)
                            elif k == "o":
                                # individual real time trigger request
                                if mqtt_session.realtime_trigger(
                                    deviceDict=self.device_selected,
                                    timeout=60,
                                    wait_for_publish=2,
                                ).is_published():
                                    CONSOLE.info(
                                        f"{Color.CYAN}\nPublished one time real time trigger request, message frequency should appear shortly...{Color.OFF}"
                                    )
                            elif k == "i":
                                # individual status request
                                if mqtt_session.status_request(
                                    deviceDict=self.device_selected,
                                    wait_for_publish=2,
                                ).is_published():
                                    CONSOLE.info(
                                        f"{Color.CYAN}\nPublished status request, status message(s) should appear shortly...{Color.OFF}"
                                    )
                            elif k == "d":
                                # save active message callback for later restore
                                cb = mqtt_session.message_callback()
                                # Clear message callback to prevent scrolling during display
                                mqtt_session.message_callback(None)
                                self.print_table()
                                input(
                                    f"Hit [{Color.GREEN}Enter{Color.OFF}] to continue...\n"
                                )
                                mqtt_session.message_callback(cb)
                            elif k == "v":
                                if (
                                    mqtt_session.message_callback()
                                    == self.print_message
                                ):
                                    CONSOLE.info(
                                        f"{Color.YELLOW}\nSwitching to Values view...{Color.OFF}"
                                    )
                                    mqtt_session.message_callback(
                                        func=self.print_values
                                    )
                                    await asyncio.sleep(1)
                                    common.clearscreen()
                                    self.print_table()
                                else:
                                    CONSOLE.info(
                                        f"{Color.YELLOW}\nSwitching to Messages view for next message...{Color.OFF}"
                                    )
                                    mqtt_session.message_callback(
                                        func=self.print_message
                                    )
                            elif k in ["esc", "q"]:
                                CONSOLE.info(
                                    f"{Color.RED}\nStopping monitor...{Color.OFF}"
                                )
                                break
                            await asyncio.sleep(0.5)
                        # check if runtime is over
                        if self.endtime and datetime.now() > self.endtime:
                            CONSOLE.info(
                                f"{Color.RED}\nRuntime exceeded, stopping monitor...{Color.OFF}"
                            )
                            break
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
                    if self.api.mqttsession:
                        self.api.mqttsession.cleanup()
                    # ensure the queue listener is closed
                    if listener:
                        listener.stop()
                        # remove queue file handler again before zipping folder
                        CONSOLE.removeHandler(qh)
                        CONSOLE.info(
                            "\nMQTT dump file completed: %s%s%s",
                            Color.CYAN,
                            Path.resolve(Path(dumpfolder / filename)),
                            Color.OFF,
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
                CONSOLE.info("Api Requests: %s", self.api.request_count)
                CONSOLE.info(self.api.request_count.get_details(last_hour=True))
            return False
        finally:
            if mqtt_session:
                CONSOLE.info("Disconnecting from MQTT server...")
                if self.api.mqttsession:
                    self.api.mqttsession.cleanup()
                # ensure the queue listener is closed
                if listener:
                    listener.stop()
                    # remove queue file handler again before zipping folder
                    CONSOLE.removeHandler(qh)

    def print_menu(self) -> None:
        """Print the key menu."""
        CONSOLE.info(100 * "-")
        CONSOLE.info(f"{Color.YELLOW}MQTT Monitor key menu:{Color.OFF}")
        CONSOLE.info(100 * "-")
        CONSOLE.info(
            f"[{Color.YELLOW}K{Color.OFF}]ey list to show this [{Color.YELLOW}M{Color.OFF}]enu"
        )
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
            f"[{Color.YELLOW}R{Color.OFF}]eal time data trigger loop OFF (Default) or ON for continuous status messages"
        )
        CONSOLE.info(
            f"[{Color.YELLOW}O{Color.OFF}]ne real time trigger for device (timeout 60 seconds)"
        )
        CONSOLE.info(f"[{Color.YELLOW}I{Color.OFF}]mmediate status request for device")
        CONSOLE.info(
            f"[{Color.YELLOW}V{Color.OFF}]iew value extraction refresh screen or MQTT message decoding"
        )
        CONSOLE.info(f"[{Color.YELLOW}D{Color.OFF}]isplay snapshot of extracted values")
        CONSOLE.info(
            f"[{Color.RED}Q{Color.OFF}]uit, [{Color.RED}ESC{Color.OFF}] or [{Color.RED}CTRL-C{Color.OFF}] to stop MQTT monitor"
        )
        input(f"Hit [{Color.GREEN}Enter{Color.OFF}] to continue...\n")

    async def print_wait_progress(self) -> None:
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
        self,
        session: AnkerSolixMqttSession,
        topic: str,
        message: Any,
        data: bytes,
        model: str,
        *args,
        **kwargs,
    ) -> None:
        """Print and decode the received messages."""
        if topic:
            self.found_topics.add(topic)
        timestamp = ""
        if isinstance(message, dict):
            timestamp = datetime.fromtimestamp(
                (message.get("head") or {}).get("timestamp") or 0
            ).strftime("%Y-%m-%d %H:%M:%S ")
        CONSOLE.info(f"\nReceived message on topic: {topic}\n{message}")
        if isinstance(data, bytes):
            CONSOLE.info(f"{timestamp}Device hex data:\n{data.hex(':')}")
            # structure hex data
            hd = DeviceHexData(model=model or "", hexbytes=data)
            CONSOLE.info(hd.decode())
        elif data:
            # no encoded data in message, dump object whatever it is
            CONSOLE.info(f"{timestamp}Device data:\n{json.dumps(data, indent=2)}")

    def print_table(self) -> None:
        """Print the accumulated extracted values in a table."""
        col1 = 25
        col2 = 25
        col3 = 25
        device_pn = (
            self.device_selected.get("device_pn")
            or self.device_selected.get("product_code")
            or ""
        )
        for sn, device in self.api.mqttsession.mqtt_data.items():
            CONSOLE.info(f"{' ' + sn + ' (' + device_pn + ') ':-^100}")
            fields = []
            for key, value in device.items():
                # convert timestamps to readable data and time for printout
                if "timestamp" in key and isinstance(value, int):
                    value = datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
                if key != "topics":
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
        for t in self.found_topics:
            CONSOLE.info(f"{t}")
        CONSOLE.info(f"{100 * '-'}\nReceived Messages:")
        CONSOLE.info(f"{json.dumps(self.api.mqttsession.mqtt_stats.dev_messages)}")

    def print_values(
        self,
        session: AnkerSolixMqttSession,
        topic: str,
        message: Any,
        data: bytes,
        model: str,
        *args,
        **kwargs,
    ) -> None:
        """Print the accumulated and refreshed values including last message timestamp."""
        if topic:
            self.found_topics.add(topic)
        timestamp = ""
        if isinstance(message, dict):
            timestamp = datetime.fromtimestamp(
                (message.get("head") or {}).get("timestamp") or 0
            ).strftime("%Y-%m-%d %H:%M:%S")
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
        self.print_table()
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
        # Parse command line arguments
        arg: argparse.Namespace = parse_arguments()
        # Print configuration when in non-interactive mode
        if arg.device_sn:
            CONSOLE.info("Launch settings:")
            CONSOLE.info(f"  Device SN: {Color.CYAN}{arg.device_sn}{Color.OFF}")
            CONSOLE.info(
                f"  Monitor view: {(Color.GREEN + 'Values') if arg.value_display else (Color.CYAN + 'Messages')}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Real-time trigger: {(Color.GREEN + 'Enabled') if arg.realtime_trigger else (Color.RED + 'Disabled')}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Status request: {(Color.GREEN + 'Enabled') if arg.status_request else (Color.RED + 'Disabled')}{Color.OFF}"
            )
            CONSOLE.info(
                f"  Filedump: {(Color.GREEN + 'Enabled') if arg.filedump else (Color.RED + 'Disabled')}{Color.OFF}"
            )
            if arg.dump_prefix:
                CONSOLE.info(
                    f"  Dump Prefix: {Color.YELLOW}{arg.dump_prefix}{Color.OFF}"
                )
            CONSOLE.info(
                f"  Runtime: {(Color.YELLOW + str(arg.runtime) + ' minutes') if arg.runtime else (Color.CYAN + 'Until cancelled')}{Color.OFF}"
            )
            CONSOLE.info("")
        if not asyncio.run(AnkerSolixMqttMonitor(arg).main(), debug=False):
            CONSOLE.warning("\nAborted!")
    except KeyboardInterrupt:
        CONSOLE.warning("\nAborted!")
    except Exception as exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        CONSOLE.exception("%s: %s", type(exception), exception)
