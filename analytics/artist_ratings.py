import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase

class ArtistRatings(AnalyticsBase):
    """
    Analytics for computing average album ratings with optional filters:
    artist, genre, and decade. Albums with multiple artists are split and
    counted for each contributing artist.
    """
    def fetch_data(self,
                   artist: str = None,
                   genre: str = None,
                   decade: str = None) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        df = df.dropna(subset=['Artist', 'Rating'])

        df['Artist'] = df['Artist'].astype(str)
        df = df.assign(
            artist=df['Artist'].str.split(r'[,&]')
        ).explode('artist')
        df['artist'] = df['artist'].str.strip()

        if artist and artist != 'All':
            df = df[df['artist'] == artist]
        if genre:
            df = df[df['Genres'].fillna('').str.contains(genre)]
        if decade:
            years = df['Release_Date'].str.extract(r"(\d{4})")[0].astype(float)
            try:
                start = int(decade[:-1]); end = start + 9
                df = df[years.between(start, end)]
            except ValueError:
                pass

        if df.empty:
            raise ValueError("No data available for selected filter.")

        result = (
            df.groupby('artist')['Rating']
              .mean()
              .reset_index()
              .rename(columns={'Rating': 'avg_rating'})
        )
        result = result.sort_values('avg_rating', ascending=False)
        return result

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        ax.bar(df['artist'], df['avg_rating'])
        ax.set_ylim(bottom=df['avg_rating'].min() - .5)
        ax.set_xlabel("Artist")
        ax.set_ylabel("Average Rating")
        ax.set_title(self.title)
        ax.set_xticklabels(df['artist'], rotation=45, ha='right')
        fig.tight_layout()
        return fig

    def render(self, parent: ttk.Frame, **kwargs):
        super().render(parent, **kwargs)
        stats_box = next(
            (c for c in parent.winfo_children()
             if isinstance(c, ttk.LabelFrame) and c.cget('text') == 'Additional Analysis'),
            None
        )
        if not stats_box:
            return
        df = self.fetch_data(**kwargs)
        total_artists = df.shape[0]
        overall_avg = df['avg_rating'].mean() if total_artists > 0 else 0
        # clear previous stats
        for w in stats_box.winfo_children():
            w.destroy()
        # display summary
        ttk.Label(
            stats_box,
            text=f"You have ratings for {total_artists} unique artists."
        ).pack(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Overall average rating: {overall_avg:.2f}."
        ).pack(anchor='w', padx=5, pady=2)
        # top 10 artists
        top10 = df.head(10)
        ttk.Label(
            stats_box,
            text="Top 10 artists by average rating:"
        ).pack(anchor='w', padx=5, pady=(5,2))
        for _, row in top10.iterrows():
            ttk.Label(
                stats_box,
                text=f"{row['artist']}: {row['avg_rating']:.2f}"
            ).pack(anchor='w', padx=15)
