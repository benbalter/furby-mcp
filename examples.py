#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example usage of the Furby DLC Editor

This script demonstrates how to use the DLC editor both as a command-line tool
and as a Python library.
"""

from dlc_editor import DLCEditor
import os


def example_cli_usage():
    """
    Examples of using the DLC editor from the command line
    """
    print("=" * 60)
    print("Command-Line Usage Examples")
    print("=" * 60)
    
    examples = [
        ("Display DLC information", 
         "python dlc_editor.py info my_dlc.dlc"),
        
        ("Extract all audio tracks",
         "python dlc_editor.py extract-audio my_dlc.dlc -o audio_output/"),
        
        ("Extract sprites with monochrome palette",
         "python dlc_editor.py extract-sprites my_dlc.dlc -o sprites_output/"),
        
        ("Extract sprites with specific palette",
         "python dlc_editor.py extract-sprites my_dlc.dlc -o sprites_output/ -p 3"),
        
        ("Replace audio track 5",
         "python dlc_editor.py replace-audio my_dlc.dlc 5 new_audio.a18 -o modified.dlc"),
    ]
    
    for description, command in examples:
        print(f"\n{description}:")
        print(f"  $ {command}")
    
    print()


def example_library_usage():
    """
    Examples of using the DLC editor as a Python library
    """
    print("=" * 60)
    print("Python Library Usage Examples")
    print("=" * 60)
    
    print("""
# Example 1: Load and inspect a DLC file
from dlc_editor import DLCEditor

editor = DLCEditor()
editor.load_dlc("my_dlc.dlc")
editor.info()

# Example 2: Extract all audio tracks
editor.load_dlc("my_dlc.dlc")
editor.extract_audio("audio_output/")

# Example 3: Extract all sprites
editor.load_dlc("my_dlc.dlc")
editor.extract_sprites("sprites_output/", palette=3)

# Example 4: Replace an audio track and save
editor.load_dlc("my_dlc.dlc")
editor.replace_audio_track(5, "new_audio.a18")
editor.save_dlc("modified.dlc")

# Example 5: Direct manipulation using furby library
from furby import dlc

# Load DLC
D = dlc("./my_dlc.dlc")

# Replace audio for action code 75-0-0-0
D.replace_audio((75,0,0,0), ["audio1.a18", "audio2.a18"])

# Extract all sprites using palette 4
D.dump_cels(4)

# Save modified DLC
D.build("modified.dlc")
""")


def example_advanced_usage():
    """
    Examples of advanced DLC manipulation
    """
    print("=" * 60)
    print("Advanced Usage Examples")
    print("=" * 60)
    
    print("""
# Working with specific DLC sections
from furby import dlc

D = dlc("./my_dlc.dlc")

# Access color palettes
palettes = D.dlc_sections["PAL"].palettes
print(f"Number of palettes: {len(palettes)}")

# Access sprites
sprites = D.dlc_sections["CEL"].cels
print(f"Number of sprites: {len(sprites)}")

# Access audio tracks
tracks = D.dlc_sections["AMF"].tracks
print(f"Number of audio tracks: {len(tracks)}")

# Access audio playlists
playlists = D.dlc_sections["APL"].playlists
print(f"Number of playlists: {len(playlists)}")

# Access animation sequences
sequences = D.dlc_sections["SEQ"].sequences
print(f"Number of sequences: {len(sequences)}")

# Access motor animations
animations = D.dlc_sections["MTR"].animations
print(f"Number of motor animations: {len(animations)}")

# Replace a specific audio track
D.dlc_sections["AMF"].replace_track(9, "my_track.a18")

# Minify audio (for testing)
D.dlc_sections["AMF"].minify_audio()

# Extract a palette from a GIF
new_palette = D.dlc_sections["PAL"].extract_palette("my_gif.gif")
D.dlc_sections["PAL"].palettes[5] = new_palette

# Quarterize a GIF into sprites
new_cels = D.dlc_sections["CEL"].quarterize("my_128x128.gif")
D.dlc_sections["CEL"].cels[5] = new_cels[0]

# Save all changes
D.build("modified.dlc")
""")


def main():
    """Main function"""
    print("\n")
    print("*" * 60)
    print("  Furby DLC Editor - Usage Examples")
    print("*" * 60)
    print("\n")
    
    example_cli_usage()
    print("\n")
    example_library_usage()
    print("\n")
    example_advanced_usage()
    print("\n")
    
    print("=" * 60)
    print("For more information:")
    print("  - See README.md")
    print("  - Run: python dlc_editor.py --help")
    print("  - Original library: https://github.com/ctxis/Furby")
    print("=" * 60)
    print("\n")


if __name__ == '__main__':
    main()
