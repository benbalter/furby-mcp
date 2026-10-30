# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""A stand-in for a Furby behind bleak's client API, answering the way real ones do."""

import asyncio

from furby_mcp import protocol


class FakeDevice:
    def __init__(self, address):
        self.address = address
        self.name = "Furby"


class FakeClient:
    """Answers GeneralPlus commands like a Furby Connect, from the replies seen on real ones.

    busy: how many triggers to answer with 20:07 (speech playing) before 20:0c.
    stored: {slot: (name, data)} DLCs already on it; active: the active slot or None.
    """

    def __init__(self, busy=0, stored=None, active=None, silent=False, missing=()):
        self.busy = busy
        self.stored = dict(stored or {})
        self.active = active
        self.silent = silent  # never answers a trigger
        self.missing = missing  # action inputs it answers with "input out of range"
        self.is_connected = False
        self.listeners = {}
        self.sent = []  # GeneralPlus commands, in order
        self.upload = None  # [expected size, bytearray, name] during a file transfer
        self.nordic = []  # Nordic commands, in order

    async def connect(self, timeout=None):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def start_notify(self, uuid, callback):
        self.listeners[uuid] = callback

    def reply(self, data, uuid=protocol.GP_LISTEN):
        # At once, before the write returns: the fastest a real Furby could answer, so code
        # that only starts listening after sending a command misses the reply here too
        self.listeners[uuid](None, bytearray(data))

    async def write_gatt_char(self, uuid, data, response=False):
        await asyncio.sleep(0)  # a real write yields, which is where cancellation lands
        data = bytes(data)
        if uuid == protocol.FILE_WRITE:
            self.upload[1] += data
            if len(self.upload[1]) >= self.upload[0]:
                slot = min(set(range(protocol.SLOTS)) - set(self.stored))
                self.stored[slot] = (self.upload[2], bytes(self.upload[1]))
                self.reply(b"\x24\x05")
            return
        if uuid == protocol.NORDIC_WRITE:
            self.nordic.append(data)
            return
        self.sent.append(data)
        op = data[0]
        if op == 0x13:
            if self.silent:
                return
            if data[2] in self.missing:
                self.reply(b"\x20\x0f")
            elif self.busy:
                self.busy -= 1
                self.reply(protocol.SPEECH_PLAYING)
                self.reply(protocol.SEQUENCE_ENDED)
            else:
                self.reply(protocol.SEQUENCE_PLAYING)
        elif op == 0x72:
            filled = sum(1 << s for s in self.stored)
            active = 1 << self.active if self.active is not None else 0
            self.reply(bytes([0x72, 0, 0, filled >> 8, filled & 0xFF, 0, 0, active >> 8, active & 0xFF]))
        elif op == 0x73:
            name, dlc = self.stored[data[1]]
            self.reply(
                bytes([0x73, data[1]])
                + name.rjust(8, "_").encode()
                + b"DLC"
                + protocol.checksum(dlc).to_bytes(4, "big")
            )
        elif op == 0x74:
            self.stored.pop(data[1], None)
            self.reply(bytes([0x74, data[1]]))
        elif op == 0x62:
            self.active = None
            self.reply(b"\xdc")
        elif op == 0x60:
            self.loaded = data[1]
            self.reply(b"\xdc")
        elif op == 0x61:
            self.active = self.loaded
            self.reply(b"\xdc")
        elif op == 0x50:
            size = int.from_bytes(data[2:5], "big")
            self.upload = [size, bytearray(), data[6:14].decode().strip("_")]
            self.reply(b"\x24\x02")
