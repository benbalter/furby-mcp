#!/usr/bin/env node

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { FurbyController } from './furby-controller.js';

// Create MCP server
const server = new McpServer(
  {
    name: 'furby-mcp',
    version: '1.0.0',
    description: 'MCP server for controlling Furby Connect via Bluetooth',
  },
  {
    capabilities: {
      tools: {},
      logging: {},
    },
  }
);

// Initialize Furby controller
const furbyController = new FurbyController();

// Tool: Connect to Furby
server.tool(
  'connect',
  'Connect to a Furby device via Bluetooth',
  {
    name: z.string().optional().describe('Optional: Specific Furby name to connect to'),
  },
  async (args) => {
    try {
      await furbyController.connect(args.name);
      return {
        content: [
          {
            type: 'text',
            text: 'Successfully connected to Furby',
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to connect: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Disconnect from Furby
server.tool(
  'disconnect',
  'Disconnect from the connected Furby device',
  {},
  async () => {
    try {
      await furbyController.disconnect();
      return {
        content: [
          {
            type: 'text',
            text: 'Successfully disconnected from Furby',
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to disconnect: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Set antenna color
server.tool(
  'set_antenna_color',
  'Set the color of Furby\'s antenna LED',
  {
    red: z.number().min(0).max(255).describe('Red LED brightness (0-255)'),
    green: z.number().min(0).max(255).describe('Green LED brightness (0-255)'),
    blue: z.number().min(0).max(255).describe('Blue LED brightness (0-255)'),
  },
  async (args) => {
    try {
      await furbyController.setAntennaColor(args.red, args.green, args.blue);
      return {
        content: [
          {
            type: 'text',
            text: `Set antenna color to RGB(${args.red}, ${args.green}, ${args.blue})`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to set antenna color: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Control LCD backlight
server.tool(
  'set_lcd_light',
  'Turn Furby\'s LCD eye backlight on or off',
  {
    state: z.boolean().describe('True to turn on, false to turn off'),
  },
  async (args) => {
    try {
      await furbyController.setLcdLight(args.state);
      return {
        content: [
          {
            type: 'text',
            text: `LCD backlight turned ${args.state ? 'on' : 'off'}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to set LCD light: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Perform action
server.tool(
  'do_action',
  'Make Furby perform a specific action (move, talk, etc.)',
  {
    input: z.number().min(0).max(255).describe('Action input type'),
    index: z.number().min(0).max(255).describe('Action index'),
    subindex: z.number().min(0).max(255).describe('Action subindex'),
    specific: z.number().min(0).max(255).describe('Specific action'),
  },
  async (args) => {
    try {
      await furbyController.doAction(args.input, args.index, args.subindex, args.specific);
      return {
        content: [
          {
            type: 'text',
            text: `Executed action: input=${args.input}, index=${args.index}, subindex=${args.subindex}, specific=${args.specific}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to perform action: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Show debug screen
server.tool(
  'show_debug_screen',
  'Cycle through Furby\'s LCD eye debug menus',
  {},
  async () => {
    try {
      await furbyController.showDebugScreen();
      return {
        content: [
          {
            type: 'text',
            text: 'Cycled to next debug screen',
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to show debug screen: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Set Furby's name
server.tool(
  'set_name',
  'Set Furby\'s name (0-128)',
  {
    nameId: z.number().min(0).max(128).describe('Name ID (0-128)'),
  },
  async (args) => {
    try {
      await furbyController.setName(args.nameId);
      return {
        content: [
          {
            type: 'text',
            text: `Set Furby name to ID ${args.nameId}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to set name: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Set mood meter
server.tool(
  'set_mood',
  'Set Furby\'s mood parameters',
  {
    type: z.enum(['excited', 'displeased', 'tired', 'fullness', 'wellness']).describe('Mood type'),
    value: z.number().min(0).max(100).describe('Mood value (0-100)'),
    set: z.boolean().optional().default(true).describe('True to set value, false to increment'),
  },
  async (args) => {
    try {
      const typeMap: { [key: string]: number } = {
        excited: 0,
        displeased: 1,
        tired: 2,
        fullness: 3,
        wellness: 4,
      };
      await furbyController.setMood(args.set ? 1 : 0, typeMap[args.type], args.value);
      return {
        content: [
          {
            type: 'text',
            text: `${args.set ? 'Set' : 'Changed'} ${args.type} to ${args.value}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to set mood: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Tool: Get list of available actions
server.tool(
  'list_actions',
  'Get a list of some common Furby actions',
  {},
  async () => {
    const actions = [
      { name: 'Yawn', input: 0, index: 0, subindex: 0, specific: 0 },
      { name: 'Sneeze', input: 0, index: 1, subindex: 0, specific: 0 },
      { name: 'Giggle', input: 0, index: 2, subindex: 0, specific: 0 },
      { name: 'Sing', input: 0, index: 3, subindex: 0, specific: 0 },
    ];
    
    return {
      content: [
        {
          type: 'text',
          text: 'Common Furby actions:\n' + actions.map(a => 
            `- ${a.name}: input=${a.input}, index=${a.index}, subindex=${a.subindex}, specific=${a.specific}`
          ).join('\n'),
        },
      ],
    };
  }
);

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  // Log to stderr since stdout is used for MCP communication
  console.error('Furby MCP server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error in main():', error);
  process.exit(1);
});
