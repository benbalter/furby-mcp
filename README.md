# furby-mcp

An [MCP](https://modelcontextprotocol.io) server for [Furby Connect](https://en.wikipedia.org/wiki/Furby#Fourth_generation_(2016–2017)) toys. It lets Claude, or any other MCP client, find Furbies over Bluetooth LE, make them say and do things, light their antennas, and flash custom DLCs to them.

> "Make the Furby laugh, then turn its antenna purple."

It works with more than one Furby at a time, and it knows about 1,500 of the things a stock Furby can say, so you can ask for "something about hot dogs" instead of looking up action codes.

## Tools

| Tool | What it does |
| --- | --- |
| `connect_furby` | Finds and connects to every Furby in range (or one, by address), and reports each one's active DLC, plus any it found but couldn't connect to |
| `scan_furbies` | Lists Furbies in range without connecting |
| `furby_status` | Shows each connected Furby's antenna colour and stored DLCs: slots, names, checksums, which is active |
| `find_actions` | Searches what a stock Furby can say or do ("fart", "sing", "sleepy") and returns the action codes |
| `trigger_action` | Plays an action, on every Furby at once if you ask for all of them. If a Furby is still busy with its last action, it waits and tries again, since a busy Furby plays new actions without sound. It reports whether the sound played |
| `set_antenna` | Sets the antenna light to any RGB colour, or off |
| `set_eyes` | Turns the eyes' backlight on or off |
| `set_mood` | Sets or adds to a mood meter: excitedness, displeasedness, tiredness, fullness, wellness (untested on hardware) |
| `flash_dlc` | Uploads a `.dlc` file and makes it the active DLC. **This deletes every DLC already on that Furby**, and reports which ones it deleted |
| `disconnect_furby` | Lets go of one Furby or all of them |

Tools that act on a Furby take an optional `furby`: its Bluetooth address, the name of its active DLC, or `"all"`. Leave it out to mean the only connected Furby; with several connected, the tool asks which. `furby_status` and `disconnect_furby` default to all of them instead.

## Install

You need [uv](https://docs.astral.sh/uv/), which fetches Python 3.11 or newer if you don't have it. The server isn't on PyPI yet, so for now `uvx` runs it from GitHub:

**Claude Code**

```sh
claude mcp add furby -- uvx --from git+https://github.com/benbalter/furby-mcp furby-mcp
```

**Claude Desktop, and other clients that take a JSON config**

```json
{
  "mcpServers": {
    "furby": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/benbalter/furby-mcp", "furby-mcp"]
    }
  }
}
```

Add `--verbose` after `furby-mcp` to log Bluetooth activity to stderr.

### Bluetooth permission on macOS

macOS asks for Bluetooth permission for the app that starts the server: your terminal for Claude Code, or Claude Desktop. If nothing is ever found, check **System Settings → Privacy & Security → Bluetooth**.

## Using it

1. **Wake the Furby** by tilting it or petting its head. A sleeping Furby doesn't advertise, so it can't be found.
2. **Ask your MCP client to connect**, for example "connect to my Furby". Once connected, the server keeps the Furby awake until you disconnect it.
3. **Ask for things in plain words**: "make it sing", "make both Furbies burp", "turn the antenna off".

**Two Furbies at once.** Two Furby Connects near each other start singing together, and while they do, neither one advertises, so neither can be found. Wake one, connect to it, then wake the next and connect again.

**Addresses.** On Linux and Windows a Furby's address is its Bluetooth MAC address. On macOS it's a UUID that macOS makes up, which differs from one computer to the next.

**Flashing.** A DLC is a Furby's content pack: sounds, eye animations and action sequences.

- **It's slow.** Each 20-byte packet goes out 15 ms after the last, so a 300 KB file takes about 4 minutes (300,000 ÷ 20 × 15 ms ≈ 225 s, plus overhead). Files over 350 KB are refused, since they time out mid-upload.
- **Give it the full path** to a `.dlc` file on the computer running the server.
- **Names are short.** The Furby stores DLCs under 8.3 names, so a DLC's name is 1–8 letters or digits. It defaults to the file's name; pass `name` to pick another.
- **Watch the antenna.** It turns green when the upload is done, red if it failed.
- **Don't cut it off.** The old DLCs are deleted before the upload starts, so a flash that's cancelled or times out leaves the Furby with no DLC: flash it again. Some MCP clients time out long tool calls. In Claude Code, set `MCP_TOOL_TIMEOUT` (in milliseconds) above the flash time, e.g. `MCP_TOOL_TIMEOUT=600000 claude` for 10 minutes.

To build your own DLCs, see [ctxis/Furby](https://github.com/ctxis/Furby) and [benbalter/Furby](https://github.com/benbalter/Furby).

**What a DLC changes.** A DLC only changes what plays when an action is triggered over Bluetooth. The Furby's own reactions to being petted, tilted or fed come from its built-in memory, whatever DLC is active. Custom DLCs usually put their clips on input 75 ("app videos").

## What's tested on real Furbies

The following ran on real Furby Connects in [benbalter/Furby](https://github.com/benbalter/Furby), whose `furbyshow.py` and `flash.py` this server's Bluetooth code is ported from: triggering actions and the busy-Furby retry, the antenna, the keepalive, reading DLC slots, and flashing. That repo keeps its own copy, written to also run on MicroPython on an ESP32.

These come from [bluefluff](https://github.com/Jeija/bluefluff)'s and [PyFluff](https://github.com/martinwoodward/PyFluff)'s documentation and haven't been tried with this server: mood meters, and the replies that say an action code doesn't exist.

The server itself is tested against a simulated Furby (`tests/fake.py`), not yet end to end with a real one.

## Development

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Credits

- [bluefluff](https://github.com/Jeija/bluefluff) by Florian Euchner reverse-engineered the Furby Connect's Bluetooth protocol. Its community-transcribed [action list](https://github.com/Jeija/bluefluff/blob/master/doc/actionlist.md) ships unchanged in [`src/furby_mcp/data/actionlist.md`](src/furby_mcp/data/actionlist.md) under its MIT license ([`BLUEFLUFF-LICENSE.md`](src/furby_mcp/data/BLUEFLUFF-LICENSE.md)), and powers `find_actions`.
- [PyFluff](https://github.com/martinwoodward/PyFluff) by Martin Woodward, a Python port of bluefluff with its own MCP server, documented the mood meter command.
- [FurBLE](https://github.com/pdjstone/furby-web-bluetooth) by Paul Stone is the browser app whose upload sequence the flashing follows.

Furby and Furby Connect are trademarks of Hasbro. This project isn't affiliated with or endorsed by Hasbro.

## License

[MIT](LICENSE)
