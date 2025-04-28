import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class DurationRating(AnalyticsBase):
    """
    Examines correlation between album duration and rating, summing track durations from tracklist.
    Produces a scatter plot with regression and concise insights, including top 5 longest/shortest albums
    and detailed duration distribution metrics.
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Load album durations (from tracklist) and ratings, apply optional filters."""
        artist = kwargs.get('artist')
        genre = kwargs.get('genre')
        decade = kwargs.get('decade')
        self.last_filters = {'artist': artist, 'genre': genre, 'decade': decade}

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            """
            SELECT a.id AS album_id,
                   a.Title,
                   a.Artist,
                   a.Genres,
                   a.Release_Date,
                   a.Rating,
                   SUM(t.duration_sec) AS total_sec
            FROM tracklist t
            JOIN albums a ON t.album_id = a.id
            GROUP BY t.album_id
            """, conn
        )
        conn.close()

        df = df.dropna(subset=['total_sec', 'Rating', 'Release_Date', 'Artist', 'Title'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df['Duration'] = df['total_sec'] / 60.0  # minutes
        df = df[df['Duration'] > 0]
        df = df.dropna(subset=['Rating', 'Duration'])

        df['year'] = (
            df['Release_Date'].astype(str)
              .str.extract(r"(\d{4})")[0]
              .astype(float, errors='ignore')
        )
        df = df.dropna(subset=['year'])
        df['decade'] = (df['year']//10*10).astype(int).astype(str) + 's'

        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre and genre != 'All':
            df = df[df['Genres'].fillna('').str.contains(genre, na=False, regex=False)]
        if decade and decade != 'All':
            df = df[df['decade'] == decade]

        if df.empty:
            return pd.DataFrame(columns=['Title','Duration','Rating','decade'])
        return df[['Title','Duration','Rating','decade']]

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """Create scatter plot of duration vs rating with regression trend line."""
        fig = Figure(figsize=(8, 6), constrained_layout=True)
        ax = fig.add_subplot(111)
        ax.scatter(df['Duration'], df['Rating'], alpha=0.7)

        x = df['Duration'].values
        y = df['Rating'].values
        if len(x) >= 2:
            slope, intercept = np.polyfit(x, y, 1)
            ax.plot(x, slope * x + intercept,
                    linestyle='--', color='#FFD700',
                    label=f'Trend: {slope:.2f} pts/min')
            ax.legend(facecolor='#2E2E2E', edgecolor='white', labelcolor='white')

        ax.set_xlabel('Duration (min)', color='white')
        ax.set_ylabel('Rating', color='white')
        ax.set_title(self.title, color='white', pad=15)
        ax.grid(True, color='#555555', linestyle='--', alpha=0.5)
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.tick_params(colors='white')
        for spine in ax.spines.values(): spine.set_color('white')
        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        """Compute concise boxed insights and duration distribution metrics."""
        if df.empty:
            return {'Status': 'No data'}

        insights = {}
        # Basic counts and averages
        insights['Albums'] = len(df)
        insights['Avg Duration'] = f"{df['Duration'].mean():.1f} min"
        insights['Avg Rating'] = f"{df['Rating'].mean():.2f}"

        # Correlation coefficient
        corr = np.corrcoef(df['Duration'], df['Rating'])[0,1]
        insights['Correlation'] = f"{corr:.3f}"

        # Duration distribution metrics
        dur = df['Duration']
        insights['Duration Median'] = f"{dur.median():.1f} min"
        insights['Duration Std Dev'] = f"{dur.std():.1f} min"
        q1 = dur.quantile(0.25)
        q3 = dur.quantile(0.75)
        insights['Avg Rating Shortest 25%'] = f"{df[df['Duration'] <= q1]['Rating'].mean():.2f}"
        insights['Avg Rating Longest 25%'] = f"{df[df['Duration'] >= q3]['Rating'].mean():.2f}"
        return insights

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        """Render boxed Visualization, Insights, and Top 5 sections."""
        for w in parent.winfo_children():
            w.destroy()
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

        top5_frame = ttk.Frame(parent)
        top5_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5,0))
        longest_box = ttk.Labelframe(top5_frame, text='Top 5 Longest Albums')
        longest_box.grid(row=0, column=0, sticky='nsew', padx=2)
        shortest_box = ttk.Labelframe(top5_frame, text='Top 5 Shortest Albums')
        shortest_box.grid(row=0, column=1, sticky='nsew', padx=2)
        top5_frame.grid_columnconfigure(0, weight=1)
        top5_frame.grid_columnconfigure(1, weight=1)

        top_long = df.nlargest(5, 'Duration')
        for idx, row in enumerate(top_long.itertuples(), 1):
            ttk.Label(longest_box, text=f"{idx}. {row.Title} ({row.Duration:.1f} min)", anchor='w', padding=5).pack(fill='x')
        top_short = df.nsmallest(5, 'Duration')
        for idx, row in enumerate(top_short.itertuples(), 1):
            ttk.Label(shortest_box, text=f"{idx}. {row.Title} ({row.Duration:.1f} min)", anchor='w', padding=5).pack(fill='x')

        return fig