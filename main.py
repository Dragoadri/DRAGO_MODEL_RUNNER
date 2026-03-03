#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██████╗  █████╗  ██████╗  ██████╗                   ║
║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝ ██╔═══██╗                  ║
║   ██║  ██║██████╔╝███████║██║  ███╗██║   ██║                  ║
║   ██║  ██║██╔══██╗██╔══██║██║   ██║██║   ██║                  ║
║   ██████╔╝██║  ██║██║  ██║╚██████╔╝╚██████╔╝                  ║
║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝                   ║
║                                                               ║
║   MODEL RUNNER // MATRIX EDITION                              ║
║   Local LLM Inference Interface                               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

A Matrix-styled application for managing and running local LLM models
with Ollama. Features include:

  ▶ Load and create models from GGUF files
  ▶ Interactive chat with streaming responses
  ▶ Configurable model parameters
  ▶ Custom system prompts with presets
  ▶ GPU detection and status monitoring

Usage:
    python main.py

Requirements:
    - Python 3.10+
    - Ollama installed and available
    - Dependencies: pip install -r requirements.txt
"""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk

from src.ui import MainWindow
from src.ui.theme import COLORS


def configure_theme():
    """Configure the Matrix dark theme"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # Custom color overrides would go here if customtkinter supported it


def print_banner():
    """Print startup banner"""
    banner = """
\033[32m
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██████╗  █████╗  ██████╗  ██████╗                   ║
║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝ ██╔═══██╗                  ║
║   ██║  ██║██████╔╝███████║██║  ███╗██║   ██║                  ║
║   ██║  ██║██╔══██╗██╔══██║██║   ██║██║   ██║                  ║
║   ██████╔╝██║  ██║██║  ██║╚██████╔╝╚██████╔╝                  ║
║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝                   ║
║                                                               ║
║   MODEL RUNNER // MATRIX EDITION v1.0                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
\033[0m
    """
    print(banner)
    print("\033[32m  ▶ Initializing neural interface...\033[0m")
    print("\033[32m  ▶ Loading configuration...\033[0m")
    print()


def main():
    """Main entry point"""
    print_banner()

    # Configure theme
    configure_theme()

    # Config path
    config_path = Path(__file__).parent / "config" / "default_settings.json"

    print("\033[32m  ▶ Starting UI...\033[0m")
    print()

    # Create and run main window
    # NOTE: tk scaling override is in MainWindow.__init__(), before widget creation
    app = MainWindow(config_path)

    # Handle window close
    def on_closing():
        print("\n\033[32m  ▶ Shutting down...\033[0m")
        print("\033[32m  ▶ Connection terminated.\033[0m\n")
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Start main loop
    app.mainloop()


if __name__ == "__main__":
    main()
