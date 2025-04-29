import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class GenreRatings(AnalyticsBase):
    """
    Computes and visualizes average album ratings by genre with detailed insights.
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        artist = kwargs.get('artist')
        decade = kwargs.get('decade')
        self.last_filters = {'artist': artist, 'decade': decade}

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        df = df.dropna(subset=['Genres', 'Rating'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])
        df['GenreList'] = df['Genres'].astype(str).str.split(r',\s*|\s*&\s*', expand=False)
        df = df.explode('GenreList')
        df['Genre'] = df['GenreList'].str.strip()
        df = df[df['Genre'] != '']

        df['year'] = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0].astype(float, errors='ignore')
        df['decade'] = (df['year']//10*10).astype(int).astype(str) + 's'

        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if decade and decade != 'All':
            df = df[df['decade'] == decade]

        if df.empty:
            return pd.DataFrame(columns=['Genre', 'avg_rating', 'count'])

        result = (
            df.groupby('Genre', observed=True)
              .agg(avg_rating=('Rating', 'mean'), count=('Rating', 'size'))
              .reset_index()
              .sort_values('avg_rating', ascending=False)
        )
        return result

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(max(6, len(df)*0.4), 6), constrained_layout=True)
        ax = fig.add_subplot(111)
        bars = ax.bar(df['Genre'], df['avg_rating'], edgecolor='#444444')
        ax.yaxis.grid(True, color='#555555', linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.set_ylabel('Average Rating', color='white', fontsize=12)
        ax.set_xlabel('Genre', color='white', fontsize=12)
        ax.set_title(self.title, color='white', pad=15, fontsize=14)
        ax.tick_params(colors='white', rotation=45, labelsize=10)
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2,
                h + 0.02,
                f"{h:.2f}",
                ha='center', va='bottom', color='white', fontsize=9
            )
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {'Status': 'No data'}
        insights = {}
        insights['Genres Analyzed'] = len(df)
        insights['Overall Avg Rating'] = f"{df['avg_rating'].mean():.2f}"
        insights['Highest Rated Genre'] = f"{df.iloc[0]['Genre']} ({df.iloc[0]['avg_rating']:.2f})"
        insights['Lowest Rated Genre'] = f"{df.iloc[-1]['Genre']} ({df.iloc[-1]['avg_rating']:.2f})"
        counts = df['count']
        insights['Genre Count Std Dev'] = f"{counts.std():.1f}"
        insights['Average Albums per Genre'] = f"{counts.mean():.1f}"
        insights['Rating Range'] = f"{df['avg_rating'].max() - df['avg_rating'].min():.2f}"
        top5 = df.nlargest(5, 'count')
        insights['Top 5 Genres by Count'] = "; ".join(f"{row.Genre} ({row.count})" for row in top5.itertuples())
        bottom5 = df.nsmallest(5, 'count')
        insights['Bottom 5 Genres by Count'] = "; ".join(f"{row.Genre} ({row.count})" for row in bottom5.itertuples())
        top5_rating = df.nlargest(5, 'avg_rating')
        insights['Top 5 Genres by Avg Rating'] = "; ".join(f"{row.Genre} ({row.avg_rating:.2f})" for row in top5_rating.itertuples())
        bottom5_rating = df.nsmallest(5, 'avg_rating')
        insights['Bottom 5 Genres by Avg Rating'] = "; ".join(f"{row.Genre} ({row.avg_rating:.2f})" for row in bottom5_rating.itertuples())
        return insights

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        for w in parent.winfo_children(): w.destroy()
        df = self.fetch_data(**kwargs)
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=vis).get_tk_widget().pack(fill=tk.BOTH, expand=True)
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)
        cols = 4
        for i, (k, v) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='center', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)
        return fig
