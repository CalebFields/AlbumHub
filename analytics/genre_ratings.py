import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase
import re

class GenreAverageRatings(AnalyticsBase):
    """
    Compute average album ratings grouped by genre, with proper Release_Date handling.
    """
    def fetch_data(self, artist=None, genre=None, decade=None) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Genres, Rating, Release_Date FROM albums", conn
        )
        conn.close()
        df = df.dropna(subset=['Genres', 'Rating', 'Release_Date'])
        df = df.assign(genre=df['Genres'].str.split(',')).explode('genre')
        df['genre'] = df['genre'].str.strip()
        if decade and decade != 'All':
            years = pd.to_numeric(
                df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0],
                errors='coerce'
            )
            df = df[years.between(int(decade[:-1]), int(decade[:-1]) + 9)]
        if genre and genre != 'All':
            df = df[df['genre'] == genre]
        if df.empty:
            raise ValueError("No data for selected genre filter.")
        result = (
            df.groupby('genre')['Rating']
              .mean()
              .reset_index(name='avg_rating')
              .sort_values('avg_rating', ascending=False)
        )
        return result

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)
        ax.bar(df['genre'], df['avg_rating'])
        ax.set_ylim(bottom=df['avg_rating'].min() - .5)
        ax.set_xlabel('Genre')
        ax.set_ylabel('Average Rating')
        ax.set_title(self.title)
        ax.set_xticklabels(df['genre'], rotation=45, ha='right')
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
        total_genres = df.shape[0]
        overall_avg = df['avg_rating'].mean() if total_genres > 0 else 0
        top = df.iloc[0]
        bottom = df.iloc[-1]
        for w in stats_box.winfo_children():
            w.destroy()
        ttk.Label(
            stats_box,
            text=f"You have data for {total_genres} genres."
        ).pack(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Overall average rating: {overall_avg:.2f}."
        ).pack(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Highest-rated genre: {top['genre']} ({top['avg_rating']:.2f})."
        ).pack(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Lowest-rated genre: {bottom['genre']} ({bottom['avg_rating']:.2f})."
        ).pack(anchor='w', padx=5, pady=2)