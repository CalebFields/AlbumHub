import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase
import re

class RatingDistribution(AnalyticsBase):
    """
    Shows a histogram of album ratings (1–10) for the selected filter.
    Adds personalized summary below the chart.
    """
    def fetch_data(self, artist=None, genre=None, decade=None) -> pd.Series:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Rating, Artist, Genres, Release_Date FROM albums", conn
        )
        conn.close()
        df = df.dropna(subset=['Rating'])
        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist)]
        if genre:
            df = df[df['Genres'].fillna('').str.contains(genre)]
        if decade:
            years = pd.to_numeric(
                df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0],
                errors='coerce'
            )
            df = df[years.between(int(decade[:-1]), int(decade[:-1]) + 9)]
        if df.empty:
            raise ValueError('No data to plot distribution')
        return df['Rating']

    def create_figure(self, data: pd.Series) -> Figure:
        bins = np.linspace(0.5, 10.5, 11)
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(1, 1, 1)
        counts, edges, patches = ax.hist(
            data,
            bins=bins,
            edgecolor='black',
            align='mid'
        )
        mids = (edges[:-1] + edges[1:]) / 2
        ax.set_xticks(mids)
        ax.set_xticklabels([str(int(mid)) for mid in mids])
        ax.set_xlim(edges[0], edges[-1])
        ax.set_ylim(bottom=counts.min() - 0.5)
        ax.set_xlabel('Rating')
        ax.set_ylabel('Count')
        ax.set_title(self.title)
        fig.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.2)
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
        data = self.fetch_data(**kwargs)
        total = data.count()
        avg = data.mean()
        common = data.mode()[0] if not data.mode().empty else None
        counts = data.value_counts()
        least = counts.idxmin() if not counts.empty else None
        for w in stats_box.winfo_children():
            w.destroy()
        ttk.Label(stats_box, text=f"Total ratings: {total}").pack(anchor='w', padx=5, pady=2)
        ttk.Label(stats_box, text=f"Average rating: {avg:.2f}").pack(anchor='w', padx=5, pady=2)
        if common is not None:
            ttk.Label(stats_box, text=f"Most common rating: {common}").pack(anchor='w', padx=5, pady=2)
        if least is not None:
            ttk.Label(stats_box, text=f"Least common rating: {least}").pack(anchor='w', padx=5, pady=2)
