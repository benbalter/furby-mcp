# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""The MCP server: tools that find, connect to and control Furby Connects."""

import asyncio
import contextlib
import logging
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
        "Tools that act on a Furby take an optional `furby`: its address, the name of its active DLC, or "
        '"all". Left out, it means the only connected Furby (furby_status and disconnect_furby: all of them).',
        "To make a Furby say or do something, look up the action with find_actions (bluefluff's transcription of "
        "what each stock action says), then play it with trigger_action. A DLC can change what actions play: "
        'input 75 ("app videos") is where custom DLCs usually put their own clips.',
    )
)


def reason(e):
    """An exception's message, or its type when it has none (TimeoutError() says nothing)."""
    return str(e) or type(e).__name__


def failed(f, e):
    """A ToolError the model can act on: the SDK hides other exceptions' text, and TimeoutError has none."""
    return ToolError(f"{f.address}: {reason(e)}. If it fell asleep, wake it and call connect_furby.")


class Furbies:
    """The connected Furbies, by address."""

    def __init__(self, scan=furby.scan, make=furby.Furby):
        self.scan = scan
        self.make = make
        self.connected = {}

    def forget(self, f):
        self.connected.pop(f.address, None)

    def get(self, address):
        return next((f for a, f in self.connected.items() if a.lower() == address.lower()), None)

    def pick(self, which=None):
        """The Furbies a tool should act on: one by address or DLC name, all of them, or the only one."""
        present = [f for f in self.connected.values() if f.connected]
        if not present:
            raise ToolError("No Furby is connected. Wake one (tilt it or pet its head) and call connect_furby.")
        if which is None:
            if len(present) > 1:
                raise ToolError(f"{len(present)} Furbies are connected; say which: {', '.join(self.names())}, or all")
            chosen = present
        elif which.lower() == "all":
            chosen = present
        else:
            chosen = [
                f
                for f in present
                if f.address.lower() == which.lower() or (f.dlc and f.dlc["name"].lower() == which.lower())
            ]
            if not chosen:
                raise ToolError(f"No connected Furby is called {which!r}. Connected: {', '.join(self.names())}")
        flashing = [f.address for f in chosen if f.flashing]
        if flashing:
            raise ToolError(f"{', '.join(flashing)} is being flashed; try again when that's done")
        return chosen

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


async def each(chosen, act):
    """Run act(furby) on every chosen Furby at once; raise the first failure as a ToolError."""
    results = await asyncio.gather(*(act(f) for f in chosen), return_exceptions=True)
    for f, result in zip(chosen, results, strict=True):
        if isinstance(result, ToolError):
            raise result
        if isinstance(result, Exception):
            raise failed(f, result)
    return results


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
        try:
            found = await furbies.scan(timeout)
        except Exception as e:
            raise ToolError(f"Bluetooth scan failed: {reason(e)}. Is Bluetooth on?") from None
        return [{"address": d.address, "rssi": rssi} for d, rssi in found]

    @server.tool(annotations=gentle)
    async def connect_furby(address: str | None = None, timeout: float = 8.0) -> dict:
        """Connect to the Furby with this address, or to every Furby in range that isn't connected yet.

        Returns every connected Furby with its active DLC (None on a stock Furby), and any that
        were found but couldn't be connected.
        """
        if address and furbies.get(address):  # a connected Furby doesn't advertise, so don't scan for it
            return {"connected": [describe(f) for f in furbies.connected.values()], "errors": []}
        try:
            found = [d for d, _ in await furbies.scan(timeout)]
        except Exception as e:
            raise ToolError(f"Bluetooth scan failed: {reason(e)}. Is Bluetooth on?") from None
        if address:
            found = [d for d in found if d.address.lower() == address.lower()]
        found = [d for d in found if not furbies.get(d.address)]
        if not found and not (furbies.connected and not address):
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
                errors.append(f"{device.address}: {reason(e)}")
                continue
            furbies.connected[f.address] = f
            log.info("Connected to %s", f)
        if not furbies.connected:
            raise ToolError("Couldn't connect: " + "; ".join(errors))
        return {"connected": [describe(f) for f in furbies.connected.values()], "errors": errors}

    @server.tool(annotations=gentle)
    async def disconnect_furby(furby: str | None = "all") -> str:
        """Let go of a Furby (default: all of them), so it can sleep or connect to another app."""
        chosen = furbies.pick(furby)
        for f in chosen:
            with contextlib.suppress(Exception):  # gone already is fine
                await f.disconnect()
            furbies.forget(f)
        return f"Disconnected {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=read_only)
    async def furby_status(furby: str | None = "all") -> list[dict]:
        """Each connected Furby's address, antenna colour and stored DLCs (which slot is active, names, checksums)."""

        async def status(f):
            slots = await f.read_dlc()
            return {**describe(f), "slots": slots}

        return await each(furbies.pick(furby), status)

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
        all that), or "no reply" (it probably played; the Furby didn't confirm). With furby="all",
        every Furby plays it at once.
        """
        code = [input, index, subindex, specific]
        try:
            protocol.trigger_command(*code)
        except ValueError as e:
            raise ToolError(str(e)) from None
        entry = actions.describe(code)

        async def play(f):
            try:
                result = await f.play(*code)
            except ValueError as e:  # the Furby says it has no such action
                raise ToolError(f"{f.address}: {e}") from None
            return {"furby": f.address, "action": code, "result": result, "says": entry and entry["says"]}

        return await each(furbies.pick(furby), play)

    @server.tool(annotations=gentle)
    async def set_antenna(red: int, green: int, blue: int, furby: str | None = None) -> str:
        """Set the antenna light's colour, each channel 0-255; 0, 0, 0 turns it off."""
        for value, what in ((red, "red"), (green, "green"), (blue, "blue")):
            try:
                protocol.check_byte(value, what)
            except ValueError as e:
                raise ToolError(str(e)) from None
        chosen = furbies.pick(furby)
        await each(chosen, lambda f: f.set_antenna(red, green, blue))
        return f"Antenna set to ({red}, {green}, {blue}) on {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=gentle)
    async def set_eyes(on: bool, furby: str | None = None) -> str:
        """Turn the eyes' LCD backlight on or off."""
        chosen = furbies.pick(furby)
        await each(chosen, lambda f: f.command(protocol.lcd_command(on)))
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
        await each(chosen, lambda f: f.command(command))
        return f"{'Set' if mode == 'set' else 'Added'} {meter} {value} on {', '.join(f.address for f in chosen)}"

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True))
    async def flash_dlc(path: str, ctx: Context, furby: str | None = None, name: str | None = None) -> dict:
        """Upload a .dlc file to one Furby and make it the active DLC. DELETES every DLC already on that Furby.

        path is an absolute path on the computer running this server. Takes a few minutes (about 4 for
        300 KB); files over 350 KB are refused, since they time out mid-upload. If the call is cancelled
        or times out, the Furby is left with no DLC: flash it again. name is what the Furby stores it as
        (1-8 letters or digits; default: the file's name), and what furby_status reports. The antenna
        turns green when done, red if it failed. Returns the new DLC and the names of those deleted.
        """
        file = Path(path).expanduser()
        if not file.is_absolute():
            raise ToolError(f"Give the full path to the .dlc file, not {path!r}")
        if file.suffix.lower() != ".dlc":
            raise ToolError(f"{file.name} isn't a .dlc file")
        if not file.is_file():
            raise ToolError(f"{file} doesn't exist")
        try:
            protocol.dlc_filename(name or file.stem)
        except ValueError as e:
            raise ToolError(f"{e}; pass name= to store it under another name") from None
        size = file.stat().st_size
        if size > protocol.MAX_UPLOAD:
            raise ToolError(f"{file.name} is {size:,} bytes; uploads over {protocol.MAX_UPLOAD:,} bytes time out")
        chosen = furbies.pick(furby)
        if len(chosen) != 1:
            raise ToolError("Flash one Furby at a time: say which with furby=")
        f = chosen[0]

        async def progress(done, total):
            await ctx.report_progress(done, total, f"Uploading {file.name}")

        try:
            result = await f.flash(file.read_bytes(), name or file.stem, progress=progress)
        except Exception as e:
            raise ToolError(
                f"Flashing {f.address} failed: {reason(e)}. Its old DLCs may be gone; "
                "flash again, and if it keeps failing, reset the Furby and try once more."
            ) from None
        return {"furby": f.address, **result, "bytes": size}

    return server
