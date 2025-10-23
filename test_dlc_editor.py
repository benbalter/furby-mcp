#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the DLC Editor
"""

import unittest
import os
import tempfile
import shutil
from dlc_editor import DLCEditor


class TestDLCEditor(unittest.TestCase):
    """Test cases for the DLC Editor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.editor = DLCEditor()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_editor_initialization(self):
        """Test that the editor initializes correctly"""
        self.assertIsNotNone(self.editor)
        self.assertIsNone(self.editor.dlc)
        self.assertIsNone(self.editor.dlc_file)
    
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist"""
        result = self.editor.load_dlc("nonexistent.dlc")
        self.assertFalse(result)
        self.assertIsNone(self.editor.dlc)
    
    def test_info_without_loading(self):
        """Test info command without loading a DLC"""
        # Should not crash, just print an error
        self.editor.info()
        self.assertIsNone(self.editor.dlc)
    
    def test_extract_audio_without_loading(self):
        """Test extract audio without loading a DLC"""
        result = self.editor.extract_audio(self.temp_dir)
        self.assertFalse(result)
    
    def test_extract_sprites_without_loading(self):
        """Test extract sprites without loading a DLC"""
        result = self.editor.extract_sprites(self.temp_dir)
        self.assertFalse(result)
    
    def test_replace_audio_without_loading(self):
        """Test replace audio without loading a DLC"""
        result = self.editor.replace_audio_track(0, "fake.a18")
        self.assertFalse(result)
    
    def test_save_without_loading(self):
        """Test save without loading a DLC"""
        output_file = os.path.join(self.temp_dir, "output.dlc")
        result = self.editor.save_dlc(output_file)
        self.assertFalse(result)


class TestFurbyModule(unittest.TestCase):
    """Test cases for the furby module"""
    
    def test_import_furby(self):
        """Test that the furby module can be imported"""
        try:
            from furby import dlc
            self.assertIsNotNone(dlc)
        except ImportError as e:
            self.fail(f"Failed to import furby module: {e}")
    
    def test_dlc_class_exists(self):
        """Test that the dlc class exists"""
        from furby import dlc
        self.assertTrue(hasattr(dlc, '__init__'))


if __name__ == '__main__':
    unittest.main()
