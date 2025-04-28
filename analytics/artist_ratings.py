import sqlite3
import pandas as pd
import tkinter as tk
from matplotlib.figure import Figure
from tkinter import ttk
from analytics.analytics_base import AnalyticsBase
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from export.exporters import export_chart_and_insights

class ArtistRatings(AnalyticsBase):
    def __init__(self, db_path, title=None):
        super().__init__(db_path, title)
        self.last_filters = {}

    def fetch_data(self, **kwargs):
        """Fetch artist ratings with optional artist, genre, decade filters."""
        # store filters for export
        self.last_filters = kwargs.copy()
        try:
            conn = sqlite3.connect(self.db_path)
            query = '''
                SELECT Artist,
                       AVG(CAST(TRIM(Rating) AS REAL)) AS avg_rating,
                       COUNT(*) AS album_count
                FROM albums
                WHERE TRIM(Rating) <> ''
                  AND TRIM(Rating) GLOB '*[0-9]*'
                  AND CAST(TRIM(Rating) AS REAL) BETWEEN 0 AND 10
            '''
            params = []
            if kwargs.get('artist') and kwargs['artist'] != 'All':
                query += " AND Artist = ?"
                params.append(kwargs['artist'])
            if kwargs.get('genre') and kwargs['genre'] != 'All':
                query += " AND Genres LIKE ?"
                params.append(f"%{kwargs['genre']}%")
            if kwargs.get('decade') and kwargs['decade'] != 'All':
                start = int(kwargs['decade'][:-1])
                end = start + 9
                query += " AND CAST(SUBSTR(Release_Date,1,4) AS INTEGER) BETWEEN ? AND ?"
                params.extend([start, end])
            query += '''
                GROUP BY Artist
                HAVING album_count >= 1
                ORDER BY avg_rating DESC
            '''
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            raise RuntimeError(f"Data fetch failed: {e}")

    def create_figure(self, df, **kwargs):
        """Create and style the bar chart."""
        num = len(df)
        fig = Figure(figsize=(min(max(12, num*0.6),36), 6), constrained_layout=True)
        ax = fig.add_subplot(111)
        if df.empty:
            ax.text(0.5,0.5,'No data available',ha='center',va='center',color='white')
            return fig
        positions = [i*(0.6+0.2) for i in range(num)]
        bars = ax.bar(positions, df['avg_rating'], width=0.6, color='#4B72B8', edgecolor='#444444')
        ax.set_xticks(positions)
        ax.set_xticklabels(df['Artist'], rotation=45, ha='right', fontsize=self._calculate_font_size(num))
        y_max = df['avg_rating'].max() if num>0 else 5
        ax.set_ylim(0, y_max*1.15)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x()+bar.get_width()/2, h + y_max*0.02,
                    f'{h:.2f}', ha='center', va='bottom', color='white',
                    fontsize=self._calculate_font_size(num, is_label=True))
        ax.set_title('Artist Ratings Analysis', color='white', pad=20)
        ax.set_ylabel('Average Rating', color='white')
        ax.set_xlabel('Artist', color='white')
        # theme
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.title.set_color('#FFFFFF')
        ax.xaxis.label.set_color('#FFFFFF')
        ax.yaxis.label.set_color('#FFFFFF')
        ax.tick_params(colors='#FFFFFF', which='both')
        for spine in ax.spines.values(): spine.set_color('#FFFFFF')
        ax.grid(True, color='#555555', linestyle='--', alpha=0.5)
        return fig

    def _render_chart_section(self, parent, df):
        """Render chart and insights in separate labeled frames, include top 5 artists."""
        for w in parent.winfo_children(): w.destroy()

        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0,5))
        canvas = tk.Canvas(vis, bg='#2E2E2E', height=300)
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
        info.pack(fill=tk.X)
        stats = self._calculate_statistics(df)
        cols = min(len(stats),4)
        for i,(k,v) in enumerate(stats.items()):
            r,c = divmod(i,cols)
            ttk.Label(info, text=f'{k}: {v}', anchor='center', borderwidth=1,
                      relief='solid', padding=5).grid(row=r, column=c, sticky='nsew', padx=2, pady=2)
            info.grid_columnconfigure(c, weight=1)
        # top 5
        start_row = (len(stats)+cols-1)//cols
        ttk.Label(info, text='Top 5 Artists:', anchor='w', font=('TkDefaultFont',10,'bold')).grid(
            row=start_row, column=0, columnspan=cols, sticky='w', pady=(10,2), padx=2)
        top5 = df.head(5)
        for idx,row in enumerate(top5.itertuples(),1):
            r = start_row+1+(idx-1)//cols
            c = (idx-1)%cols
            ttk.Label(info, text=f'{idx}. {row.Artist} ({row.avg_rating:.2f})', anchor='w', padding=(15,0)).grid(
                row=r, column=c, sticky='w', padx=2, pady=2)

    def export_visualization(self, filepath):
        """Export chart and insights with filters applied."""
        df = self.fetch_data(**self.last_filters)
        stats = self._calculate_statistics(df)
        top5 = df.head(5)
        stats['Top 5 Artists'] = '\n'.join(
            f'{i+1}. {row.Artist} ({row.avg_rating:.2f})' for i,row in top5.iterrows()
        )
        export_chart_and_insights(self.fig, stats, filepath)

    def _calculate_font_size(self, num_items, is_label=False):
        base = 10 if is_label else 8
        scale = max(0.8, 1.2 - num_items*0.01)
        return max(base*scale, 8)

    def _calculate_statistics(self, df):
        if df.empty: return {'Status':'No data'}
        return {
            'Artists Analyzed': str(len(df)),
            'Average Rating': f"{df['avg_rating'].mean():.2f}",
            'Highest Rating': f"{df['avg_rating'].max():.2f}",
            'Lowest Rating': f"{df['avg_rating'].min():.2f}",
            'Rating Std Dev': f"{df['avg_rating'].std():.2f}",
            'Median Rating': f"{df['avg_rating'].median():.2f}",
            'Total Albums': str(df['album_count'].sum()),
            'Avg Albums/Artist': f"{df['album_count'].mean():.1f}"
        }

    def render(self, parent, **kwargs):
        for w in parent.winfo_children(): w.destroy()
        df = self.fetch_data(**kwargs)
        self._render_chart_section(parent, df)
        return self.fig
