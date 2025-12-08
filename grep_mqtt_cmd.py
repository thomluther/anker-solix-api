"""Extract Anker Solix MQTT command messages from an mqtt_monitor dump file and compare status message before and after the message for differences.

Before using this module, you need to update the definitions below with dump filename and status message types that should be
compared before and after non excluded message types are found and printed. Preferably you should produce an MQTT dump file,
where you have realtime trigger enabled with status messages prior and after the command message, and you should toggle only
one setting in the Anker mobile App to identify the the command message type that is used for this setting.
The comparison after the setting changes will help to identify the fields and bytes that reflect the setting change in the
status messages. Certain diff lines can be excluded from printing if they often have changes, like power fields, timestamps etc.
"""

# Based on https://gist.github.com/soxofaan/e97112c4789ee74e1bf61532c998c0eb
# Code licensed MIT  2023 Stefaan Lippens

from collections.abc import Iterator
from dataclasses import dataclass
import difflib
import itertools
import logging
from pathlib import Path

import common

# use Console logger from common module
CONSOLE: logging.Logger = common.CONSOLE

# define screen width for diff lines
screen_width = 180
# define filename to be verified
test_file = Path(__file__).parent / "mqttdumps" / "A1763" / "CMD.AC.Smart.Modus.txt"
#test_file = Path(__file__).parent / "mqttdumps" / "A17C0_mqtt_dump_2025_14_02__22_14_35.txt"
# define messages that should not be printed
excluded_msgs = ["0421","0900", "0057", "0040", "0857", "0901", "0902", "0903"] # A1763
#excluded_msgs = ["405", "0057", "0040", "0857"] # Solarbank
# define status message types that should be compared after a printed message
compare_msg = "0421"
#compare_msg = "0405"
# define words in lines that should be excluded in found differences
skip_diff_words = ["fd  ", "fe  ", "timestamp"]


@dataclass
class Message:
    """Define Message class."""

    msg: list
    type: str
    count: int


class Sdiffer:
    """Define Sdiffer class."""

    def __init__(
        self,
        max_width: int = 80,
        skip_match: bool = False,
        skip_words: list | None = None,
    ) -> None:
        """Define class initiator."""
        # Two columns with a gutter
        self._col_width = (max_width - 3) // 2
        assert self._col_width > 0
        self.skip_match = skip_match
        self.skip_words = skip_words or []

    def _fit(self, s: str) -> str:
        s = s.rstrip()[: self._col_width]
        return f"{s: <{self._col_width}}"

    def sdiff(self, a: list[str], b: list[str]) -> Iterator[str]:
        """Verify differences."""
        diff_lines = difflib.Differ().compare(a, b)
        diff_table: list[tuple[str, list[str], list[str]]] = []
        for diff_type, line_group in itertools.groupby(
            diff_lines, key=lambda ln: ln[:1]
        ):
            lines = [ln[2:] for ln in line_group]
            if diff_type == " " and not self.skip_match:
                diff_table.append((" ", lines, lines))
            else:
                if not diff_table or diff_table[-1][0] != "|":
                    diff_table.append(("|", [], []))
                if diff_type == "-":
                    # Lines only in `a`
                    diff_table[-1][1].extend(lines)
                elif diff_type == "+":
                    # Lines only in `b`
                    diff_table[-1][2].extend(lines)

        for diff_type, cell_a, cell_b in diff_table:
            for left, right in itertools.zip_longest(cell_a, cell_b, fillvalue=""):
                if not [
                    word for word in self.skip_words if (word in left or word in right)
                ]:
                    for row in range(
                        int(
                            max(
                                len(left) // self._col_width,
                                len(right) // self._col_width,
                            )
                        )
                        + 1
                    ):
                        yield (
                            f"{self._fit(left[row * self._col_width : (row + 1) * self._col_width + 1])} {diff_type} "
                            f"{self._fit(right[row * self._col_width : (row + 1) * self._col_width + 1])}"
                        )

    def print_sdiff(self, a: list[str], b: list[str]) -> Iterator[str]:
        """Print differences."""
        CONSOLE.info("\n".join(self.sdiff(a, b)))


def search_for_msg(messagelist: list, t: str) -> str | bool:
    """Search for the next message of given type."""
    for msg in messagelist:
        if msg.type == t:
            return msg
    return False


# main part

with Path.open(test_file, encoding="utf-8") as f:
    file_text = f.readlines()

headers = []
for line in file_text:
    ll = line.strip()
    if " / Header ------" in ll:
        headers.append(ll[59:63])
for h in sorted(set(headers)):
    CONSOLE.info(h)

messages = []
message = []
count = 0
read = False
for line in file_text:
    ll = line.strip()
    if " / Header ------" in ll:
        message = [ll]
        message_type = ll.split("/")[2].strip()
        read = True
    elif "Received message on topic:" in ll and len(message) > 1:
        # remove last extra line
        if not str(message[-1:]).startswith("----"):
            message.pop()
        messages.append(Message(message, message_type, count))
        read = False
        count += 1
    elif read:
        message.append(ll)

last_status = False
for m in messages:
    t1 = m.type
    if t1 == compare_msg:
        last_status = m
    if t1 not in excluded_msgs:
        # print messages not excluded
        CONSOLE.info("\n".join(m.msg))
        if last_status:
            next_status = search_for_msg(messages[last_status.count + 1 :], compare_msg)
            if next_status:
                CONSOLE.info(f"Found differences in: {compare_msg}")
                Sdiffer(
                    screen_width, skip_match=True, skip_words=skip_diff_words
                ).print_sdiff(last_status.msg[7:], next_status.msg[7:])
