"""Anker Solix MQTT class to handle an MQTT server client connection session for an account."""

from base64 import b64decode, b64encode
from collections.abc import Callable
import contextlib
from datetime import datetime
import json
import os
from pathlib import Path
import ssl
import tempfile
from typing import Any

import aiofiles
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .apitypes import (
    DeviceHexData,
    DeviceHexDataField,
    DeviceHexDataHeader,
    DeviceHexDataTypes,
)
from .session import AnkerSolixClientSession

MessageCallback = Callable[[Any, Any], None]


class AnkerSolixMqttSession:
    """Define the class to handle an MQTT client for Anker MQTT server connection."""

    def __init__(self, apisession: AnkerSolixClientSession) -> None:
        """Initialize."""
        self._message_callback: MessageCallback | None = None
        self._temp_cert_files: list[tempfile.NamedTemporaryFile] = []
        self._logger = apisession.logger()
        # ensure folder for certificate file caching exists
        self._auth_cache_dir = Path(__file__).parent / "authcache"
        if not os.access(self._auth_cache_dir.parent, os.W_OK):
            self._auth_cache_dir = Path(tempfile.gettempdir()) / "authcache"
        self._auth_cache_dir.mkdir(parents=True, exist_ok=True)
        self.apisession: AnkerSolixClientSession = apisession
        self.client: mqtt.Client | None = None
        self.mqtt_info: dict = {}
        self.host: str | None = None
        self.port: int = 8883
        self.subscriptions: set = set()

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: mqtt.Any,
        flags: mqtt.ConnectFlags,
        rc: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            self._logger.debug(
                "MQTT client connected successfully to Anker Solix MQTT server"
            )
            # we should always subscribe from on_connect callback to be sure
            # our subscribed is persisted across reconnection.
            for topic in self.subscriptions:
                self.client.subscribe(topic)
        else:
            self._logger.error(
                "MQTT client failed to connect to Anker Solix MQTT server, return code %s",
                rc,
            )

    def on_message(
        self, client: mqtt.Client, userdata: mqtt.Any, msg: mqtt.MQTTMessage
    ):
        """Callback for when a PUBLISH message is received from the server."""
        # default MQTT payload decode is UTF-8
        message = json.loads(msg.payload.decode())
        # Extract timestamp field from expected dictionary in message
        timestamp = (
            (message.get("head") or {}).get("timestamp")
            if isinstance(message, dict)
            else 0
        )
        # extract message payload
        payload = json.loads(message.get("payload") or "")
        model = payload.get("pn") if isinstance(payload, dict) else None
        # Decrypt base64-encoded encrypted data field from expected dictionary in message payload
        data = (
            b64decode(payload.get("data") or "") if isinstance(payload, dict) else None
        )
        self._logger.debug(
            "%sReceived message: %s on topic: %s",
            datetime.fromtimestamp(timestamp).strftime("%Y-%M-%d %H:%M:%S ")
            if timestamp
            else "",
            message,
            msg.topic,
        )
        if self._message_callback:
            self._message_callback(msg.topic, message, data, model)

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: mqtt.Any,
        flags: mqtt.ConnectFlags,
        rc: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ):
        """Callback for when the client disconnects from the server."""
        self._logger.debug("MQTT client disconnected from Anker Solix MQTT server")

    def on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[mqtt.ReasonCode],
        properties: mqtt.Properties | None,
    ):
        """Callback for when the client subscribes to a topic."""
        # Since we subscribe only for a single channel, reason_code_list contains a single entry
        if reason_code_list[0].is_failure:
            self._logger.error(
                "MQTT client received failure while subscribing topic: %s",
                reason_code_list[0],
            )
        else:
            self._logger.debug(
                "MQTT client subscribed to topic with following QoS: %s",
                reason_code_list[0].value,
            )

    def on_unsubscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[mqtt.ReasonCode],
        properties: mqtt.Properties | None,
    ):
        """Callback for when the client unsubscribes from a topic."""
        # The reason_code_list is only present in MQTTv5,in MQTTv3 it will always be empty
        if not reason_code_list or not reason_code_list[0].is_failure:
            self._logger.debug("MQTT client unsubscribed from topic")
        else:
            self._logger.error(
                "MQTT client received failure while unsubscribing topic: %s",
                reason_code_list[0],
            )

    def on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties,
    ):
        """Callback for when the client subscribes to a topic."""
        if reason_code.is_failure:
            self._logger.error(
                "MQTT client received failure while publishing topic: %s",
                reason_code,
            )
        else:
            self._logger.debug(
                "MQTT client published topic with following QoS: %s",
                reason_code.value,
            )

    def message_callback(self, func: MessageCallback | None) -> MessageCallback:
        """Get or set the message callback for this session."""
        if func:
            self._message_callback = func
        return self._message_callback

    def get_topic_prefix(self, deviceDict: dict, publish: bool = False) -> str:
        """Get the MQTT topic prefix for provided device data."""
        topic = ""
        if (
            isinstance(deviceDict, dict)
            and self.mqtt_info
            and (sn := deviceDict.get("device_sn") or "")
            and (
                pn := deviceDict.get("device_pn")
                or deviceDict.get("product_code")
                or ""
            )
        ):
            topic = f"{'cmd' if publish else 'dt'}/{self.mqtt_info.get('app_name')}/{pn}/{sn}/"
        return topic

    def get_command_data(
        self, command: str = "update_trigger", parameters: dict | None = None
    ) -> str | None:
        r"""Compose the hex data for MQTT publish payload to Anker Solix devices.

        -------------------- Publish Header for update trigger -------------------------
        ff 09   : 2 Byte Anker Solix message marker (supposed 'ff 09')
        1f 00   : 2 Byte total message length (31) in Bytes (Little Endian format)
        03 00 0f: 3 Byte fixed message pattern (supposed `03 00 0f` for sending message)
        00 57   : 2 Byte message type pattern (varies per device model and message type)
        -- Fields --|- Value (Hex/Decode Options)---------------------------------------
        Fld Len Typ    uIntLe/var     sIntLe
        a1  01  --  22
        └->   1 unk           34             -> fix
        a2  02  01  01
        └->   2 ui             1             -> Toggle updates on/off
        a3  05  03  2c:01:00:00
        └->   5 var                      300 -> Update timeout in sec
        fe  05  03  c8:d7:b6:68
        └->   5 var               1756813256 -> Unix Timestamp
        --------------------------------------------------------------------------------
        """

        hexdata = None
        if not isinstance(parameters, dict):
            parameters = {}
        if command == "update_trigger":
            hexdata = DeviceHexData(msg_header=DeviceHexDataHeader(cmd_msg="0057"))
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a3"),
                    f_type=DeviceHexDataTypes.var.value,
                    f_value=int(parameters.get("timeout") or 60).to_bytes(
                        length=4, byteorder="little"
                    ),
                )
            )
            hexdata.add_timestamp_field()
        if hexdata:
            self._logger.info("Generated hexdata for device mqtt command '%s':\n%s", command, hexdata.hex(":"))
            return hexdata.hex()
        return None

    def publish(
        self,
        deviceDict: dict,
        hexbytes: bytearray | bytes | str,
        cmd: int = 17,
        sessId: str = "1234-5678",
    ) -> tuple[str, mqtt.MQTTMessageInfo]:
        """Get the MQTT topic prefix for provided device data."""
        # convert parameter as required
        if isinstance(hexbytes, str):
            hexbytes = bytes.fromhex(hexbytes.replace(":", ""))
        message = {
            "head": {
                "version": "1.0.0.1",
                "client_id": f"android-{self.mqtt_info.get('app_name')}-{self.mqtt_info.get('user_id')}-{self.mqtt_info.get('certificate_id')}",
                "sess_id": sessId,  # eg "5681-3252", can this be fix, or can it be obtained from client connection?
                "msg_seq": 1,
                "seed": 1,
                "timestamp": int(datetime.now().timestamp()),
                "cmd_status": 2,
                "cmd": cmd,
                "sign_code": 1,
                "device_pn": (
                    deviceDict.get("device_pn") or deviceDict.get("product_code") or ""
                ),
                "device_sn": (sn := deviceDict.get("device_sn") or ""),
            },
            "payload": json.dumps(
                {
                    "account_id": self.mqtt_info.get("user_id"),
                    "device_sn": sn,
                    # "data": "/wkfAAMADwBXoQEiogIBAaMFAywBAAD+BQPI17ZoIQ==",
                    "data": b64encode(hexbytes).decode("utf-8"),
                },
                separators=(",", ":"),
            ),
        }
        # generate message string and topic
        message = json.dumps(message, separators=(",", ":"))
        topic = f"{self.get_topic_prefix(deviceDict=deviceDict, publish=True)}req"
        # publish the message and return message and response
        return (message, self.client.publish(topic=topic, payload=message))

    def subscribe(self, topic: str) -> tuple[mqtt.MQTTErrorCode, int | None] | None:
        """Add topic to subscription set and subscribe if just added and client is already connected."""
        if topic and topic not in self.subscriptions:
            # Add topic to subscription set to ensure it will be subscribed again on reconnects
            self.subscriptions.add(topic)
            self._logger.info("MQTT session subscribed new topic: %s", topic)
            # subscribe topic if client already connected
            if self.client and self.client.is_connected():
                return self.client.subscribe(topic)
        return None

    def unsubscribe(self, topic: str) -> tuple[mqtt.MQTTErrorCode, int | None] | None:
        """Remove topic from subscription set and unsubscribe if already connected."""
        if topic and topic in self.subscriptions:
            # Remove topic from subscription set to ensure it will not be subscribed again on reconnects
            self.subscriptions.discard(topic)
            self._logger.info("MQTT session unsubscribed topic: %s", topic)
            # unsubscribe topic if client already connected
            if self.client and self.client.is_connected():
                return self.client.unsubscribe(topic)
        return None

    async def connect_client_async(self, keepalive: int = 60) -> mqtt.Client | None:
        """Connect MQTT client, it will optionally being created if none configured yet."""
        if not self.client and not await self.create_client():
            return None
        # TODO: async connection functionality still to be figured out
        # self.client.connect_async(host=self.host, port=self.port, keepalive=keepalive)
        self.client.connect(host=self.host, port=self.port, keepalive=keepalive)
        return self.client

    async def create_client(self) -> mqtt.Client | None:
        """Create and configure MQTT client with SSL/TLS certificates queried from Anker Solix api session."""
        try:
            # get latest mqtt info from api session
            self.mqtt_info = await self.apisession.get_mqtt_info()
            # extract host from info
            self.host = self.mqtt_info.get("endpoint_addr") or None
            if not self.host:
                self.mqtt_info = {}
                self.host = None
                self.client = None
                return self.client
            # Create client instance
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=self.mqtt_info.get("thing_name"),
                clean_session=True,
            )
            # Set userdata for client
            self.client.user_data_set(self.subscriptions)
            # Set callbacks for client
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            self.client.on_subscribe = self.on_subscribe
            self.client.on_unsubscribe = self.on_unsubscribe
            self.client.on_publish = self.on_publish
            # create temporary cert files
            self._temp_cert_files = []
            for certname in [
                "aws_root_ca1_pem",
                "certificate_pem",
                "private_key",
            ]:
                filename = str(
                    self._auth_cache_dir
                    / f"{self.apisession.email}_mqtt_{certname}.crt"
                )
                # remove file if existing
                if Path(filename).is_file():
                    with contextlib.suppress(Exception):
                        Path(filename).unlink()
                # Cache login response in file for reuse
                async with aiofiles.open(filename, "w", encoding="utf-8") as certfile:
                    await certfile.write(self.mqtt_info.get(certname))
                    self._logger.debug("Certificate dumped to file: %s", filename)
                    self._temp_cert_files.append(filename)
            # Configure SSL/TLS using temporary files
            if len(self._temp_cert_files) == 3:
                self.client.tls_set(
                    ca_certs=self._temp_cert_files[0],
                    certfile=self._temp_cert_files[1],
                    keyfile=self._temp_cert_files[2],
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS,
                    ciphers=None,
                )
            else:
                self.client = None
        except Exception:
            # Clean up files if there was an error
            self.cleanup()
            raise
        return self.client

    def cleanup(self):
        """Clean up client connections and delete certificate files."""
        if self.client and self.client.is_connected:
            self.client.disconnect()
        self.client = None
        self.subscriptions = set()
        for filename in self._temp_cert_files:
            # remove file if existing
            if Path(filename).is_file():
                with contextlib.suppress(Exception):
                    Path(filename).unlink()
                    self._logger.debug("MQTT session deleted cert file: %s", filename)
        self._temp_cert_files = []
