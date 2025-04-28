import sqlite3
import pandas as pd
import tkinter as tk
import re
from tkinter import ttk
from abc import ABC, abstractmethod
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from export.exporters import export_chart_and_insights

class AnalyticsBase(ABC):
    """
    Base class for analytics visualizations, enforcing a consistent container of chart and insights.
    Subclasses implement `fetch_data` and `create_figure`, and may override `_calculate_statistics`.
    """
    def __init__(self, db_path: str, title: str = None):
        self.db_path = db_path
        self.title = title or self.__class__.__name__
        self.fig = None
        self.last_filters = {}

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetch and preprocess data; must return a pandas DataFrame."""
        raise NotImplementedError

    @abstractmethod
    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """Create a Matplotlib Figure from df; must be implemented by subclasses."""
        raise NotImplementedError

    def _calculate_statistics(self, df: pd.DataFrame) -> dict:
        """Basic statistics; override in subclasses for richer metrics."""
        return {'Records': str(len(df))}

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        """Compute insight metrics, defaulting to `_calculate_statistics`."""
        return self._calculate_statistics(df)

    def _render_chart_section(self, parent: ttk.Frame, df: pd.DataFrame):
        """Render the chart area inside a labeled frame."""
        for w in parent.winfo_children():
            w.destroy()
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        canvas = tk.Canvas(vis, bg='#2E2E2E', height=300)
        canvas.pack(fill=tk.BOTH, expand=True)
        h_scroll = ttk.Scrollbar(vis, orient=tk.HORIZONTAL, command=canvas.xview)
        h_scroll.pack(fill=tk.X)
        canvas.configure(xscrollcommand=h_scroll.set)
        inner = ttk.Frame(canvas)
        win = canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, height=e.height))
        self.fig = self.create_figure(df)
        FigureCanvasTkAgg(self.fig, master=inner).get_tk_widget().pack(fill=tk.X)

    def _render_insights_section(self, parent: ttk.Frame, df: pd.DataFrame):
        """Render the insights/statistics area inside a labeled frame."""
        stats = self._calculate_insights(df)
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        cols = min(len(stats), 4)
        for i, (label, value) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            lbl = ttk.Label(info, text=f'{label}: {value}', anchor='w', padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        """Top-level render: wraps chart and insights in a unified container."""
        self.last_filters = kwargs.copy()
        for w in parent.winfo_children():
            w.destroy()
        # Outer container
        container = ttk.Labelframe(parent, text='Chart & Insights')
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # Fetch data
        df = self.fetch_data(**kwargs)
        # Render sections
        self._render_chart_section(container, df)
        if not df.empty:
            self._render_insights_section(container, df)
        return self.fig

    def export_visualization(self, filepath: str):
        """Export current figure and insights to files via export_chart_and_insights."""
        df = self.fetch_data(**self.last_filters)
        stats = self._calculate_insights(df)
        export_chart_and_insights(self.fig, stats, filepath)

    def export(self, export_dir: str, **kwargs) -> str:
        """
        Generalized export method for all analytics classes.
        Exports the visualization figure as a PNG file and insights as a TXT file.
        Returns the base file path (without extension).
        """
        import os

        # Fetch the current filtered data
        df = self.fetch_data(**kwargs)
        if df.empty:
            raise ValueError("No data to export for the given filters.")

        # Create a fresh figure
        fig = self.create_figure(df, **kwargs)
        if fig is None:
            raise ValueError("Figure creation failed, cannot export.")

        # Build a meaningful filename
        base_name = self.title.replace(' ', '_').lower()
        
        filters = []
        for k, v in self.last_filters.items():
            if v and v != 'All':
                safe_v = re.sub(r'[\\\\/:*?"<>|]', '_', v)  # Sanitize illegal characters
                safe_v = safe_v.replace(' ', '_').lower()   # Force lowercase and underscores
                filters.append(f"{k}_{safe_v}")
        
        if filters:
            base_name += "_" + "_".join(filters)
        else:
            base_name += "_all"
        
        # Ensure no double extension
        base_name = os.path.splitext(base_name)[0]

        file_base_path = os.path.join(export_dir, base_name)

        # Save the figure
        fig.savefig(file_base_path + ".png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())

        # Save insights
        insights = self._calculate_insights(df)
        with open(file_base_path + ".txt", 'w', encoding='utf-8') as f:
            for k, v in insights.items():
                f.write(f"{k}: {v}\n")

        return file_base_path