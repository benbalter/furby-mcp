# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""
The Furby Connect's Bluetooth protocol: the bytes to send and how to read the replies.

Nothing here touches Bluetooth, so it's all testable without a Furby. The
commands come from Jeija's bluefluff (https://github.com/Jeija/bluefluff),
PyFluff (https://github.com/martinwoodward/PyFluff) and FurBLE
(https://github.com/pdjstone/furby-web-bluetooth). The ones marked "tested"
have run on real Furbies in https://github.com/benbalter/Furby, whose
furbyshow.py and flash.py hold a MicroPython-friendly copy of the same code.
"""

import re
import zlib

# Bluetooth LE characteristics. The Furby has two chips: a GeneralPlus one that
# runs the toy, and a Nordic one that handles the radio and file uploads.
GP_SERVICE = "dab91435-b5a1-e29c-b041-bcd562613bde"
GP_WRITE = "dab91383-b5a1-e29c-b041-bcd562613bde"
GP_LISTEN = "dab91382-b5a1-e29c-b041-bcd562613bde"
NORDIC_WRITE = "dab90757-b5a1-e29c-b041-bcd562613bde"
NORDIC_LISTEN = "dab90756-b5a1-e29c-b041-bcd562613bde"
FILE_WRITE = "dab90758-b5a1-e29c-b041-bcd562613bde"

ADVERTISED_NAME = "Furby"  # what a Furby Connect calls itself when advertising

KEEPALIVE = b"\x20\x06"  # "I'm here": keeps a connected Furby awake and quiet (tested)
KEEPALIVE_S = 3.0  # how often to send it when nothing else has been sent, as FurBLE does
DLC_INFO = b"\x72"  # which slots hold a DLC and which one is active (tested)

# Status notifications (bluefluff's "FurbyMessage", 0x20 xx)
SPEECH_PLAYING = b"\x20\x07"  # still busy: the action runs, but without its audio (tested)
SEQUENCE_PLAYING = b"\x20\x0c"  # the action started, audio and all (tested)
SEQUENCE_CANCELLED = b"\x20\x0d"
SEQUENCE_ENDED = b"\x20\x0e"  # (tested)
# Replies to an action code the Furby doesn't have, per bluefluff (untested)
OUT_OF_RANGE = {
    b"\x20\x0f": "input",
    b"\x20\x10": "index",
    b"\x20\x11": "subindex",
    b"\x20\x12": "specific",
}

# Mood meters (0x23), per bluefluff and PyFluff (untested)
MOODS = ("excitedness", "displeasedness", "tiredness", "fullness", "wellness")

# File transfer modes (0x24 xx), per bluefluff
TRANSFER = {
    1: "FileAlreadyExists",
    2: "ReadyToReceive",
    3: "FileTransferTimeout",
    4: "ReadyToAppend",
    5: "FileReceivedOk",
    6: "FileReceivedErr",
}

CHUNK = 20  # bytes per file packet
MAX_UPLOAD = 350_000  # bigger DLCs time out mid-upload (tested)
SLOTS = 14
DLC_NAME = re.compile(r"[A-Za-z0-9]{1,8}$")


def check_byte(value, what):
    if not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError(f"{what} must be a whole number from 0 to 255, not {value!r}")
    return value


def trigger_command(input, index, subindex, specific):
    """0x13: play one fully specified action, e.g. (1, 0, 0, 0). (tested)"""
    parts = (input, index, subindex, specific)
    for what, value in zip(("input", "index", "subindex", "specific"), parts, strict=True):
        check_byte(value, what)
    return bytes([0x13, 0, *parts])


def antenna_command(red, green, blue):
    """0x14: set the antenna light; (0, 0, 0) turns it off. (tested)"""
    return bytes([0x14, check_byte(red, "red"), check_byte(green, "green"), check_byte(blue, "blue")])


def lcd_command(on):
    """0xcd: turn the eyes' backlight on or off. (tested, as part of flashing)"""
    return bytes([0xCD, 1 if on else 0])


def mood_command(meter, value, add=False):
    """0x23: set a mood meter to value (0-100), or add value to it. (untested)"""
    if meter not in MOODS:
        raise ValueError(f"meter must be one of {', '.join(MOODS)}, not {meter!r}")
    if not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError(f"value must be a whole number from 0 to 100, not {value!r}")
    return bytes([0x23, 0 if add else 1, MOODS.index(meter), value])


def slot_info_command(slot):
    """0x73: the name and checksum of the DLC in a slot. (tested)"""
    return bytes([0x73, slot])


def slots(info):
    """(filled, active) slot numbers from a 0x72 (DLC info) reply. (tested)"""
    filled, active = (info[3] << 8) | info[4], (info[7] << 8) | info[8]
    return [s for s in range(SLOTS) if filled & (1 << s)], [s for s in range(SLOTS) if active & (1 << s)]


def slot_name(info):
    """The DLC name in a 0x73 (slot info) reply, without padding: b'____PINK' → 'PINK'."""
    return bytes(info[2:10]).decode(errors="replace").strip("_\x00 ")


def slot_checksum(info):
    """The Adler-32 checksum in a 0x73 (slot info) reply."""
    return int.from_bytes(bytes(info[13:17]), "big")


def dlc_filename(name):
    """The 8.3 name the Furby stores a DLC under: 'pink' → '____PINK.DLC'."""
    if not DLC_NAME.match(name):
        raise ValueError(
            f"{name!r} won't work as a DLC name: use 1-8 letters or digits, "
            "since the Furby stores it as an 8.3 name (____NAME.DLC)"
        )
    return name.upper().rjust(8, "_") + ".DLC"


def announce_command(size, filename):
    """0x50: the file's size (24-bit, big-endian), slot 2 as FurBLE sends, the name, two zero bytes. (tested)"""
    return bytes([0x50, 0, size >> 16 & 0xFF, size >> 8 & 0xFF, size & 0xFF, 2]) + filename.encode() + b"\0\0"


def checksum(data):
    """The checksum the Furby reports for a stored DLC."""
    return zlib.adler32(data)
