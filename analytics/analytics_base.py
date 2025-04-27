# analytics/analytics_base.py
"""
Base Analytics class to handle data fetching, plotting, and embedding in a Tkinter frame.
Subclasses should implement fetch_data() and create_figure().
All plots are styled for dark/night mode.
"""
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
    Applies a dark theme to all Matplotlib figures.
    """
    DARK_BG = '#2e3440'      # Figure background
    AXIS_BG = '#3b4252'      # Axes background
    FG_COLOR = '#eceff4'     # Text and tick color

    def __init__(self, db_path: str, title: str = None):
        self.db_path = db_path
        self.title = title or self.__class__.__name__

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Query the database and return a pandas DataFrame.
        """
        pass

    @abstractmethod
    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """
        Given a DataFrame, return a Matplotlib Figure object.
        """
        pass

    def render(self, parent: ttk.Frame, **kwargs):
        """
        Fetches data, creates the figure, applies dark theme, and embeds it in the Tkinter frame.
        """
        # clear existing widgets
        for w in parent.winfo_children():
            w.destroy()

        try:
            df = self.fetch_data(**kwargs)
            if df.empty:
                messagebox.showinfo(self.title, "No data available for the selected criteria.")
                return
            fig = self.create_figure(df, **kwargs)
        except Exception as e:
            messagebox.showerror(self.title, str(e))
            return

        # apply dark/night mode styling
        fig.patch.set_facecolor(self.DARK_BG)
        for ax in fig.axes:
            ax.set_facecolor(self.AXIS_BG)
            ax.tick_params(colors=self.FG_COLOR, labelcolor=self.FG_COLOR)
            ax.xaxis.label.set_color(self.FG_COLOR)
            ax.yaxis.label.set_color(self.FG_COLOR)
            ax.title.set_color(self.FG_COLOR)

        # embed the Matplotlib figure into Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
