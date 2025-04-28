import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class RatingDistribution(AnalyticsBase):
    """
    Computes and visualizes the distribution of album ratings with GUI theme compliance.
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """
        Fetch ratings, optionally filtering by artist, genre, or decade.
        Returns a DataFrame with a 'Rating' column.
        """
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        df = df.dropna(subset=['Rating'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])

        artist = kwargs.get('artist')
        genre = kwargs.get('genre')
        decade = kwargs.get('decade')

        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre and genre != 'All':
            df = df[df['Genres'].astype(str).str.contains(genre, na=False, regex=False)]
        if decade and decade != 'All':
            years = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0].astype(float, errors='ignore')
            start = int(decade[:-1])
            df = df[(years >= start) & (years < start+10)]

        return df[['Rating']]

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """
        Create a themed histogram showing rating frequency distribution.
        """
        fig = Figure(figsize=(8, 4), constrained_layout=True)
        ax = fig.add_subplot(111)

        # Themed histogram
        ax.hist(
            df['Rating'], bins=10,
            color='#4B72B8', edgecolor='#444444'
        )

        # Styling for dark GUI
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.grid(axis='y', color='#555555', linestyle='--', linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.tick_params(colors='white')

        # Labels and title in theme colors
        ax.set_xlabel('Rating', color='white', fontsize=12)
        ax.set_ylabel('Count', color='white', fontsize=12)
        ax.set_title(self.title, color='white', fontsize=14, pad=10)

        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        """
        Generate distribution metrics: count, mean, median, mode, std, range, skewness, and kurtosis.
        """
        ratings = df['Rating']
        total = len(ratings)
        mean = ratings.mean()
        median = ratings.median()
        mode = ratings.mode().iloc[0] if not ratings.mode().empty else None
        std = ratings.std()
        rmin, rmax = ratings.min(), ratings.max()
        skew = ratings.skew()
        kurt = ratings.kurt()

        insights = {
            'Total Ratings': f"{total}",
            'Mean Rating': f"{mean:.2f}",
            'Median Rating': f"{median:.2f}",
            'Mode Rating': f"{mode:.2f}" if mode is not None else 'N/A',
            'Std Deviation': f"{std:.2f}",
            'Rating Range': f"{(rmax-rmin):.2f}",
            'Skewness': f"{skew:.2f}",
            'Kurtosis': f"{kurt:.2f}"
        }
        return insights

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        """
        Render the themed distribution chart and extended insights within the Tkinter frame.
        """
        for w in parent.winfo_children():
            w.destroy()

        df = self.fetch_data(**kwargs)

        # Visualization container
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=vis).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Insights container
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)
        cols = min(len(stats), 4)
        for i, (k, v) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            lbl = ttk.Label(
                info,
                text=f"{k}: {v}",
                anchor='center',
                relief='solid',
                borderwidth=1,
                padding=5
            )
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        return fig