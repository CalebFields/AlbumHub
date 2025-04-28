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

class AlbumsCount(AnalyticsBase):
    """
    Analyzes album distribution across artists with accurate filtering,
    normalization, and enhanced statistics (including in-depth insights).
    """
    def __init__(self, db_path: str, title: str = None):
        super().__init__(db_path, title)
        self.last_filters = {}

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetch and normalize album counts per artist, preserving filters."""
        self.last_filters = kwargs.copy()
        conn = sqlite3.connect(self.db_path)
        query = "SELECT Artist, Genres, Release_Date FROM albums WHERE 1=1"
        params = []
        if kwargs.get('genre') and kwargs['genre'] != 'All':
            query += " AND Genres LIKE ?"
            params.append(f"%{kwargs['genre']}%")
        if kwargs.get('decade') and kwargs['decade'] != 'All':
            start = int(kwargs['decade'][:-1])
            end = start + 9
            query += " AND CAST(SUBSTR(Release_Date,1,4) AS INTEGER) BETWEEN ? AND ?"
            params.extend([start, end])
        raw = pd.read_sql_query(query, conn, params=params)
        conn.close()
        self.raw_df = raw.copy()

        if raw.empty:
            return pd.DataFrame(columns=['Artist', 'count'])

        raw['Artist'] = raw['Artist'].str.replace(r"\s*&\s*", " and ", regex=True)
        split_pattern = re.compile(r',\s*(?!the\s)|\s+and\s+(?!the\s)', flags=re.IGNORECASE)
        exploded = raw.assign(artist_list=raw['Artist'].str.split(split_pattern)).explode('artist_list')
        exploded['artist_list'] = exploded['artist_list'].str.strip()
        exploded['artist_norm'] = (
            exploded['artist_list']
            .str.lower()
            .str.replace(r"[\.'\"]", "", regex=True)
            .str.strip()
        )
        exploded['Artist'] = exploded['artist_norm'].str.title()

        if kwargs.get('artist') and kwargs['artist'] != 'All':
            exploded = exploded[exploded['Artist'] == kwargs['artist']]

        result = (
            exploded.groupby('Artist', observed=True)
                    .size()
                    .reset_index(name='count')
                    .sort_values('count', ascending=False)
        )
        return result

    def create_figure(self, df: pd.DataFrame) -> Figure:
        fig = Figure(figsize=(max(10, len(df) * 0.5), 6), constrained_layout=True)
        ax = fig.add_subplot(111)

        if df.empty:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', color='white')
            ax.set_xticks([])
            ax.set_yticks([])
            return fig

        wrapped = ["\n".join(textwrap.wrap(name, width=10)) for name in df['Artist']]
        bars = ax.bar(wrapped, df['count'], color='#4B8BBE')

        max_count = df['count'].max()
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + max_count * 0.02,
                f"{int(h)}",
                ha='center', va='bottom', color='white', fontsize=9
            )

        ax.set_title('Album Distribution by Artist', color='white', pad=15)
        ax.set_xlabel('Artist', color='white')
        ax.set_ylabel('Number of Albums', color='white')
        ax.tick_params(axis='x', rotation=45, colors='white')
        for lbl in ax.get_xticklabels():
            lbl.set_horizontalalignment('right')
        ax.tick_params(axis='y', colors='white')

        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        return fig

    def _calculate_statistics(self, df: pd.DataFrame) -> dict:
        """Compute in-depth metrics for insights panel."""
        total_albums = len(self.raw_df)
        artists = df['Artist'].unique()
        counts = df['count']
        if df.empty:
            return {'Status': 'No data'}

        # core metrics
        top_share = counts.iloc[0] / total_albums * 100
        top5_share = counts.iloc[:5].sum() / total_albums * 100
        single_pct = (counts == 1).sum() / len(counts) * 100
        hhi = (counts / total_albums) ** 2
        hhi = hhi.sum()

        # added metrics
        avg_count = counts.mean()
        median_count = counts.median()
        std_count = counts.std()
        pct_10 = counts.quantile(0.1)
        pct_90 = counts.quantile(0.9)
        gini = (counts.sort_values().values)
        n = len(gini)
        gini = (2 * (gini.cumsum() / gini.sum()).sum() - (n + 1)) / n

        return {
            'Artists Analyzed': len(counts),
            'Total Albums': total_albums,
            'Average Albums/Artist': f"{avg_count:.1f}",
            'Median Albums/Artist': f"{median_count:.1f}",
            'Album Count Std Dev': f"{std_count:.1f}",
            '10th Percentile Count': f"{pct_10:.1f}",
            '90th Percentile Count': f"{pct_90:.1f}",
            'Gini Coefficient': f"{gini:.3f}",
            'Top Artist Share (%)': f"{top_share:.1f}",
            'Top 5 Cumulative Share (%)': f"{top5_share:.1f}",
            'Single-Album Artists (%)': f"{single_pct:.1f}",
            'HHI (Concentration Index)': f"{hhi:.4f}"        
        }

    def _render_chart_section(self, parent: ttk.Frame, df: pd.DataFrame):
        for w in parent.winfo_children():
            w.destroy()
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        canvas = tk.Canvas(vis, bg='#2E2E2E')
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        h_scroll = ttk.Scrollbar(vis, orient=tk.HORIZONTAL, command=canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.configure(xscrollcommand=h_scroll.set)
        inner = ttk.Frame(canvas)
        win = canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, height=e.height))
        self.fig = self.create_figure(df)
        FigureCanvasTkAgg(self.fig, master=inner).get_tk_widget().pack(fill=tk.X)

        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True)
        stats = self._calculate_statistics(df)
        cols = min(len(stats), 4)
        for i, (k, v) in enumerate(stats.items()):
            r, c = divmod(i, cols)
            ttk.Label(info, text=f'{k}: {v}', anchor='center', relief='solid', padding=5).grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)

        start_row = (len(stats) + cols - 1)//cols
        ttk.Label(info, text='Top 10 Artists:', font=('TkDefaultFont', 10, 'bold')).grid(row=start_row, column=0, columnspan=cols, sticky='w', pady=(10,2), padx=2)
        for idx, row in enumerate(df.head(10).itertuples(),1):
            r = start_row + 1 + (idx-1)//cols
            c = (idx-1)%cols
            ttk.Label(info, text=f'{idx}. {row.Artist} ({row.count})', padding=(15,0)).grid(row=r, column=c, sticky='w', padx=2, pady=2)

    def render(self, parent: ttk.Frame, **kwargs):
        for w in parent.winfo_children(): w.destroy()
        try:
            df = self.fetch_data(**kwargs)
            container = ttk.Frame(parent)
            container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self._render_chart_section(container, df)
            return self.fig
        except Exception as e:
            err = ttk.Label(parent, text=f"Error: {e}", foreground='red')
            err.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            return None

    def export_visualization(self, filepath: str):
        df = self.fetch_data(**self.last_filters)
        stats = self._calculate_statistics(df)
        stats['Top 10 Artists'] = '\n'.join(
            f"{i}. {row.Artist} ({row.count})" for i,row in enumerate(df.head(10).itertuples(),1)
        )
        export_chart_and_insights(self.fig, stats, filepath)
