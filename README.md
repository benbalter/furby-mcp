# furby-mcp

A Model Context Protocol (MCP) server that allows Copilot and other MCP clients to control a Furby Connect via Bluetooth. This server uses the [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk) and integrates [bluefluff](https://github.com/Jeija/bluefluff) to communicate with Furby Connect toys.

## Features

- 🤖 Control Furby Connect via Bluetooth Low Energy
- 🎨 Change antenna LED colors
- 👁️ Control LCD eye backlight
- 🎭 Set Furby's mood and personality
- 🎪 Trigger actions and movements
- 🔧 Access debug screens
- 📝 Set Furby's name

## Prerequisites

- Node.js 16 or later
- Bluetooth 4.0+ adapter (built-in or USB)
- A Furby Connect toy
- Linux, macOS, or Windows with Bluetooth support

### Linux Requirements

On Debian/Ubuntu-based systems:
```bash
sudo apt install libudev-dev bluetooth bluez
```

Make sure Bluetooth is enabled:
```bash
rfkill unblock bluetooth
sudo systemctl start bluetooth
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/benbalter/furby-mcp.git
cd furby-mcp
```

2. Install dependencies:
```bash
npm install
```

3. Build the project:
```bash
npm run build
```

## Usage

### Running the MCP Server

The server communicates over stdio, which is the standard for MCP servers:

```bash
npm start
```

or directly:

```bash
node dist/index.js
```

### Using with VS Code / Copilot

Add the server to your MCP settings file (typically `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` or similar):

```json
{
  "mcpServers": {
    "furby": {
      "command": "node",
      "args": ["/path/to/furby-mcp/dist/index.js"]
    }
  }
}
```

## Available Tools

The MCP server exposes the following tools:

### Connection Management

- **connect**: Connect to a Furby device
  - Optional parameter: `name` - specific Furby name to connect to
  
- **disconnect**: Disconnect from the connected Furby

### LED Control

- **set_antenna_color**: Set the antenna LED color
  - Parameters: `red`, `green`, `blue` (0-255)

- **set_lcd_light**: Control LCD backlight
  - Parameter: `state` (true/false)

### Actions & Movements

- **do_action**: Make Furby perform actions
  - Parameters: `input`, `index`, `subindex`, `specific`

- **list_actions**: Get a list of common Furby actions

- **show_debug_screen**: Cycle through debug menus

### Personality & Mood

- **set_mood**: Set Furby's mood parameters
  - Parameters: `type` (excited/displeased/tired/fullness/wellness), `value` (0-100), `set` (true/false)

- **set_name**: Set Furby's name
  - Parameter: `nameId` (0-128)

## Example Usage

Once connected through your MCP client (like VS Code with Copilot), you can:

```
"Connect to my Furby"
"Make the antenna glow blue"
"Set the antenna to red=255, green=0, blue=0"
"Make Furby giggle"
"Set Furby's wellness to 100"
"Turn off the LCD backlight"
```

## Development

### Build
```bash
npm run build
```

### Clean
```bash
npm run clean
```

### Development Mode
```bash
npm run dev
```

## Technical Details

This MCP server wraps the bluefluff Furby Connect protocol implementation and exposes it through the Model Context Protocol. It uses:

- **@modelcontextprotocol/sdk**: For MCP server implementation
- **@abandonware/noble**: For Bluetooth Low Energy communication
- **winston**: For logging

The Furby Connect uses Bluetooth Low Energy (BLE) with two main microcontrollers:
- GeneralPlus: Controls movement, LCD eyes, and speech
- Nordic Semiconductor: Handles BLE communication and updates

## Credits

- [bluefluff](https://github.com/Jeija/bluefluff) by Jeija - For reverse engineering the Furby Connect protocol
- [Model Context Protocol](https://github.com/modelcontextprotocol) - For the MCP specification and SDK

## License

MIT

## Disclaimer

This project is for educational purposes. By using this software, you agree to take sole responsibility for any risks associated with interfacing with your Furby Connect. You may void your warranty when using this software. See the bluefluff project for more details.
