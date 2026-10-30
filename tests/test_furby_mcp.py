# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
import asyncio
import json
import os
import sys

import anyio
import pytest
from mcp import Client

from furby_mcp import actions, furby, protocol
from furby_mcp.server import Furbies, create_server

from .fake import FakeClient, FakeDevice

# Made-up bytes: real DLCs are Hasbro's, so none belong in this repo
DLC = bytes(range(256)) * 9


# protocol


def test_commands():
    assert protocol.trigger_command(1, 2, 3, 4) == b"\x13\x00\x01\x02\x03\x04"
    assert protocol.antenna_command(255, 0, 16) == b"\x14\xff\x00\x10"
    assert protocol.lcd_command(False) == b"\xcd\x00"
    assert protocol.mood_command("tiredness", 80) == b"\x23\x01\x02\x50"
    assert protocol.mood_command("wellness", 5, add=True) == b"\x23\x00\x04\x05"
    assert protocol.announce_command(0x012345, "____PINK.DLC") == b"\x50\x00\x01\x23\x45\x02____PINK.DLC\x00\x00"


@pytest.mark.parametrize(
    "bad", [lambda: protocol.trigger_command(256, 0, 0, 0), lambda: protocol.antenna_command(-1, 0, 0),
            lambda: protocol.mood_command("grumpiness", 5), lambda: protocol.mood_command("fullness", 101)]
)  # fmt: skip
def test_bad_values(bad):
    with pytest.raises(ValueError):
        bad()


def test_slots():
    info = bytes([0x72, 0, 0, 0, 0b101, 0, 0, 0, 0b100])
    assert protocol.slots(info) == ([0, 2], [2])


def test_dlc_filename():
    assert protocol.dlc_filename("pink") == "____PINK.DLC"
    for bad in ("toolongname", "pink.dlc", ""):
        with pytest.raises(ValueError):
            protocol.dlc_filename(bad)


# actions


def test_catalog():
    catalog = actions.catalog()
    assert len(catalog) > 1500
    assert catalog[0] == {
        "action": [1, 0, 0, 0],
        "alternatives": [],
        "category": "Generic reactions",
        "says": '"ah-may moh-moh, kah kah more pet!"',
    }


def test_code_lists_and_ranges():
    rows = actions.parse("## 30 - Playing\n|37|0|2,3|0|hi|\n|24|7|0|0 - 2|yawn|\n|38|x|x|x|skip|\n")
    assert [r["action"] for r in rows] == [[37, 0, 2, 0], [24, 7, 0, 0]]
    assert rows[0]["alternatives"] == [[37, 0, 3, 0]]
    assert rows[1]["alternatives"] == [[24, 7, 0, 1], [24, 7, 0, 2]]
    assert rows[0]["category"] == "Playing"


def test_find():
    found, total = actions.find("hot dog")
    assert total >= 2 and all("hot" in a["says"] and "dog" in a["says"] for a in found)
    assert "hot dog" in found[0]["says"]  # whole words rank first
    notes, total = actions.find(input=71)
    assert total == 8 and notes[0]["says"] == '"Do"'
    laughs, _ = actions.find(input=4)  # listed as "3, 4", so found under either
    assert any(a["action"][0] == 3 for a in laughs)
    assert actions.find("zzzqqq") == ([], 0)
    assert actions.describe([1, 0, 0, 0])["category"] == "Generic reactions"
    assert actions.describe([255, 255, 255, 255]) is None


# furby


async def connected(client):
    f = furby.Furby(FakeDevice("AA"), client=client)
    await f.connect()
    return f


async def test_stock_furby_has_no_dlc():
    f = await connected(FakeClient())
    assert f.dlc is None
    await f.disconnect()


async def test_reads_active_dlc():
    f = await connected(FakeClient(stored={0: ("OLD", b"x"), 3: ("PINK", DLC)}, active=3))
    assert f.dlc == {"slot": 3, "name": "PINK", "checksum": f"{protocol.checksum(DLC):#010x}"}
    await f.disconnect()


async def test_play():
    f = await connected(FakeClient())
    assert await f.play(1, 0, 0, 0) == "played"
    await f.disconnect()


async def test_play_waits_out_a_busy_furby():
    client = FakeClient(busy=2)
    f = await connected(client)
    assert await f.play(1, 0, 0, 0) == "played"
    assert sum(c[0] == 0x13 for c in client.sent) == 3
    await f.disconnect()


async def test_play_gives_up_on_a_furby_that_stays_busy():
    client = FakeClient(busy=10**9)
    f = await connected(client)
    assert await f.play(1, 0, 0, 0, patience_s=0.05) == "silent"
    assert sum(c[0] == 0x13 for c in client.sent) > 1  # it waited for each 20:0e and tried again
    await f.disconnect()


async def test_play_without_reply():
    f = await connected(FakeClient(silent=True))
    assert await f.play(1, 0, 0, 0) == "no reply"
    await f.disconnect()


async def test_play_out_of_range():
    f = await connected(FakeClient(missing={73}))
    with pytest.raises(ValueError, match="input"):
        await f.play(73, 0, 0, 0)
    await f.disconnect()


async def test_flash():
    client = FakeClient(stored={0: ("OLD", b"old"), 1: ("OTHER", b"other")}, active=0)
    f = await connected(client)
    progress = []

    async def note(done, total):
        progress.append((done, total))

    result = await f.flash(DLC, "pink", packet_delay=0, progress=note)
    assert result["dlc"]["name"] == "PINK" and list(client.stored.values()) == [("PINK", DLC)]
    assert result["deleted"] == ["OLD", "OTHER"]
    assert f.antenna == (0, 255, 0)
    assert progress[0] == (0, len(DLC)) and progress[-1] == (len(DLC), len(DLC))
    assert client.nordic[-1] == b"\x09\x00\x00" and protocol.lcd_command(True) in client.sent
    await f.disconnect()


async def test_cancelled_flash_cleans_up():
    """A client timeout or Esc cancels the call mid-upload: the Furby must still get its eyes back and go red."""
    client = FakeClient(stored={0: ("OLD", b"old")}, active=0)
    f = await connected(client)
    with anyio.move_on_after(0.05):
        await f.flash(DLC, "pink", packet_delay=0.01)
    assert not f.flashing and not client.stored
    assert client.nordic[-1] == b"\x09\x00\x00"
    assert protocol.lcd_command(True) in client.sent
    assert client.sent[-1] == protocol.antenna_command(255, 0, 0) and f.antenna == (255, 0, 0)
    await f.disconnect()


async def test_flash_refuses_big_files():
    f = await connected(FakeClient())
    with pytest.raises(ValueError, match="too big"):
        await f.flash(b"\0" * (protocol.MAX_UPLOAD + 1), "big")
    await f.disconnect()


# server


def fake_furbies(*clients):
    """Furbies whose scan finds one fake device per client."""
    devices = {f"AA:{i}": client for i, client in enumerate(clients)}

    async def scan(timeout):
        return [(FakeDevice(a), -50) for a, c in devices.items() if not c.is_connected]

    def make(device, on_disconnect=None):
        return furby.Furby(device, client=devices[device.address], on_disconnect=on_disconnect)

    return Furbies(scan=scan, make=make)


async def call(client, tool, **args):
    result = await client.call_tool(tool, args)
    text = result.content[0].text if result.content else ""
    if result.is_error:
        raise AssertionError(text)
    structured = result.structured_content
    if isinstance(structured, dict) and set(structured) == {"result"}:  # a list or str return, wrapped
        return structured["result"]
    return json.loads(text) if text[:1] in "[{" else text


async def error(client, tool, **args):
    result = await client.call_tool(tool, args)
    assert result.is_error, result
    return result.content[0].text


async def test_tools_listed():
    async with Client(create_server()) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"scan_furbies", "connect_furby", "disconnect_furby", "furby_status", "find_actions",
                          "trigger_action", "set_antenna", "set_eyes", "set_mood", "flash_dlc"}  # fmt: skip
    assert tools["flash_dlc"].annotations.destructive_hint
    assert tools["find_actions"].annotations.read_only_hint


async def test_connect_and_play():
    fake = FakeClient(stored={2: ("PINK", DLC)}, active=2)
    async with Client(create_server(fake_furbies(fake))) as client:
        [status] = (await call(client, "connect_furby"))["connected"]
        assert status["dlc"]["name"] == "PINK"
        assert (await call(client, "connect_furby", address="aa:0"))["connected"][0]["address"] == "AA:0"
        [played] = await call(client, "trigger_action", input=1)
        assert played == {"furby": "AA:0", "action": [1, 0, 0, 0], "result": "played",
                          "says": '"ah-may moh-moh, kah kah more pet!"'}  # fmt: skip
        assert "on AA:0" in await call(client, "set_antenna", red=255, green=0, blue=0)
        [status] = await call(client, "furby_status")
        assert status["antenna"] == [255, 0, 0] and status["slots"][0]["active"]
    assert not fake.is_connected  # the lifespan lets go on shutdown


async def test_two_furbies():
    async with Client(
        create_server(fake_furbies(FakeClient(), FakeClient(stored={0: ("BLUE", DLC)}, active=0)))
    ) as client:
        assert len((await call(client, "connect_furby"))["connected"]) == 2
        assert "say which" in await error(client, "trigger_action", input=1)
        [played] = await call(client, "trigger_action", input=1, furby="blue")
        assert played["furby"] == "AA:1"
        assert len(await call(client, "trigger_action", input=1, furby="all")) == 2
        assert "No connected Furby" in await error(client, "set_eyes", on=True, furby="green")
        await call(client, "disconnect_furby", furby="AA:0")
        assert [s["address"] for s in await call(client, "furby_status")] == ["AA:1"]


async def test_helpful_errors():
    async with Client(create_server(fake_furbies())) as client:
        assert "Wake it" in await error(client, "connect_furby")
        assert "No Furby is connected" in await error(client, "set_antenna", red=1, green=2, blue=3)
        assert "0 to 255" in await error(client, "set_antenna", red=300, green=0, blue=0)
        assert "doesn't exist" in await error(client, "flash_dlc", path="/nonexistent.dlc")
        assert "isn't a .dlc" in await error(client, "flash_dlc", path="/etc/hosts")
        assert "full path" in await error(client, "flash_dlc", path="pink.dlc")


async def test_bluetooth_errors_reach_the_model():
    fake = FakeClient()
    async with Client(create_server(fake_furbies(fake))) as client:
        await call(client, "connect_furby")

        async def broken(*args, **kwargs):
            raise TimeoutError()

        fake.write_gatt_char = broken
        assert "AA:0: TimeoutError. If it fell asleep" in await error(client, "set_eyes", on=False)


async def test_flash_tool(tmp_path):
    path = tmp_path / "spooky.dlc"
    path.write_bytes(DLC)
    fake = FakeClient()
    async with Client(create_server(fake_furbies(fake))) as client:
        await call(client, "connect_furby")
        long = tmp_path / "toolongname.dlc"
        long.write_bytes(DLC)
        assert "8.3" in await error(client, "flash_dlc", path=str(long))
        flashing = asyncio.create_task(call(client, "flash_dlc", path=str(path)))
        await asyncio.sleep(0.2)
        assert "being flashed" in await error(client, "set_eyes", on=True)
        flashed = await flashing
        assert flashed["dlc"]["name"] == "SPOOKY" and flashed["deleted"] == []
    assert list(fake.stored.values()) == [("SPOOKY", DLC)]


async def test_stdio_keeps_stdout_clean():
    """Over stdio, stdout is the MCP channel: every line on it must be JSON-RPC, or the session breaks."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "furby_mcp", "--verbose",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},  # so a stray print shows up at once, not at exit
    )  # fmt: skip
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "find_actions", "arguments": {"query": "hiccup", "limit": 1}}},
    ]  # fmt: skip
    proc.stdin.write(b"".join(json.dumps(m).encode() + b"\n" for m in messages))
    await proc.stdin.drain()
    lines = []
    try:
        async with asyncio.timeout(20):
            while not any(m.get("id") == 2 for m in lines):
                line = await proc.stdout.readline()
                assert line, "the server exited early"
                lines.append(json.loads(line))  # fails on anything that isn't JSON
    finally:
        proc.kill()
        await proc.wait()
    assert all(m["jsonrpc"] == "2.0" for m in lines)
    assert "hiccup" in json.dumps(lines[-1]).lower()
