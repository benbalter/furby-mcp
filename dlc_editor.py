#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Furby DLC Editor - A user-friendly command-line tool for editing Furby Connect DLC files

This tool provides an easy-to-use interface for modifying Furby Connect DLC files,
including audio, graphics, animations, and more.
"""

import argparse
import sys
import os
from furby import dlc


class DLCEditor:
    """Main class for the DLC Editor"""
    
    def __init__(self, dlc_file=None):
        """Initialize the DLC editor with an optional DLC file"""
        self.dlc = None
        self.dlc_file = dlc_file
        if dlc_file:
            self.load_dlc(dlc_file)
    
    def load_dlc(self, filepath):
        """Load a DLC file"""
        if not os.path.exists(filepath):
            print(f"Error: File '{filepath}' not found")
            return False
        
        try:
            print(f"Loading DLC file: {filepath}")
            self.dlc = dlc(filepath)
            self.dlc_file = filepath
            print("✓ DLC file loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading DLC file: {e}")
            return False
    
    def info(self):
        """Display information about the loaded DLC"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return
        
        print("\n=== DLC File Information ===")
        
        # Show sections present
        print("\nSections present:")
        for section_name in self.dlc.dlc_sections.keys():
            print(f"  - {section_name}")
        
        # Show detailed info for each section
        if "PAL" in self.dlc.dlc_sections:
            num_palettes = len(self.dlc.dlc_sections["PAL"].palettes)
            print(f"\nPalettes: {num_palettes}")
        
        if "CEL" in self.dlc.dlc_sections:
            num_cels = len(self.dlc.dlc_sections["CEL"].cels)
            print(f"Sprites (CEL): {num_cels}")
        
        if "AMF" in self.dlc.dlc_sections:
            num_tracks = len(self.dlc.dlc_sections["AMF"].tracks)
            print(f"Audio tracks (AMF): {num_tracks}")
        
        if "APL" in self.dlc.dlc_sections:
            num_playlists = len(self.dlc.dlc_sections["APL"].playlists)
            print(f"Audio playlists (APL): {num_playlists}")
        
        if "SEQ" in self.dlc.dlc_sections:
            num_sequences = len(self.dlc.dlc_sections["SEQ"].sequences)
            print(f"Sequences (SEQ): {num_sequences}")
        
        if "MTR" in self.dlc.dlc_sections:
            num_animations = len(self.dlc.dlc_sections["MTR"].animations)
            print(f"Motor animations (MTR): {num_animations}")
        
        if "LPS" in self.dlc.dlc_sections:
            num_phrases = len(self.dlc.dlc_sections["LPS"].phrases)
            print(f"Lip sync phrases (LPS): {num_phrases}")
        
        if "SPR" in self.dlc.dlc_sections:
            num_playlists = len(self.dlc.dlc_sections["SPR"].frame_playlists)
            num_frames = len(self.dlc.dlc_sections["SPR"].frames)
            print(f"Frame playlists (SPR): {num_playlists}")
            print(f"Frames (SPR): {num_frames}")
    
    def extract_audio(self, output_dir):
        """Extract all audio tracks to a directory"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return False
        
        if "AMF" not in self.dlc.dlc_sections:
            print("Error: No audio section (AMF) found in DLC")
            return False
        
        os.makedirs(output_dir, exist_ok=True)
        
        num_tracks = len(self.dlc.dlc_sections["AMF"].tracks)
        print(f"\nExtracting {num_tracks} audio tracks to {output_dir}/")
        
        for i, track in enumerate(self.dlc.dlc_sections["AMF"].tracks):
            output_file = os.path.join(output_dir, f"track_{i:03d}.a18")
            with open(output_file, "wb") as f:
                # Add the GeneralPlus header
                f.write(self.dlc.dlc_sections["AMF"].a18_header.encode('latin-1'))
                # Pad to offset 0x30
                f.write(b'\x00' * (0x30 - len(self.dlc.dlc_sections["AMF"].a18_header)))
                # Write the track data
                f.write(track.encode('latin-1') if isinstance(track, str) else track)
            print(f"  ✓ Extracted track_{i:03d}.a18")
        
        print(f"\n✓ All audio tracks extracted successfully")
        return True
    
    def replace_audio_track(self, track_number, audio_file):
        """Replace a specific audio track"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return False
        
        if "AMF" not in self.dlc.dlc_sections:
            print("Error: No audio section (AMF) found in DLC")
            return False
        
        if not os.path.exists(audio_file):
            print(f"Error: Audio file '{audio_file}' not found")
            return False
        
        try:
            num_tracks = len(self.dlc.dlc_sections["AMF"].tracks)
            if track_number >= num_tracks:
                print(f"Error: Track number {track_number} out of range (0-{num_tracks-1})")
                return False
            
            print(f"Replacing track {track_number} with {audio_file}")
            self.dlc.dlc_sections["AMF"].replace_track(track_number, audio_file)
            print("✓ Audio track replaced successfully")
            return True
        except Exception as e:
            print(f"Error replacing audio track: {e}")
            return False
    
    def extract_sprites(self, output_dir, palette=None):
        """Extract all sprites/cels to PNG files"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return False
        
        if "CEL" not in self.dlc.dlc_sections:
            print("Error: No sprite section (CEL) found in DLC")
            return False
        
        os.makedirs(output_dir, exist_ok=True)
        
        num_cels = len(self.dlc.dlc_sections["CEL"].cels)
        print(f"\nExtracting {num_cels} sprites to {output_dir}/")
        
        if palette is None:
            # Use monochrome palette
            print("Using monochrome palette")
            old_dir = os.getcwd()
            os.chdir(output_dir)
            self.dlc.dump_cels_monochrome()
            os.chdir(old_dir)
        else:
            # Use specified palette
            if "PAL" not in self.dlc.dlc_sections:
                print("Error: No palette section (PAL) found in DLC")
                return False
            
            num_palettes = len(self.dlc.dlc_sections["PAL"].palettes)
            if palette >= num_palettes:
                print(f"Error: Palette {palette} out of range (0-{num_palettes-1})")
                return False
            
            print(f"Using palette {palette}")
            old_dir = os.getcwd()
            os.chdir(output_dir)
            self.dlc.dump_cels(palette)
            os.chdir(old_dir)
        
        print(f"✓ All sprites extracted successfully")
        return True
    
    def replace_sprite(self, sprite_number, image_file, palette_file=None):
        """Replace a specific sprite with an image from a GIF file"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return False
        
        if "CEL" not in self.dlc.dlc_sections:
            print("Error: No sprite section (CEL) found in DLC")
            return False
        
        if not os.path.exists(image_file):
            print(f"Error: Image file '{image_file}' not found")
            return False
        
        try:
            num_cels = len(self.dlc.dlc_sections["CEL"].cels)
            if sprite_number >= num_cels:
                print(f"Error: Sprite number {sprite_number} out of range (0-{num_cels-1})")
                return False
            
            print(f"Replacing sprite {sprite_number} with {image_file}")
            
            # If a palette file is provided, extract and add the palette
            if palette_file:
                if not os.path.exists(palette_file):
                    print(f"Error: Palette file '{palette_file}' not found")
                    return False
                
                print(f"Extracting palette from {palette_file}")
                new_palette = self.dlc.dlc_sections["PAL"].extract_palette(palette_file)
                # Add the new palette if it doesn't exist
                self.dlc.dlc_sections["PAL"].palettes.append(new_palette)
                print(f"✓ Added new palette (index {len(self.dlc.dlc_sections['PAL'].palettes)-1})")
            
            # Quarterize the image into sprite quarters
            new_cels = self.dlc.dlc_sections["CEL"].quarterize(image_file)
            
            if not new_cels:
                print("Error: Failed to process image file. Make sure it's a 128x128 indexed GIF.")
                return False
            
            # Replace the sprite
            self.dlc.dlc_sections["CEL"].cels[sprite_number] = new_cels[0]
            print(f"✓ Sprite {sprite_number} replaced successfully")
            
            if len(new_cels) > 1:
                print(f"Note: Image contained {len(new_cels)} sprite quarters. Only the first one was used.")
                print(f"      To replace multiple sprites, run this command multiple times.")
            
            return True
        except Exception as e:
            print(f"Error replacing sprite: {e}")
            return False
    
    def save_dlc(self, output_file):
        """Save the modified DLC to a new file"""
        if not self.dlc:
            print("Error: No DLC file loaded")
            return False
        
        try:
            print(f"Saving modified DLC to: {output_file}")
            self.dlc.build(output_file)
            print("✓ DLC file saved successfully")
            return True
        except Exception as e:
            print(f"Error saving DLC file: {e}")
            return False


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description="Furby DLC Editor - Edit Furby Connect DLC files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Display information about a DLC file
  %(prog)s info my_dlc.dlc
  
  # Extract all audio tracks
  %(prog)s extract-audio my_dlc.dlc -o audio_output/
  
  # Extract all sprites
  %(prog)s extract-sprites my_dlc.dlc -o sprites_output/
  
  # Replace an audio track
  %(prog)s replace-audio my_dlc.dlc 5 new_audio.a18 -o modified.dlc
  
  # Replace a sprite
  %(prog)s replace-sprite my_dlc.dlc 10 new_sprite.gif -o modified.dlc
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display DLC file information')
    info_parser.add_argument('dlc_file', help='Path to DLC file')
    
    # Extract audio command
    extract_audio_parser = subparsers.add_parser('extract-audio', help='Extract all audio tracks')
    extract_audio_parser.add_argument('dlc_file', help='Path to DLC file')
    extract_audio_parser.add_argument('-o', '--output', required=True, help='Output directory')
    
    # Extract sprites command
    extract_sprites_parser = subparsers.add_parser('extract-sprites', help='Extract all sprites/cels')
    extract_sprites_parser.add_argument('dlc_file', help='Path to DLC file')
    extract_sprites_parser.add_argument('-o', '--output', required=True, help='Output directory')
    extract_sprites_parser.add_argument('-p', '--palette', type=int, help='Palette number to use (default: monochrome)')
    
    # Replace audio command
    replace_audio_parser = subparsers.add_parser('replace-audio', help='Replace an audio track')
    replace_audio_parser.add_argument('dlc_file', help='Path to DLC file')
    replace_audio_parser.add_argument('track_number', type=int, help='Track number to replace')
    replace_audio_parser.add_argument('audio_file', help='Path to new audio file (.a18)')
    replace_audio_parser.add_argument('-o', '--output', required=True, help='Output DLC file')
    
    # Replace sprite command
    replace_sprite_parser = subparsers.add_parser('replace-sprite', help='Replace a sprite/cel')
    replace_sprite_parser.add_argument('dlc_file', help='Path to DLC file')
    replace_sprite_parser.add_argument('sprite_number', type=int, help='Sprite number to replace')
    replace_sprite_parser.add_argument('image_file', help='Path to new image file (128x128 indexed GIF)')
    replace_sprite_parser.add_argument('-o', '--output', required=True, help='Output DLC file')
    replace_sprite_parser.add_argument('-p', '--palette', help='Optional: GIF file to extract palette from')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    editor = DLCEditor()
    
    # Execute the requested command
    if args.command == 'info':
        if editor.load_dlc(args.dlc_file):
            editor.info()
            return 0
        return 1
    
    elif args.command == 'extract-audio':
        if editor.load_dlc(args.dlc_file):
            if editor.extract_audio(args.output):
                return 0
        return 1
    
    elif args.command == 'extract-sprites':
        if editor.load_dlc(args.dlc_file):
            if editor.extract_sprites(args.output, args.palette):
                return 0
        return 1
    
    elif args.command == 'replace-audio':
        if editor.load_dlc(args.dlc_file):
            if editor.replace_audio_track(args.track_number, args.audio_file):
                if editor.save_dlc(args.output):
                    return 0
        return 1
    
    elif args.command == 'replace-sprite':
        if editor.load_dlc(args.dlc_file):
            palette_file = getattr(args, 'palette', None)
            if editor.replace_sprite(args.sprite_number, args.image_file, palette_file):
                if editor.save_dlc(args.output):
                    return 0
        return 1
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
