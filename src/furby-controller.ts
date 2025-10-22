import winston from 'winston';
import type * as Noble from '@abandonware/noble';

// Configure winston logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message }) => {
      return `${timestamp} [${level}]: ${message}`;
    })
  ),
  transports: [
    new winston.transports.Console({ level: 'error' }), // Only log errors to stderr
  ],
});

interface FurbyDevice {
  peripheral: Noble.Peripheral;
  generalPlusCharacteristic: Noble.Characteristic;
  nordicCharacteristic: Noble.Characteristic | null;
  name: string;
  uuid: string;
}

export class FurbyController {
  private connectedFurby: FurbyDevice | null = null;
  private scanning = false;
  private noble: typeof Noble | null = null;

  constructor() {
    // Noble will be lazily initialized on first connect
  }

  private async initNoble() {
    if (this.noble) return;
    
    // Dynamically import noble only when needed
    const nobleModule = await import('@abandonware/noble');
    this.noble = nobleModule;
    
    // Set up noble state monitoring
    this.noble.on('stateChange', (state: string) => {
      logger.info(`Bluetooth state changed to: ${state}`);
    });
  }

  /**
   * Connect to a Furby device
   */
  async connect(furbyName?: string): Promise<void> {
    // Initialize noble on first connect
    await this.initNoble();
    
    if (this.connectedFurby) {
      throw new Error('Already connected to a Furby. Disconnect first.');
    }

    if (!this.noble) {
      throw new Error('Failed to initialize Bluetooth');
    }

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.noble!.stopScanning();
        this.scanning = false;
        reject(new Error('Timeout: Could not find Furby device'));
      }, 30000); // 30 second timeout

      this.noble!.on('discover', async (peripheral: Noble.Peripheral) => {
        const name = peripheral.advertisement?.localName || '';
        
        // Check if this is a Furby device
        if (name.includes('Furby') || (!furbyName && name)) {
          if (furbyName && !name.includes(furbyName)) {
            return; // Skip if specific name requested and doesn't match
          }

          clearTimeout(timeout);
          this.noble!.stopScanning();
          this.scanning = false;

          try {
            logger.info(`Connecting to ${name}...`);
            await this.connectToPeripheral(peripheral, name);
            resolve();
          } catch (error) {
            reject(error);
          }
        }
      });

      // Start scanning
      if (this.noble!._state === 'poweredOn') {
        this.noble!.startScanning([], false);
        this.scanning = true;
      } else {
        this.noble!.once('stateChange', (state: string) => {
          if (state === 'poweredOn') {
            this.noble!.startScanning([], false);
            this.scanning = true;
          } else {
            clearTimeout(timeout);
            reject(new Error(`Bluetooth is not available: ${state}`));
          }
        });
      }
    });
  }

  /**
   * Connect to a specific peripheral
   */
  private async connectToPeripheral(peripheral: Noble.Peripheral, name: string): Promise<void> {
    return new Promise((resolve, reject) => {
      peripheral.connect((err: string) => {
        if (err) {
          reject(new Error(`Failed to connect: ${err}`));
          return;
        }

        peripheral.discoverAllServicesAndCharacteristics(
          (err: string, services: Noble.Service[], characteristics: Noble.Characteristic[]) => {
            if (err) {
              reject(new Error(`Failed to discover services: ${err}`));
              return;
            }

            // Find the characteristics we need
            // Based on bluefluff documentation, Furby uses specific UUIDs
            let generalPlusChar: Noble.Characteristic | null = null;
            let nordicChar: Noble.Characteristic | null = null;

            for (const char of characteristics) {
              const uuid = char.uuid.toLowerCase();
              // GeneralPlus characteristic (for commands)
              if (uuid.includes('10b20101')) {
                generalPlusChar = char;
              }
              // Nordic characteristic (for DLC updates)
              if (uuid.includes('10b20201')) {
                nordicChar = char;
              }
            }

            if (!generalPlusChar) {
              peripheral.disconnect();
              reject(new Error('Could not find GeneralPlus characteristic'));
              return;
            }

            this.connectedFurby = {
              peripheral,
              generalPlusCharacteristic: generalPlusChar,
              nordicCharacteristic: nordicChar,
              name,
              uuid: peripheral.uuid,
            };

            logger.info(`Connected to ${name}`);
            resolve();
          }
        );
      });
    });
  }

  /**
   * Disconnect from the current Furby
   */
  async disconnect(): Promise<void> {
    if (!this.connectedFurby) {
      throw new Error('Not connected to any Furby');
    }

    return new Promise((resolve) => {
      this.connectedFurby!.peripheral.disconnect(() => {
        logger.info(`Disconnected from ${this.connectedFurby!.name}`);
        this.connectedFurby = null;
        resolve();
      });
    });
  }

  /**
   * Write data to GeneralPlus characteristic
   */
  private async generalPlusWrite(data: Buffer): Promise<void> {
    if (!this.connectedFurby) {
      throw new Error('Not connected to any Furby');
    }

    return new Promise((resolve, reject) => {
      this.connectedFurby!.generalPlusCharacteristic.write(
        data,
        false,
        (err: string) => {
          if (err) {
            reject(new Error(`Write failed: ${err}`));
          } else {
            resolve();
          }
        }
      );
    });
  }

  /**
   * Set antenna LED color
   */
  async setAntennaColor(red: number, green: number, blue: number): Promise<void> {
    const command = Buffer.from([0x14, red, green, blue]);
    await this.generalPlusWrite(command);
  }

  /**
   * Control LCD backlight
   */
  async setLcdLight(state: boolean): Promise<void> {
    const command = Buffer.from([0xcd, state ? 1 : 0]);
    await this.generalPlusWrite(command);
  }

  /**
   * Perform an action
   */
  async doAction(input: number, index: number, subindex: number, specific: number): Promise<void> {
    const command = Buffer.from([0x13, 0x00, input, index, subindex, specific]);
    await this.generalPlusWrite(command);
  }

  /**
   * Show debug screen
   */
  async showDebugScreen(): Promise<void> {
    const command = Buffer.from([0xdb]);
    await this.generalPlusWrite(command);
  }

  /**
   * Set Furby name
   */
  async setName(nameId: number): Promise<void> {
    // First set the name
    const setNameCmd = Buffer.from([0x21, nameId]);
    await this.generalPlusWrite(setNameCmd);
    
    // Then make Furby say the name
    const sayNameCmd = Buffer.from([0x13, 0x00, 0x21, 0x00, 0x00, nameId]);
    await this.generalPlusWrite(sayNameCmd);
  }

  /**
   * Set mood parameter
   */
  async setMood(action: number, type: number, value: number): Promise<void> {
    const command = Buffer.from([0x23, action, type, value]);
    await this.generalPlusWrite(command);
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connectedFurby !== null;
  }

  /**
   * Get connected Furby info
   */
  getConnectedFurbyInfo(): { name: string; uuid: string } | null {
    if (!this.connectedFurby) {
      return null;
    }
    return {
      name: this.connectedFurby.name,
      uuid: this.connectedFurby.uuid,
    };
  }
}
