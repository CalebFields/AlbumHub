import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class DecadeTrends(AnalyticsBase):
    """
    Shows average rating per decade with a linear trend line and concise insights,
    styled to match the app's dark theme and boxed layout.
    """
    def fetch_data(self, artist=None, genre=None, decade=None, **kwargs) -> pd.DataFrame:
        """Fetch ratings, compute decades, apply optional filters."""
        self.last_filters = {'artist': artist, 'genre': genre, 'decade': decade}
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Release_Date, Genres, Rating FROM albums", conn
        )
        conn.close()

        df = df.dropna(subset=['Release_Date', 'Rating', 'Artist'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])
        df['year'] = (
            df['Release_Date'].astype(str)
              .str.extract(r"(\d{4})")[0]
              .astype(float, errors='ignore')
        )
        df = df.dropna(subset=['year'])
        df['decade'] = (df['year'] // 10 * 10).astype(int).astype(str) + 's'

        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre and genre != 'All':
            df = df[df['Genres'].fillna('').str.contains(genre, na=False, regex=False)]
        if decade and decade != 'All':
            df = df[df['decade'] == decade]

        if df.empty:
            return pd.DataFrame(columns=['decade', 'avg_rating', 'count', 'mid_year'])

        return (
            df.groupby('decade', observed=True)
              .agg(avg_rating=('Rating', 'mean'),
                   count=('Rating', 'size'),
                   mid_year=('year', 'mean'))
              .reset_index()
              .sort_values('decade')
        )

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """Build a dark-themed line chart with trend line."""
        fig = Figure(figsize=(10, 5), constrained_layout=True)
        ax = fig.add_subplot(111)
        decades = df['decade']
        ratings = df['avg_rating']
        ax.plot(decades, ratings,
                marker='o', linewidth=2, color='#4B72B8', markerfacecolor='white')

        # Trend line
        if len(ratings) >= 2:
            x = np.arange(len(ratings))
            slope, _ = np.polyfit(x, ratings.values, 1)
            trend = ratings.values[0] + slope * x
            ax.plot(decades, trend,
                    linestyle='--', linewidth=2, color='#FFD700',
                    label=f"Trend: {slope:.3f} pts/decade")
            ax.legend(facecolor='#2E2E2E', edgecolor='white', labelcolor='white')

        ax.set_xlabel('Decade', color='white')
        ax.set_ylabel('Average Rating', color='white')
        ax.set_title(self.title, color='white', pad=15)
        ax.tick_params(axis='x', rotation=45, colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, color='#555555', linestyle='--', alpha=0.5)
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        for spine in ax.spines.values():
            spine.set_color('#FFFFFF')
        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        """Compute concise boxed insights based on rating data."""
        if df.empty:
            return {'Status': 'No data'}

        x = np.arange(len(df))
        y = df['avg_rating'].values
        insights = {
            'Decades Covered': len(df),
            'Total Albums': int(df['count'].sum()),
            'Overall Avg Rating': f"{y.mean():.2f}",
        }

        # Trend magnitude only
        if len(y) >= 2:
            slope, _ = np.polyfit(x, y, 1)
            insights['Rating Trend'] = f"{slope:.3f} pts/decade"

        # Best/Worst
        best = df.loc[df['avg_rating'].idxmax()]
        worst = df.loc[df['avg_rating'].idxmin()]
        insights['Best Decade'] = f"{best['decade']} ({best['avg_rating']:.2f})"
        insights['Worst Decade'] = f"{worst['decade']} ({worst['avg_rating']:.2f})"

        # Peak count
        peak = df.loc[df['count'].idxmax()]
        insights['Decade with Most Albums'] = f"{peak['decade']} ({peak['count']})"

        return insights

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        """Render with separate Visualization and Insights boxes."""
        for w in parent.winfo_children(): w.destroy()
        df = self.fetch_data(**kwargs)
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=vis).get_tk_widget().pack(fill=tk.BOTH, expand=True)
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)
        cols = min(len(stats), 4)
        for i, (k, v) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='center', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)
        return fig
