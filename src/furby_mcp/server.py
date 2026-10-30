# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""The MCP server: tools that find, connect to and control Furby Connects."""

import contextlib
import logging
import os
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import actions, furby, protocol

log = logging.getLogger("furby_mcp")

INSTRUCTIONS = "\n\n".join(
    (
        "Controls Furby Connect toys over Bluetooth LE.",
        "Start with connect_furby, which finds and connects to every Furby in range. A Furby has to be awake to "
        "be found: tilt it or pet its head. Two Furby Connects near each other start singing together, and while "
        "they do neither can be found, so wake them one at a time and connect to each before waking the next. "
        "Once connected, a Furby stays awake until disconnect_furby.",
        "Tools that act on a Furby take an optional `furby`: its address, or the name of its active DLC. With one "
        'Furby connected you can leave it out; "all" means every connected Furby.',
        "To make a Furby say or do something, look up the action with find_actions (bluefluff's transcription of "
        "what each stock action says), then play it with trigger_action. A DLC can change what actions play: "
        'input 75 ("app videos") is where custom DLCs usually put their own clips.',
    )
)


class Furbies:
    """The connected Furbies, by address."""

    def __init__(self, scan=furby.scan, make=furby.Furby):
        self.scan = scan
        self.make = make
        self.connected = {}

    def forget(self, f):
        self.connected.pop(f.address, None)

    def pick(self, which=None):
        """The Furbies a tool should act on: one by address or DLC name, all of them, or the only one."""
        present = [f for f in self.connected.values() if f.connected]
        if not present:
            raise ToolError("No Furby is connected. Wake one (tilt it or pet its head) and call connect_furby.")
        if which is None:
            if len(present) > 1:
                raise ToolError(f"{len(present)} Furbies are connected; say which: {', '.join(self.names())}, or all")
            return present
        if which.lower() == "all":
            return present
        found = [
            f
            for f in present
            if f.address.lower() == which.lower() or (f.dlc and f.dlc["name"].lower() == which.lower())
        ]
        if not found:
            raise ToolError(f"No connected Furby is called {which!r}. Connected: {', '.join(self.names())}")
        return found

    def names(self):
        return [f"{f.address} ({f.dlc['name']})" if f.dlc else f.address for f in self.connected.values()]

    async def close(self):
        for f in list(self.connected.values()):
            with contextlib.suppress(Exception):
                await f.disconnect()
        self.connected.clear()


def describe(f):
    return {
        "address": f.address,
        "connected": f.connected,
        "dlc": f.dlc,
        "antenna": list(f.antenna) if f.antenna else None,
    }


def create_server(furbies=None):
    furbies = furbies or Furbies()

    @contextlib.asynccontextmanager
    async def lifespan(_):
        try:
            yield furbies
        finally:
            await furbies.close()

    server = MCPServer("Furby", instructions=INSTRUCTIONS, lifespan=lifespan)
    read_only = ToolAnnotations(read_only_hint=True, open_world_hint=True)
    gentle = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

    @server.tool(annotations=read_only)
    async def scan_furbies(timeout: float = 8.0) -> list[dict]:
        """List the Furby Connects advertising in range, without connecting to them.

        Connected Furbies stop advertising, so they won't appear here; see furby_status.
        """
        return [{"address": d.address, "rssi": rssi} for d, rssi in await furbies.scan(timeout)]

    @server.tool(annotations=gentle)
    async def connect_furby(address: str | None = None, timeout: float = 8.0) -> list[dict]:
        """Connect to the Furby with this address, or to every Furby in range that isn't connected yet.

        Returns each connected Furby with its active DLC (None on a stock Furby).
        """
        found = [d for d, _ in await furbies.scan(timeout)]
        if address:
            found = [d for d in found if d.address.lower() == address.lower()]
        found = [d for d in found if d.address not in furbies.connected]
        if not found:
            if address and address in furbies.connected:
                return [describe(furbies.connected[address])]
            raise ToolError(
                "No Furby found. Wake it by tilting it or petting its head. If two Furbies are on and "
                "singing together, neither can be found: turn one off, connect to the other, then turn it back on."
            )
        errors = []
        for device in found:
            f = furbies.make(device, on_disconnect=furbies.forget)
            try:
                await f.connect()
            except Exception as e:  # asleep, busy, or connected to another app
                errors.append(f"{device.address}: {e or type(e).__name__}")
                continue
            furbies.connected[f.address] = f
            log.info("Connected to %s", f)
        if not furbies.connected:
            raise ToolError("Couldn't connect: " + "; ".join(errors))
        return [describe(f) for f in furbies.connected.values()]

    @server.tool(annotations=gentle)
    async def disconnect_furby(furby: str | None = "all") -> str:
        """Let go of a Furby (default: all of them), so it can sleep or connect to another app."""
        chosen = furbies.pick(furby)
        for f in chosen:
            await f.disconnect()
            furbies.forget(f)
        return f"Disconnected {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=read_only)
    async def furby_status(furby: str | None = "all") -> list[dict]:
        """Each connected Furby's address, antenna colour and stored DLCs (which slot is active, names, checksums)."""
        out = []
        for f in furbies.pick(furby):
            status = describe(f)
            status["slots"] = await f.read_dlc()
            status["dlc"] = f.dlc
            out.append(status)
        return out

    @server.tool(annotations=read_only)
    def find_actions(query: str = "", input: int | None = None, limit: int = 25) -> dict:
        """Search the actions a stock Furby can play by what it says or does, e.g. "fart", "sing", "sleepy".

        Matches every word of query against bluefluff's transcription and category of each action;
        give input to list one group (e.g. 71 for the octave notes). Pass a result's "action" to trigger_action.
        DLCs can change what some actions play, especially input 75.
        """
        found, total = actions.find(query, input=input, limit=max(1, min(limit, 200)))
        return {"total": total, "shown": len(found), "actions": found}

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True))
    async def trigger_action(
        input: int, index: int = 0, subindex: int = 0, specific: int = 0, furby: str | None = None
    ) -> list[dict]:
        """Make a Furby play an action: a sound with movement and eye animation, from its action code.

        A Furby still finishing its last action plays a new one without sound, so this waits for it
        to finish (up to about 25 s) and tries again. "result" is "played", "silent" (still busy after
        all that), or "no reply" (it probably played; the Furby didn't confirm).
        """
        code = [input, index, subindex, specific]
        try:
            protocol.trigger_command(*code)
        except ValueError as e:
            raise ToolError(str(e)) from None
        entry = actions.describe(code)
        out = []
        for f in furbies.pick(furby):
            try:
                result = await f.play(*code)
            except ValueError as e:
                raise ToolError(f"{f.address}: {e}") from None
            out.append({"furby": f.address, "action": code, "result": result, "says": entry and entry["says"]})
        return out

    @server.tool(annotations=gentle)
    async def set_antenna(red: int, green: int, blue: int, furby: str | None = "all") -> str:
        """Set the antenna light's colour, each channel 0-255; 0, 0, 0 turns it off."""
        for value, what in ((red, "red"), (green, "green"), (blue, "blue")):
            try:
                protocol.check_byte(value, what)
            except ValueError as e:
                raise ToolError(str(e)) from None
        chosen = furbies.pick(furby)
        for f in chosen:
            await f.set_antenna(red, green, blue)
        return f"Antenna set to ({red}, {green}, {blue}) on {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=gentle)
    async def set_eyes(on: bool, furby: str | None = "all") -> str:
        """Turn the eyes' LCD backlight on or off."""
        chosen = furbies.pick(furby)
        for f in chosen:
            await f.command(protocol.lcd_command(on))
        return f"Eyes {'on' if on else 'off'} on {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True))
    async def set_mood(
        meter: Literal["excitedness", "displeasedness", "tiredness", "fullness", "wellness"],
        value: int,
        mode: Literal["set", "add"] = "set",
        furby: str | None = None,
    ) -> str:
        """Set one of a Furby's mood meters to value (0-100), or add value to it. Untested on hardware."""
        try:
            command = protocol.mood_command(meter, value, add=mode == "add")
        except ValueError as e:
            raise ToolError(str(e)) from None
        chosen = furbies.pick(furby)
        for f in chosen:
            await f.command(command)
        return f"{'Set' if mode == 'set' else 'Added'} {meter} {value} on {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True))
    async def flash_dlc(path: str, ctx: Context, furby: str | None = None, name: str | None = None) -> dict:
        """Upload a .dlc file to one Furby and make it the active DLC. DELETES every DLC already on that Furby.

        Takes 2-3 minutes for a 300 KB file; files over 350 KB time out. name is what the Furby stores
        it as (1-8 letters or digits; default: the file's name), and what furby_status reports.
        The antenna turns green when done, red if it failed.
        """
        file = Path(os.path.expanduser(path))
        if file.suffix.lower() != ".dlc" or not file.is_file():
            raise ToolError(f"{path} isn't a .dlc file")
        data = file.read_bytes()
        try:
            protocol.dlc_filename(name or file.stem)
        except ValueError as e:
            raise ToolError(f"{e}; pass name= to store it under another name") from None
        if len(data) > protocol.MAX_UPLOAD:
            raise ToolError(f"{file.name} is {len(data):,} bytes; uploads over {protocol.MAX_UPLOAD:,} bytes time out")
        chosen = furbies.pick(furby)
        if len(chosen) != 1:
            raise ToolError("Flash one Furby at a time: say which with furby=")

        async def progress(done, total):
            await ctx.report_progress(done, total, f"Uploading {file.name}")

        try:
            dlc = await chosen[0].flash(data, name or file.stem, progress=progress)
        except Exception as e:
            raise ToolError(f"Flashing failed: {e}. If it keeps failing, reset the Furby and try again.") from None
        return {"furby": chosen[0].address, "dlc": dlc, "bytes": len(data)}

    return server
