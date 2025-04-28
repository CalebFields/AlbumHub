import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk
from math import ceil
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class LabelAnalytics(AnalyticsBase):
    """
    Analyzes record labels and self-released artists: average rating per label or artist,
    respecting optional filters (artist, genre, decade).
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        # Retrieve filter parameters
        artist = kwargs.get('artist')
        genre_filter = kwargs.get('genre')
        decade = kwargs.get('decade')
        self.last_filters = {'artist': artist, 'genre': genre_filter, 'decade': decade}

        # Load necessary fields for filtering
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Label, Genres, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        # Apply artist filter
        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        # Apply genre filter
        if genre_filter and genre_filter != 'All':
            df = df[df['Genres'].astype(str).str.contains(genre_filter, na=False, regex=False)]
        # Apply decade filter
        if decade and decade != 'All':
            years = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0].astype(float, errors='ignore')
            start = int(decade[:-1])
            df = df[(years >= start) & (years < start + 10)]

        # Clean and standardize labels
        df['Label'] = df['Label'].fillna('').astype(str).str.strip()
        # Treat 'Not On Label' (case-insensitive) and blanks as self-releases
        mask = df['Label'].eq('') | df['Label'].str.lower().eq('not on label')
        df.loc[mask, 'Label'] = df.loc[mask, 'Artist']

        # Convert ratings and drop invalids
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating', 'Label'])

        return df

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        # Aggregate by label/artist
        grouped = df.groupby('Label').agg(
            avg_rating=('Rating', 'mean'),
            count=('Rating', 'size')
        )
        avg_ratings = grouped['avg_rating'].sort_values(ascending=False)

        # Plot
        fig = Figure(figsize=(max(8, len(avg_ratings) * 0.4), 6), constrained_layout=True)
        ax = fig.add_subplot(111)
        bars = ax.bar(
            avg_ratings.index,
            avg_ratings.values,
            color='#81a1c1', edgecolor='#444444', width=0.8
        )

        # Theme styling
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.yaxis.grid(True, color='#555555', linestyle='--', linewidth=0.5)
        ax.tick_params(axis='y', colors='white')

        # X-axis labels
        ax.set_xticklabels(
            avg_ratings.index, rotation=60, ha='right', color='white', fontsize=9
        )
        ax.tick_params(axis='x', colors='white')

        ax.set_xlabel('Label / Self-Released Artist', color='white')
        ax.set_ylabel('Average Rating', color='white')
        ax.set_title('Average Rating by Label or Artist', color='white', pad=10)

        # Annotate bars
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.02,
                f"{h:.2f}",
                ha='center', va='bottom', color='white', fontsize=9
            )

        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        grouped = df.groupby('Label').agg(
            avg_rating=('Rating', 'mean'),
            count=('Rating', 'size')
        )
        total_entities = grouped.shape[0]
        total_albums = int(grouped['count'].sum())
        ratings = grouped['avg_rating']

        overall_avg = ratings.mean()
        median = ratings.median()
        std_dev = ratings.std()
        rating_range = ratings.max() - ratings.min()
        best_label, best_rating = ratings.idxmax(), ratings.max()
        worst_label, worst_rating = ratings.idxmin(), ratings.min()

        insights = {
            'Labels / Self-Released Artists Analyzed': total_entities,
            'Total Albums': total_albums,
            'Overall Avg Rating': f"{overall_avg:.2f}",
            'Median Avg Rating': f"{median:.2f}",
            'Rating Std Dev': f"{std_dev:.2f}",
            'Rating Range': f"{rating_range:.2f}",
            'Highest Rated': f"{best_label} ({best_rating:.2f})",
            'Lowest Rated': f"{worst_label} ({worst_rating:.2f})"
        }

        # Top lists
        top5_count = grouped['count'].nlargest(5)
        insights['Top 5 by Count'] = "; ".join(f"{lbl} ({cnt})" for lbl, cnt in top5_count.items())
        top5_rating = ratings.nlargest(5)
        insights['Top 5 by Avg Rating'] = "; ".join(f"{lbl} ({rt:.2f})" for lbl, rt in top5_rating.items())

        return insights

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        # Clear frame
        for w in parent.winfo_children():
            w.destroy()
        # Fetch filtered data
        df = self.fetch_data(**kwargs)

        # Visualization
        vis = ttk.Labelframe(parent, text='Label / Self-Released Artist Quality')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=vis).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Insights
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)

        metrics = [(k, v) for k, v in stats.items() if not k.startswith('Top')]
        lists = [(k, v) for k, v in stats.items() if k.startswith('Top')]

        cols = 2
        for idx, (k, v) in enumerate(metrics):
            r, c = divmod(idx, cols)
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        bottom_row = ceil(len(metrics) / cols)
        for idx, (k, v) in enumerate(lists):
            r = bottom_row + (idx // cols)
            c = idx % cols
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        return fig
