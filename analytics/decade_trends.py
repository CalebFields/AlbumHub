import sqlite3
import pandas as pd
from tkinter import ttk
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase

class DecadeTrends(AnalyticsBase):
    """
    Shows average rating per decade as a line chart with robust year parsing.
    """
    def fetch_data(self,
                   artist: str = None,
                   genre: str = None,
                   decade: str = None) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Release_Date, Genres, Rating FROM albums", conn
        )
        conn.close()

        # Drop rows missing date or rating, convert Rating to numeric
        df = df.dropna(subset=['Release_Date'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])

        # Extract year and compute decade
        df['year'] = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0]
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df.dropna(subset=['year'])
        df['decade'] = (df['year'] // 10 * 10).astype(int).astype(str) + 's'

        # Filters
        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre:
            df = df[df['Genres'].fillna('').str.contains(genre, na=False, regex=False)]
        if decade and decade != 'All':
            df = df[df['decade'] == decade]

        # Return empty DataFrame if no data for base.render to handle
        if df.empty:
            return pd.DataFrame(columns=['decade', 'avg_rating'])

        # Compute average rating per decade
        result = (
            df.groupby('decade')['Rating']
              .mean()
              .reset_index(name='avg_rating')
              .sort_values('decade')
        )
        return result

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(df['decade'], df['avg_rating'], marker='o')
        ax.set_xlabel('Decade')
        ax.set_ylabel('Average Rating')
        ax.set_title(self.title)
        ax.tick_params(axis='x', rotation=45)
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

        # Fetch filtered data
        df = self.fetch_data(**kwargs)
        total_decades = df.shape[0]
        overall_avg = df['avg_rating'].mean() if total_decades > 0 else 0

        # Clear previous stats
        for w in stats_box.winfo_children():
            w.destroy()

        # Display summary
        ttk.Label(
            stats_box,
            text=f"Data covers {total_decades} decades."
        ).pack(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Average rating across decades: {overall_avg:.2f}."
        ).pack(anchor='w', padx=5, pady=2)

        if total_decades > 0:
            highest = df.loc[df['avg_rating'].idxmax()]
            lowest = df.loc[df['avg_rating'].idxmin()]
            ttk.Label(
                stats_box,
                text=f"Highest-rated decade: {highest['decade']} ({highest['avg_rating']:.2f})."
            ).pack(anchor='w', padx=5, pady=2)
            ttk.Label(
                stats_box,
                text=f"Lowest-rated decade: {lowest['decade']} ({lowest['avg_rating']:.2f})."
            ).pack(anchor='w', padx=5, pady=2)
