# Furby DLC Editor

A user-friendly command-line tool for editing Furby Connect DLC (Downloadable Content) files.

This project uses the [ctxis/Furby](https://github.com/ctxis/Furby) library to provide an easy-to-use interface for modifying Furby Connect DLC files, including audio tracks, sprites, animations, and more.

## Features

- 📊 **Inspect DLC files** - View detailed information about DLC structure and contents
- 🎵 **Extract audio tracks** - Export all audio tracks from a DLC file
- 🔄 **Replace audio tracks** - Swap individual audio tracks with custom ones
- 🎨 **Extract sprites** - Export all sprite/cel graphics as PNG images
- 🖼️ **Replace sprites** - Swap individual sprites with custom images from GIF files
- 💾 **Save modifications** - Build modified DLC files ready for use

## Installation

1. Clone this repository:
```bash
git clone https://github.com/benbalter/furby-mcp.git
cd furby-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the editor executable (optional):
```bash
chmod +x dlc_editor.py
```

## Usage

The DLC editor provides several commands for working with DLC files:

### Display DLC Information

View detailed information about a DLC file:

```bash
python dlc_editor.py info path/to/dlc_file.dlc
```

This will display:
- Available sections (PAL, CEL, AMF, APL, SEQ, MTR, LPS, SPR)
- Number of palettes, sprites, audio tracks, animations, etc.

### Extract Audio Tracks

Export all audio tracks from a DLC file:

```bash
python dlc_editor.py extract-audio path/to/dlc_file.dlc -o output_directory/
```

Audio tracks are saved as `.a18` files (GeneralPlus A18 format).

### Extract Sprites

Export all sprite graphics as PNG images:

```bash
# Extract with monochrome palette (default)
python dlc_editor.py extract-sprites path/to/dlc_file.dlc -o output_directory/

# Extract with specific palette number
python dlc_editor.py extract-sprites path/to/dlc_file.dlc -o output_directory/ -p 3
```

### Replace Audio Track

Replace a specific audio track with a new one:

```bash
python dlc_editor.py replace-audio path/to/dlc_file.dlc 5 new_audio.a18 -o modified.dlc
```

Where:
- `5` is the track number to replace (0-indexed)
- `new_audio.a18` is your replacement audio file
- `modified.dlc` is the output file with your changes

### Replace Sprite

Replace a specific sprite with a new image:

```bash
# Replace sprite with a 128x128 indexed GIF
python dlc_editor.py replace-sprite path/to/dlc_file.dlc 10 new_sprite.gif -o modified.dlc

# Replace sprite and add a new palette from another GIF
python dlc_editor.py replace-sprite path/to/dlc_file.dlc 10 new_sprite.gif -o modified.dlc -p palette.gif
```

Where:
- `10` is the sprite number to replace (0-indexed)
- `new_sprite.gif` must be a 128x128 pixel indexed GIF (6-bit color, 64 colors max)
- `-p palette.gif` is optional and extracts a new color palette from the specified GIF
- `modified.dlc` is the output file with your changes

**Note**: Sprites are 64x64 pixels, but the input image must be 128x128 as it gets "quarterized" into the correct format automatically.

## DLC File Format

Furby Connect DLC files contain multiple sections:

- **PAL** - Color palettes for sprites
- **CEL** - Sprite/cel graphics (64x64 pixels, 6-bit color)
- **SPR** - Sprite animation sequences
- **XLS** - Action tree (behavior responses)
- **AMF** - Audio tracks (A18 format)
- **APL** - Audio playlists
- **LPS** - Lip sync phrases
- **SEQ** - Response sequences
- **MTR** - Motor/servo animations

## Audio Format

Audio files must be in GeneralPlus A18 format:
- Sample rate: 16 kHz
- Codec: GeneralPlus A18 (proprietary)

⚠️ **Note**: Converting standard audio formats (MP3, WAV) to A18 requires specialized tools not included in this editor.

## Examples

```bash
# Inspect a DLC file
python dlc_editor.py info tu012700.dlc

# Extract all audio and sprites
python dlc_editor.py extract-audio tu012700.dlc -o audio/
python dlc_editor.py extract-sprites tu012700.dlc -o sprites/

# Replace audio track 10 and save
python dlc_editor.py replace-audio tu012700.dlc 10 custom_sound.a18 -o custom.dlc

# Replace sprite 5 with a custom image
python dlc_editor.py replace-sprite tu012700.dlc 5 my_sprite.gif -o custom.dlc
```

## Credits

- Based on the [ctxis/Furby](https://github.com/ctxis/Furby) reverse engineering work by Ed Locard (@L0C4RD)
- Original research: [Context IS Blog - Don't Feed Them After Midnight](https://www.contextis.com/blog/dont-feed-them-after-midnight-reverse-engineering-the-furby-connect)

## License

This project is provided as-is for educational and research purposes.

**Disclaimer**: This tool is alpha quality. Bad DLC files can make your Furby Connect unhappy. Use at your own risk!

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## See Also

- [ctxis/Furby](https://github.com/ctxis/Furby) - Original Furby DLC research and tools
- [Paul Stone's FurBLE Web Bluetooth Controller](https://github.com/pdjstone/furby-web-bluetooth)
- [Jeija's Bluefluff project](https://github.com/Jeija/bluefluff)
- [Furbhax project](https://github.com/swarley7/furbhax)