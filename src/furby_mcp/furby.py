# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""
One Furby Connect over Bluetooth LE, with bleak.

Logs go to the "furby_mcp" logger, never stdout: on the stdio transport,
stdout is the MCP channel, and a stray print would corrupt it.
"""

import asyncio
import contextlib
import logging
import time

import anyio
from bleak import BleakClient, BleakScanner

from . import protocol

log = logging.getLogger("furby_mcp")

PLAY_REPLY_S = 1.0  # a Furby answers a trigger within about 0.1 s
PLAY_PATIENCE_S = 25.0  # the longest stock sequences run about 21 s
MAX_UNACKED = 10  # the Furby only acks while packets keep arriving, so don't pause below this
MAX_PAUSE_S = 2.0
CHECKSUM_READS = 4  # times to read a fresh upload's checksum, a second apart


class ChecksumMismatch(RuntimeError):
    """The stored DLC's checksum isn't the file's."""


async def scan(timeout=8.0):
    """Furbies advertising in range, as (device, rssi) pairs, without connecting."""
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    return [
        (device, adv.rssi)
        for device, adv in found.values()
        if (device.name or adv.local_name or "").startswith(protocol.ADVERTISED_NAME)
    ]


class Furby:
    """A connected Furby. Pass a bleak BLEDevice (or address), or a client for tests."""

    def __init__(self, device, client=None, on_disconnect=None):
        if client is None:
            client = BleakClient(device, timeout=20.0, disconnected_callback=lambda _: self._disconnected())
        self.client = client
        self.address = getattr(device, "address", device)
        self.on_disconnect = on_disconnect
        self.waiting = []  # [prefixes, reply, event] for commands awaiting a reply
        self.last_sent = time.monotonic()
        self.antenna = None  # the colour last set, or None if unknown
        self.dlc = None  # the active DLC's {"slot", "name", "checksum"}, or None
        self.busy = asyncio.Lock()  # one action or flash at a time per Furby
        self.flashing = False  # other tools refuse to touch a Furby while this is set
        self.unacked = 0
        self.caught_up = asyncio.Event()
        self.recheck_s = 1.0
        self._keepalive = None

    def __str__(self):
        return self.address

    @property
    def connected(self):
        return self.client.is_connected

    def _disconnected(self):
        log.info("%s disconnected", self)
        if self.on_disconnect:
            self.on_disconnect(self)

    async def connect(self):
        await self.client.connect()
        try:
            await self.client.start_notify(protocol.GP_LISTEN, lambda _, data: self.on_response(bytes(data)))
            await self.client.start_notify(protocol.NORDIC_LISTEN, lambda _, data: self.on_nordic(bytes(data)))
            await self.read_dlc()
        except Exception:
            await self.client.disconnect()
            raise
        self._keepalive = asyncio.create_task(self.keep_alive())

    async def disconnect(self):
        if self._keepalive:
            self._keepalive.cancel()
        await self.client.disconnect()

    def on_response(self, data):
        for entry in self.waiting:
            if entry[1] is None and any(data.startswith(p) for p in entry[0]):
                entry[1] = data
                entry[2].set()

    def on_nordic(self, data):
        if data[:1] == b"\x09":  # packet ack: how many packets the Furby has buffered
            self.unacked = data[1]
            if self.unacked <= MAX_UNACKED:
                self.caught_up.set()

    def listen(self, expect):
        """Start catching the next reply that starts with expect (or any prefix in a tuple of them).

        Listen before sending whatever prompts the reply, or a quick one is lost.
        """
        prefixes = [bytes(p) for p in (expect if isinstance(expect, tuple) else (expect,))]
        entry = [prefixes, None, asyncio.Event()]
        self.waiting.append(entry)
        return entry

    def unlisten(self, entry):
        if entry in self.waiting:
            self.waiting.remove(entry)

    async def wait(self, entry, timeout):
        """The reply entry caught, waiting up to timeout seconds for it."""
        try:
            async with asyncio.timeout(timeout):
                await entry[2].wait()
            return entry[1]
        finally:
            self.unlisten(entry)

    async def command(self, data, expect=None, timeout=5.0):
        """Send data (None sends nothing) and, given expect, return the reply that starts with it."""
        entry = self.listen(expect) if expect else None
        try:
            if data is not None:
                self.last_sent = time.monotonic()
                await self.client.write_gatt_char(protocol.GP_WRITE, bytes(data), response=False)
            if entry:
                return await self.wait(entry, timeout)
        finally:
            if entry:
                self.unlisten(entry)

    async def keep_alive(self):
        while self.connected:
            if not self.busy.locked() and time.monotonic() - self.last_sent > protocol.KEEPALIVE_S:
                try:
                    await self.command(protocol.KEEPALIVE)
                except Exception as e:
                    log.warning("Keepalive to %s failed: %s", self, e)
            await asyncio.sleep(1)

    async def read_slots(self):
        """[{"slot", "name", "checksum", "active"}] for each slot holding a DLC."""
        filled, active = protocol.slots(await self.command(protocol.DLC_INFO, expect=protocol.DLC_INFO))
        out = []
        for slot in filled:
            prefix = protocol.slot_info_command(slot)
            info = await self.command(prefix, expect=prefix)
            out.append(
                {
                    "slot": slot,
                    "name": protocol.slot_name(info),
                    "checksum": f"{protocol.slot_checksum(info):#010x}",
                    "active": slot in active,
                }
            )
        return out

    async def read_dlc(self, attempts=3):
        """Note the active DLC, or None. A stock Furby has none, which is fine.

        Retries, since a sensor report arriving at the same moment can crowd out the reply.
        """
        for attempt in range(attempts):
            try:
                stored = await self.read_slots()
                break
            except TimeoutError:
                if attempt == attempts - 1:
                    raise
        self.dlc = next(({k: s[k] for k in ("slot", "name", "checksum")} for s in stored if s["active"]), None)
        return stored

    async def play(self, input, index, subindex, specific, patience_s=PLAY_PATIENCE_S):
        """Trigger an action. Returns "played", "silent" or "no reply".

        A sequence's movement and eye animation often outlast its sound, by up
        to 20 s. A Furby still running one answers a new trigger with 20:07 and
        plays the action without audio. So on 20:07, wait for the running
        sequence to end (20:0e) and trigger again, until patience_s runs out.
        """
        command = protocol.trigger_command(input, index, subindex, specific)
        async with self.busy:
            return await self._play(command, patience_s)

    async def _play(self, command, patience_s):
        expect = (protocol.SEQUENCE_PLAYING, protocol.SPEECH_PLAYING, *protocol.OUT_OF_RANGE)
        end = time.monotonic() + patience_s
        while True:
            # A busy Furby can send 20:0e right after 20:07, so listen for it from the start
            ended = self.listen((protocol.SEQUENCE_ENDED, protocol.SEQUENCE_CANCELLED))
            try:
                try:
                    reply = await self.command(command, expect=expect, timeout=PLAY_REPLY_S)
                except TimeoutError:
                    return "no reply"
                if reply[:2] == protocol.SEQUENCE_PLAYING:
                    return "played"
                if reply[:2] in protocol.OUT_OF_RANGE:
                    raise ValueError(f"this Furby has no action with that {protocol.OUT_OF_RANGE[reply[:2]]}")
                left = end - time.monotonic()
                if left <= 0:
                    return "silent"
                with contextlib.suppress(TimeoutError):  # 20:0e can still go missing, so don't wait long
                    await self.wait(ended, min(left, 2.0))
            finally:
                self.unlisten(ended)

    async def set_antenna(self, red, green, blue):
        self.antenna = None  # unknown until the write goes through
        await self.command(protocol.antenna_command(red, green, blue))
        self.antenna = (red, green, blue)

    async def nordic(self, data):
        await self.client.write_gatt_char(protocol.NORDIC_WRITE, bytes(data), response=False)

    async def clear_slots(self):
        """Delete the stored DLCs, so a new one gets a slot (instead of a tongue-and-tail reset).

        Returns the names of the DLCs it deleted.
        """
        stored = await self.read_slots()
        for entry in stored:
            if entry["active"]:
                await self.command([0x62, entry["slot"]], expect=b"\xdc")  # deactivate
        for entry in stored:
            await self.command([0x74, entry["slot"]], expect=b"\x74")
            log.info("Deleted %s from slot %d of %s", entry["name"], entry["slot"], self)
        self.dlc = None
        return [entry["name"] for entry in stored]

    async def transfer_mode(self, entry, timeout):
        reply = await self.wait(entry, timeout)
        return reply[1] if len(reply) > 1 else None

    async def upload(self, data, filename, packet_delay, progress):
        await self.command(protocol.lcd_command(False))  # eyes off while uploading, as FurBLE does
        await self.set_antenna(0, 0, 0)
        await self.nordic([0x09, 1, 0])  # packet acks on
        ready = done = None
        try:
            ready = self.listen(b"\x24")
            await self.command(protocol.announce_command(len(data), filename))
            mode = await self.transfer_mode(ready, 10)
            if mode != 2:
                raise RuntimeError(f"the Furby answered the upload with {protocol.TRANSFER.get(mode, mode)}")
            done = self.listen(b"\x24")  # FileReceivedOk can follow the last packet at once
            for pos in range(0, len(data), protocol.CHUNK):
                if self.unacked > MAX_UNACKED:
                    self.caught_up.clear()
                    try:  # it only acks while packets arrive, so carry on after a while regardless
                        async with asyncio.timeout(MAX_PAUSE_S):
                            await self.caught_up.wait()
                    except TimeoutError:
                        self.unacked = 0
                await self.client.write_gatt_char(protocol.FILE_WRITE, data[pos : pos + protocol.CHUNK], response=False)
                await asyncio.sleep(packet_delay)
                if pos % (protocol.CHUNK * 500) == 0:
                    await progress(pos, len(data))
            await progress(len(data), len(data))
            mode = await self.transfer_mode(done, 60)
            if mode != 5:
                raise RuntimeError(f"upload failed: {protocol.TRANSFER.get(mode, mode)}")
        finally:
            for entry in (ready, done):
                if entry:
                    self.unlisten(entry)
            # Even if the tool call is cancelled: otherwise the eyes stay dark and acks stay on
            with anyio.CancelScope(shield=True), contextlib.suppress(Exception):
                await self.nordic([0x09, 0, 0])
                await self.command(protocol.lcd_command(True))

    async def activate(self, checksum):
        filled, active = protocol.slots(await self.command(protocol.DLC_INFO, expect=protocol.DLC_INFO))
        new = [s for s in filled if s not in active]
        if not new:
            raise RuntimeError("the upload finished but no slot holds it; reset the Furby and try again")
        slot = new[0]
        for old in active:
            await self.command([0x62, old], expect=b"\xdc")
        # Once, on a real Furby, a fresh upload of the right size reported the
        # previous DLC's checksum straight after FileReceivedOk, so look again
        # before calling it a mismatch.
        prefix = protocol.slot_info_command(slot)
        for _ in range(CHECKSUM_READS):
            stored = protocol.slot_checksum(await self.command(prefix, expect=prefix))
            if stored == checksum:
                break
            await asyncio.sleep(self.recheck_s)
        else:
            raise ChecksumMismatch(f"stored checksum {stored:#x} doesn't match the file's {checksum:#x}")
        await self.command([0x60, slot], expect=b"\xdc")
        await self.command([0x61], expect=b"\xdc")
        await self.read_dlc()
        if not self.dlc or self.dlc["slot"] != slot:
            raise RuntimeError(f"the Furby didn't activate slot {slot}")

    async def flash(self, data, name, packet_delay=0.015, progress=None):
        """Replace every DLC on this Furby with data, stored as name, and make it the active one.

        Turns the antenna green when done, red if anything failed, including the tool
        call being cancelled. Returns the new DLC and the names of the ones it deleted.
        """

        async def no_progress(done, total):
            pass

        progress = progress or no_progress
        filename = protocol.dlc_filename(name)
        if len(data) > protocol.MAX_UPLOAD:
            raise ValueError(f"{len(data):,} bytes is too big: uploads over {protocol.MAX_UPLOAD:,} bytes time out")
        checksum = protocol.checksum(data)
        async with self.busy:
            self.flashing = True
            try:
                deleted = await self.clear_slots()
                for attempt in range(2):
                    if attempt:
                        await self.clear_slots()
                    await self.upload(data, filename, packet_delay, progress)
                    try:
                        await self.activate(checksum)
                        break
                    except ChecksumMismatch as e:
                        if attempt:
                            raise
                        log.warning("%s stored the wrong checksum (%s); uploading again", self, e)
                await self.set_antenna(0, 255, 0)
            except BaseException:  # cancellation too: the old DLCs are gone either way, so show it
                with anyio.CancelScope(shield=True), contextlib.suppress(Exception):
                    await self.set_antenna(255, 0, 0)
                raise
            finally:
                self.flashing = False
        return {"dlc": self.dlc, "deleted": deleted}
