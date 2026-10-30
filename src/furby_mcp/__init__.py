# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""An MCP server for Furby Connect toys, over Bluetooth LE."""

import argparse
import logging
from importlib.metadata import version

__version__ = version("furby-mcp")


def main():
    parser = argparse.ArgumentParser(prog="furby-mcp", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--verbose", "-v", action="store_true", help="log Bluetooth activity to stderr")
    args = parser.parse_args()
    # stderr, never stdout: on the stdio transport stdout is the MCP channel
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(name)s: %(message)s")

    from .server import create_server

    create_server().run()
