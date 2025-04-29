import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk
from math import ceil
import textwrap
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class SubgenreRatings(AnalyticsBase):
    """
    Computes and visualizes average album ratings by subgenre (Styles).
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        artist = kwargs.get('artist')
        genre_filter = kwargs.get('genre')
        decade = kwargs.get('decade')
        self.last_filters = {'artist': artist, 'genre': genre_filter, 'decade': decade}

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Styles, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        df = df.dropna(subset=['Styles', 'Rating'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])

        df['StyleList'] = df['Styles'].astype(str).str.split(r',\s*|\s*&\s*|\s*and\s*')
        df = df.explode('StyleList')
        df['Style'] = df['StyleList'].str.strip()
        df = df[df['Style'] != '']

        df['year'] = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0].astype(float, errors='ignore')
        df['decade'] = (df['year']//10*10).astype(int).astype(str) + 's'

        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre_filter and genre_filter != 'All':
            df = df[df['Genres'].astype(str).str.contains(genre_filter, na=False, regex=False)]
        if decade and decade != 'All':
            start = int(decade[:-1])
            df = df[(df['year'] >= start) & (df['year'] < start + 10)]

        if df.empty:
            return pd.DataFrame(columns=['Style', 'avg_rating', 'count'])

        result = (
            df.groupby('Style', observed=True)
              .agg(avg_rating=('Rating', 'mean'), count=('Rating', 'size'))
              .reset_index()
              .sort_values('avg_rating', ascending=False)
        )
        return result

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        labels = df['Style'].tolist()
        wrapped_labels = [textwrap.fill(lbl, 12) for lbl in labels]

        fig = Figure(figsize=(max(12, len(df) * 0.8), 6), constrained_layout=False)
        ax = fig.add_subplot(111)

        bars = ax.bar(
            range(len(wrapped_labels)),
            df['avg_rating'],
            color='#4B72B8', edgecolor='#444444', width=0.8
        )

        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.yaxis.grid(True, color='#555555', linestyle='--', linewidth=0.5)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.tick_params(axis='y', colors='white', labelsize=10)

        ax.set_xticks(range(len(wrapped_labels)))
        ax.set_xticklabels(
            wrapped_labels,
            rotation=60,
            ha='right',
            va='top',
            color='white',
            fontsize=9
        )

        fig.subplots_adjust(bottom=0.4, left=0.05, right=0.95)

        ax.set_xlabel('Subgenre', color='white', fontsize=12)
        ax.set_ylabel('Average Rating', color='white', fontsize=12)
        ax.set_title(self.title, color='white', fontsize=14, pad=10)

        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.02,
                f"{h:.2f}",
                va='bottom', ha='center', color='white', fontsize=9
            )

        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        insights = {}
        if df.empty:
            insights['Status'] = 'No data'
            return insights
        counts = df['count']
        ratings = df['avg_rating']
        insights['Subgenres Analyzed'] = len(df)
        insights['Overall Avg Rating'] = f"{ratings.mean():.2f}"
        insights['Highest Rated Subgenre'] = f"{df.iloc[0]['Style']} ({df.iloc[0]['avg_rating']:.2f})"
        insights['Lowest Rated Subgenre'] = f"{df.iloc[-1]['Style']} ({df.iloc[-1]['avg_rating']:.2f})"
        insights['Avg Albums per Subgenre'] = f"{counts.mean():.1f}"
        insights['Rating Range'] = f"{ratings.max() - ratings.min():.2f}"
        insights['Rating Std Dev'] = f"{ratings.std():.2f}"

        top5_count = df.nlargest(5, 'count')
        insights['Top 5 by Count'] = "; ".join(f"{row.Style} ({row.count})" for row in top5_count.itertuples())
        bottom5_count = df.nsmallest(5, 'count')
        insights['Bottom 5 by Count'] = "; ".join(f"{row.Style} ({row.count})" for row in bottom5_count.itertuples())

        top5_rating = df.nlargest(5, 'avg_rating')
        insights['Top 5 by Rating'] = "; ".join(f"{row.Style} ({row.avg_rating:.2f})" for row in top5_rating.itertuples())
        bottom5_rating = df.nsmallest(5, 'avg_rating')
        insights['Bottom 5 by Rating'] = "; ".join(f"{row.Style} ({row.avg_rating:.2f})" for row in bottom5_rating.itertuples())

        return insights


    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        for w in parent.winfo_children():
            w.destroy()
        df = self.fetch_data(**kwargs)

        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        chart_canvas = tk.Canvas(vis, bg='#2E2E2E', height=300)
        chart_canvas.pack(fill=tk.BOTH, expand=True)
        h_scroll = ttk.Scrollbar(vis, orient=tk.HORIZONTAL, command=chart_canvas.xview)
        h_scroll.pack(fill=tk.X)
        chart_canvas.configure(xscrollcommand=h_scroll.set)
        inner = ttk.Frame(chart_canvas)
        win = chart_canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: chart_canvas.configure(scrollregion=chart_canvas.bbox('all')))
        chart_canvas.bind('<Configure>', lambda e: chart_canvas.itemconfig(win, height=e.height))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=inner).get_tk_widget().pack(fill=tk.BOTH)

        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)

        metrics = [(k, v) for k, v in stats.items() if not k.lower().startswith(('top', 'bottom'))]
        lists = [(k, v) for k, v in stats.items() if k.lower().startswith(('top', 'bottom'))]

        cols = 2
        for idx, (k, v) in enumerate(metrics):
            r, c = divmod(idx, cols)
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        bottom_start_row = ceil(len(metrics) / cols)
        for idx, (k, v) in enumerate(lists):
            r = bottom_start_row + (idx // cols)
            c = idx % cols
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        return fig
