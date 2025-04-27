import sqlite3
import pandas as pd
from abc import ABC, abstractmethod
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AnalyticsBase(ABC):
    """
    Abstract base class for analytics visualizations.
    Applies the application's dynamically-configured dark theme to Matplotlib figures.
    """
    def __init__(self, db_path: str, title: str = None):
        self.db_path = db_path
        self.title = title or self.__class__.__name__

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Query the database and return a pandas DataFrame."""
        pass

    @abstractmethod
    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """Given a DataFrame, return a Matplotlib Figure object."""
        pass
    
    def render(self, parent: ttk.Frame, **kwargs):
        if parent is None:
            return  # Nothing to render into, so just safely exit
    
        # Clear parent without deleting the parent itself
        for w in parent.winfo_children():
            w.destroy()
    
        # fetch data
        df = self.fetch_data(**kwargs)
        if df.empty:
            messagebox.showinfo(self.title, "No data available.")
            return

        fig = self.create_figure(df)

        # apply dark theme
        style = ttk.Style()
        fig.patch.set_facecolor(style.lookup('TFrame','background') or '#2E2E2E')
        for ax in fig.axes:
            ax.set_facecolor(style.lookup('Treeview','fieldbackground') or '#333333')
            ax.tick_params(colors=style.lookup('TLabel','foreground') or '#FFFFFF',
                           labelcolor=style.lookup('TLabel','foreground') or '#FFFFFF')
            ax.xaxis.label.set_color(style.lookup('TLabel','foreground') or '#FFFFFF')
            ax.yaxis.label.set_color(style.lookup('TLabel','foreground') or '#FFFFFF')
            ax.title.set_color(style.lookup('TLabel','foreground') or '#FFFFFF')

        # embed Matplotlib figure
        canvas = FigureCanvasTkAgg(fig, master=parent)
        widget = canvas.get_tk_widget()
        widget.pack(fill=tk.BOTH, expand=True)

        # layout adjustment
        widget.update_idletasks()
        w, h = widget.winfo_width(), widget.winfo_height()
        dpi = fig.get_dpi()
        fig.set_size_inches(w/dpi, h/dpi, forward=True)
        fig.tight_layout()

        canvas.draw()

        # additional analysis
        stats_box = ttk.LabelFrame(parent, text="Additional Analysis")
        stats_box.pack(fill=tk.X, pady=(10, 0), padx=5)
        # placeholder

    