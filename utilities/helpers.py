# utilities/helpers.py

import os
import sys
import tkinter as tk
from tkinter import messagebox


def format_duration(seconds):
    """Convert seconds to human-readable duration"""
    try:
        seconds = int(seconds)
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}h {mins}m {secs}s"
        elif mins:
            return f"{mins}m {secs}s"
        else:
            return f"{secs}s"
    except Exception:
        return "0s"


def log_message(message, widget=None):
    """Log a message to the terminal or a text widget if provided"""
    if widget and hasattr(widget, 'insert'):
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)
        widget.update_idletasks()
    else:
        print(message)


def validate_csv_structure(file_path):
    """Validate that the CSV file appears to have valid headers"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline()
            return all(field in header.lower() for field in ["artist", "title", "release"])
    except Exception:
        return False


def get_resource_path(relative_path):
    """Get absolute path to resource for bundling with PyInstaller"""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(base_path, relative_path)
    except Exception:
        return relative_path