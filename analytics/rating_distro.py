import sqlite3
import pandas as pd
import numpy as np
from tkinter import ttk
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class RatingDistribution(AnalyticsBase):
    """
    Shows a histogram of album ratings (1–10) for the selected filter.
    Adds personalized summary below the chart.
    """
    def fetch_data(self, artist: str = None, genre: str = None, decade: str = None) -> pd.Series:
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT Rating, Artist, Genres, Release_Date FROM albums", conn
            )
            conn.close()

            # Convert Rating to numeric, drop NaNs
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
            df = df.dropna(subset=['Rating'])

            # Apply filters
            if artist and artist != 'All':
                df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
            if genre:
                df = df[df['Genres'].fillna('').str.contains(genre, na=False, regex=False)]
            if decade and decade != 'All':
                df['year'] = pd.to_numeric(
                    df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0],
                    errors='coerce'
                )
                start = int(decade.rstrip('s'))
                df = df[df['year'].between(start, start + 9)]

            # Return empty Series if no data
            if df.empty:
                return pd.Series(dtype=float)

            return df['Rating']

        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.Series(dtype=float)

    def create_figure(self, data: pd.Series, **kwargs) -> Figure:
        bins = np.arange(0.5, 11.5, 1)  # Bin edges for ratings 1-10
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(1, 1, 1)
        counts, edges, patches = ax.hist(data, bins=bins, edgecolor='black')

        # Set tick positions
        mids = (edges[:-1] + edges[1:]) / 2
        ax.set_xticks(mids)
        ax.set_xticklabels([str(int(m)) for m in mids])
        ax.set_xlim(edges[0], edges[-1])
        ax.set_ylim(bottom=0)
        ax.set_xlabel('Rating')
        ax.set_ylabel('Count')
        ax.set_title(self.title)
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)  # Add gridlines for better readability
        fig.tight_layout()
        return fig

    def render(self, parent: ttk.Frame, **kwargs):
        super().render(parent, **kwargs)

        # Locate stats box
        stats_box = next(
            (c for c in parent.winfo_children()
             if isinstance(c, ttk.LabelFrame) and c.cget('text') == 'Additional Analysis'),
            None
        )
        if stats_box is None:
            return

        data = self.fetch_data(**kwargs)
        total = int(data.count())
        avg = data.mean() if total > 0 else 0
        common = int(data.mode()[0]) if not data.mode().empty else None
        counts = data.value_counts() if total > 0 else pd.Series(dtype=int)
        least = int(counts.idxmin()) if not counts.empty else None

        # Clear previous stats using grid_forget to avoid destroying the layout
        for widget in stats_box.winfo_children():
            widget.grid_forget()

        ttk.Label(stats_box, text=f"Total ratings: {total}").grid(anchor='w', padx=5, pady=2)
        ttk.Label(stats_box, text=f"Average rating: {avg:.2f}").grid(anchor='w', padx=5, pady=2)
        if common is not None:
            ttk.Label(stats_box, text=f"Most common rating: {common}").grid(anchor='w', padx=5, pady=2)
        if least is not None:
            ttk.Label(stats_box, text=f"Least common rating: {least}").grid(anchor='w', padx=5, pady=2)
