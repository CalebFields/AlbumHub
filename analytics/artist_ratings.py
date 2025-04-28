import sqlite3
import pandas as pd
import re
import textwrap
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from analytics.analytics_base import AnalyticsBase
from export.exporters import export_chart_and_insights

class ArtistRatings(AnalyticsBase):
    """
    Computes average album ratings per artist with advanced concentration and diversity insights.
    """
    def __init__(self, db_path, title=None):
        super().__init__(db_path, title)
        self.last_filters = {}

    def fetch_data(self, **kwargs):
        """Fetch normalized artist ratings, handling multi-artist splits and name variants."""
        self.last_filters = kwargs.copy()
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        # Clean and filter
        df = df.dropna(subset=['Artist', 'Rating'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df[df['Rating'].between(0, 10)]

        # Split and normalize artist names
        df['Artist'] = df['Artist'].str.replace(r"\s*&\s*", " and ", regex=True)
        split_re = re.compile(r',\s*(?!the\s)|\s+and\s+(?!the\s)', flags=re.IGNORECASE)
        df = df.assign(artist_list=df['Artist'].str.split(split_re)).explode('artist_list')
        df['artist_list'] = df['artist_list'].str.strip()
        df['artist_norm'] = df['artist_list'].str.lower().str.replace(r"[\.'\"]", "", regex=True).str.strip()
        df['Artist'] = df['artist_norm'].str.title()

        # Apply filters
        if kwargs.get('genre') and kwargs['genre'] != 'All':
            df = df[df['Genres'].str.contains(kwargs['genre'], na=False)]
        if kwargs.get('decade') and kwargs['decade'] != 'All':
            years = df['Release_Date'].str.extract(r"(\d{4})")[0].astype(float)
            start = int(kwargs['decade'][:-1])
            df = df[years.between(start, start+9)]
        if kwargs.get('artist') and kwargs['artist'] != 'All':
            df = df[df['Artist'] == kwargs['artist']]

        if df.empty:
            return pd.DataFrame(columns=['Artist', 'avg_rating', 'album_count'])

        result = (
            df.groupby('Artist', observed=True)
              .agg(avg_rating=('Rating', 'mean'), album_count=('Rating', 'count'))
              .reset_index()
              .sort_values('avg_rating', ascending=False)
        )
        return result

    def create_figure(self, df):
        num = len(df)
        fig = Figure(figsize=(min(max(12, num * 0.6), 36), 6), constrained_layout=True)
        ax = fig.add_subplot(111)

        if df.empty:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', color='white')
            return fig

        positions = [i * 0.8 for i in range(num)]
        bars = ax.bar(positions, df['avg_rating'], width=0.6, color='#4B72B8', edgecolor='#444444')
        wrapped = ["\n".join(textwrap.wrap(name, width=10)) for name in df['Artist']]
        ax.set_xticks(positions)
        ax.set_xticklabels(wrapped, rotation=45, ha='right', fontsize=self._calculate_font_size(num))
        y_max = df['avg_rating'].max() if num else 5
        ax.set_ylim(0, y_max * 1.15)

        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + y_max * 0.02,
                f"{h:.2f}",
                ha='center', va='bottom', color='white', fontsize=self._calculate_font_size(num, True)
            )

        ax.set_title('Artist Ratings Analysis', color='white', pad=20)
        ax.set_xlabel('Artist', color='white')
        ax.set_ylabel('Average Rating', color='white')
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('#FFFFFF')
        ax.grid(True, color='#555555', linestyle='--', alpha=0.5)
        return fig

    def _calculate_font_size(self, num_items, is_label=False):
        base = 10 if is_label else 8
        scale = max(0.8, 1.2 - num_items * 0.01)
        return max(base * scale, 8)

    def _calculate_statistics(self, df):
        """Compute metrics for insights panel."""
        if df.empty:
            return {'Status': 'No data'}
        total_albums = df['album_count'].sum()
        shares = df['album_count'] / total_albums
        return {
            'Artists Analyzed': str(len(df)),
            'Average Rating': f"{df['avg_rating'].mean():.2f}",
            'Total Albums': str(total_albums),
            'Top Artist Share (%)': f"{shares.iloc[0] * 100:.1f}",
            'Top 5 Share (%)': f"{shares.iloc[:5].sum() * 100:.1f}",
            'Single-Album Artists (%)': f"{(df['album_count'] == 1).sum() / len(df) * 100:.1f}",
            'HHI (Conc. Index)': f"{(shares**2).sum():.4f}",
            'Rating Std Dev': f"{df['avg_rating'].std():.2f}",
            'Median Rating': f"{df['avg_rating'].median():.2f}"
        }

    def _render_chart_section(self, parent, df):
        """Render chart and insights in labeled frames."""
        for w in parent.winfo_children(): w.destroy()

        # Chart
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
        fig = self.create_figure(df)
        FigureCanvasTkAgg(fig, master=inner).get_tk_widget().pack(fill=tk.X)

        # Insights
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True)
        stats = self._calculate_statistics(df)
        cols = min(len(stats), 4)
        for i, (k, v) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            lbl = ttk.Label(info, text=f'{k}: {v}', anchor='center', relief='solid', padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        # Top 10 Artists
        start = (len(stats) + cols - 1) // cols
        ttk.Label(info, text='Top 10 Artists:', font=('TkDefaultFont',10,'bold')).grid(row=start, column=0, columnspan=cols, sticky='w', pady=(10,2), padx=2)
        for idx, row in enumerate(df.head(10).itertuples(), 1):
            r = start + 1 + (idx - 1) // cols
            c = (idx - 1) % cols
            ttk.Label(info, text=f'{idx}. {row.Artist} ({row.avg_rating:.2f})', anchor='w', padding=(15,0)).grid(row=r, column=c, sticky='w', padx=2, pady=2)

    def render(self, parent, **kwargs):
        for w in parent.winfo_children(): w.destroy()
        df = self.fetch_data(**kwargs)
        self._render_chart_section(parent, df)
        return getattr(self, 'fig', None)

    def export_visualization(self, filepath):
        df = self.fetch_data(**self.last_filters)
        stats = self._calculate_statistics(df)
        stats['Top 10 Artists'] = '\n'.join(f"{i+1}. {row.Artist} ({row.avg_rating:.2f})" for i,row in df.head(10).iterrows())
        export_chart_and_insights(getattr(self, 'fig', None), stats, filepath)
