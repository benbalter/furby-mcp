#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for Furby DLC Editor
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="furby-dlc-editor",
    version="1.0.0",
    author="Based on work by Ed Locard (@L0C4RD)",
    description="A user-friendly command-line tool for editing Furby Connect DLC files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/benbalter/furby-mcp",
    py_modules=["dlc_editor", "furby", "examples"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "furby-dlc-editor=dlc_editor:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Games/Entertainment",
    ],
    python_requires=">=3.7",
)
