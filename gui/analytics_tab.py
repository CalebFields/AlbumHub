# gui/analytics_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
from gui.ranker_tab import RankerTab
from analytics.average_ratings import AverageRatings

class AnalyticsTab:
    """
    A tab for analytics visualizations with filter support.
    """
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        self.filter_helper = None

    def setup_analytics_tab(self):
        # Create the tab frame and add to the notebook
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Analytics")

        # Main container inside the tab
        container = ttk.Frame(frame, style="TFrame")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- Artist Filter Controls borrowed from RankerTab ---
        filter_frame = ttk.LabelFrame(container, text="Filter by Artist")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Use RankerTab's filter setup
        self.filter_helper = RankerTab(self.app, self.notebook)
        self.filter_helper.setup_filter_controls(filter_frame)

        # Bind filter_var changes to redraw chart
        try:
            self.filter_helper.filter_var.trace_add('write', self._on_filter_change)
        except Exception:
            pass

        # Chart area
        self.chart_frame = ttk.Frame(container)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        # Initial draw
        self._draw_chart()

    def _on_filter_change(self, *args):
        self._draw_chart()

    def _draw_chart(self):
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Get selected artist filter from filter_var
        artist_filter = None
        if self.filter_helper and hasattr(self.filter_helper, 'filter_var'):
            artist_filter = self.filter_helper.filter_var.get()
            if artist_filter == "All":
                artist_filter = None

        # Instantiate and render the chart
        chart = AverageRatings(self.app.database.db_name, title="Average Ratings")
        chart.render(self.chart_frame, artist=artist_filter)
