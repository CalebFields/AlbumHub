import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase
import re

class AlbumsCount(AnalyticsBase):
    """
    Displays number of albums per artist.
    Adds personalized summary below the chart with top 10 artists.
    """
    def fetch_data(self, artist=None, genre=None, decade=None) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Release_Date FROM albums", conn
        )
        conn.close()
        df = df.dropna(subset=['Artist'])
        df = df.assign(artist=df['Artist'].str.split(r'[,&]')).explode('artist')
        df['artist'] = df['artist'].str.strip()
        if artist and artist != 'All':
            df = df[df['artist'] == artist]
        if genre:
            df = df[df['Genres'].fillna('').str.contains(genre)]
        if decade:
            years = df['Release_Date'].str.extract(r"(\d{4})")[0].astype(float)
            start = int(decade[:-1]); end = start + 9
            df = df[years.between(start, end)]
        if df.empty:
            raise ValueError('No data for album count')
        result = df.groupby('artist').size().reset_index(name='count')
        result = result.sort_values('count', ascending=False)
        return result

    def create_figure(self, df: pd.DataFrame) -> Figure:
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(1, 1, 1)
        ax.bar(df['artist'], df['count'])
        ax.set_xlabel('Artist')
        ax.set_ylabel('Album Count')
        ax.set_title(self.title)
        ax.set_xticklabels(df['artist'], rotation=45, ha='right')
        fig.tight_layout()
        return fig

    def render(self, parent: ttk.Frame, **kwargs):
        super().render(parent, **kwargs)
        # locate additional analysis frame
        stats_box = next(
            (c for c in parent.winfo_children()
             if isinstance(c, ttk.LabelFrame) and c.cget('text') == 'Additional Analysis'),
            None
        )
        if not stats_box:
            return
        # compute total albums (raw count)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        sql = "SELECT COUNT(*) FROM albums"
        conditions = []
        params = []
        if 'artist' in kwargs and kwargs['artist'] and kwargs['artist'] != 'All':
            conditions.append("Artist LIKE ?")
            params.append(f"%{kwargs['artist']}%")
        if 'genre' in kwargs and kwargs['genre']:
            conditions.append("Genres LIKE ?")
            params.append(f"%{kwargs['genre']}%")
        if 'decade' in kwargs and kwargs['decade'] and kwargs['decade'] != 'All':
            start = int(kwargs['decade'][:-1])
            end = start + 9
            conditions.append("CAST(substr(Release_Date,1,4) AS INT) BETWEEN ? AND ?")
            params.extend([start, end])
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        cur.execute(sql, params)
        total_albums = cur.fetchone()[0]
        conn.close()
        # fetch exploded counts for artist stats
        df = self.fetch_data(**kwargs)
        unique_artists = df.shape[0]
        top10 = df.head(10)
        # clear stats frame
        for w in stats_box.winfo_children():
            w.destroy()
        ttk.Label(stats_box, text=f"Total albums: {total_albums}").pack(anchor='w', padx=5, pady=2)
        ttk.Label(stats_box, text=f"Unique artists: {unique_artists}").pack(anchor='w', padx=5, pady=2)
        ttk.Label(stats_box, text="Top 10 artists:").pack(anchor='w', padx=5, pady=(5,2))
        for _, row in top10.iterrows():
            ttk.Label(stats_box, text=f"{row['artist']}: {row['count']}").pack(anchor='w', padx=15)