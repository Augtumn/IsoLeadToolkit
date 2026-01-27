"""
Progress Dialog
Lightweight feedback window for long operations.
"""
import tkinter as tk
from tkinter import ttk

from core.localization import translate as t


class ProgressDialog:
    """Simple indeterminate progress dialog"""

    def __init__(self, title_key="Loading Data", message_key="Reading file..."):
        self.root = tk.Tk()
        self.root.title(t(title_key))
        self.root.geometry("420x160")
        self.root.minsize(380, 140)
        self.root.resizable(False, False)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        self.label = ttk.Label(frame, text=t(message_key), anchor=tk.W)
        self.label.pack(fill=tk.X, pady=(0, 10))

        self.bar = ttk.Progressbar(frame, mode="indeterminate")
        self.bar.pack(fill=tk.X)
        self.bar.start(10)
        self.root.update_idletasks()

    def update_message(self, message_key):
        try:
            self.label.configure(text=t(message_key))
            self.root.update_idletasks()
        except Exception:
            pass

    def close(self):
        try:
            self.bar.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
