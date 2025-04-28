# analytics/analytics_base.py
import tkinter as tk
from tkinter import ttk
import pandas as pd
from abc import ABC, abstractmethod
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sqlite3

class AnalyticsBase(ABC):
    """
    Abstract base class for analytics visualizations with strict chart/stats separation
    """
    def __init__(self, db_path: str, title: str = None):
        self.db_path = db_path
        self.title = title or self.__class__.__name__
        self.fig = None
        self._canvas = None

    import sqlite3
import pandas as pd
import re
from tkinter import ttk
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase

class AlbumsCount(AnalyticsBase):
    """
    Analyzes album distribution across artists with accurate filtering and statistics
    """
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetch and process data with proper SQL parameterization"""
        conn = sqlite3.connect(self.db_path)
        
        # Base query with safe parameterization
        query = """
            SELECT Album_ID, Artist, Genres, Release_Date 
            FROM albums 
            WHERE 1=1
        """
        params = []
        
        # Apply SQL-level filters
        if kwargs.get('genre'):
            query += " AND Genres LIKE ?"
            params.append(f"%{kwargs['genre']}%")
            
        if kwargs.get('decade') and kwargs['decade'] != 'All':
            start_year = int(kwargs['decade'][:-1])
            end_year = start_year + 9
            query += " AND CAST(SUBSTR(Release_Date, 1, 4) AS INTEGER BETWEEN ? AND ?"
            params.extend([start_year, end_year])
        
        # Get base dataset
        raw_df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Store raw data for stats calculations
        self.raw_df = raw_df
        
        # Process artists
        artist_split = (
            raw_df['Artist']
            .str.split(r'[,&]', regex=True)
            .apply(lambda x: [a.strip() for a in x] if x else [])
        )
        exploded_df = raw_df.assign(artist=artist_split).explode('artist')
        
        # Apply post-processing artist filter
        if kwargs.get('artist') and kwargs['artist'] != 'All':
            target_artist = kwargs['artist']
            exploded_df = exploded_df[exploded_df['artist'] == target_artist]
        
        # Aggregate results
        result = (
            exploded_df
            .groupby('artist', observed=True)
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )
        
        if result.empty:
            raise ValueError("No albums match the current filters")
            
        return result

    def create_figure(self, df: pd.DataFrame) -> Figure:
        """Create styled visualization with theme support"""
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Visualization styling
        bars = ax.barh(
            df['artist'], 
            df['count'],
            color='#4B8BBE',  # Matplotlib blue variant for dark themes
            height=0.7
        )
        
        # Add value labels
        for bar in bars:
            ax.text(
                bar.get_width() + 0.3,
                bar.get_y() + bar.get_height()/2,
                f"{bar.get_width()}",
                va='center',
                ha='left',
                color='white',
                fontsize=9
            )
        
        ax.set_title(f"Album Distribution by Artist\n{self.title}", pad=20)
        ax.set_xlabel("Number of Albums", labelpad=10)
        ax.xaxis.set_tick_params(pad=5)
        ax.yaxis.set_tick_params(pad=5)
        
        # Improve layout
        fig.tight_layout()
        return fig

    def _add_stats_box(self, parent, df):
        """Enhanced statistics panel with accurate calculations"""
        super()._add_stats_box(parent, df)
        
        stats_frame = parent.winfo_children()[-1]
        unique_albums = self.raw_df['Album_ID'].nunique()
        unique_artists = df['artist'].nunique()
        avg_per_artist = unique_albums / unique_artists if unique_artists else 0
        
        stats = [
            f"Total Albums: {unique_albums}",
            f"Unique Artists: {unique_artists}",
            f"Avg Albums/Artist: {avg_per_artist:.1f}",
            "Top Artists:"
        ]
        
        for label_text in stats[:-1]:
            ttk.Label(stats_frame, text=label_text).pack(anchor='w', padx=5, pady=2)
        
        # Add top artists with progressive indentation
        top_artists = df.head(5).itertuples()
        ttk.Label(stats_frame, text=stats[-1]).pack(anchor='w', padx=5, pady=(5,0))
        for idx, artist in enumerate(top_artists, 1):
            ttk.Label(stats_frame, 
                     text=f"{idx}. {artist.artist}: {artist.count}",
                     padding=(15, 0)).pack(anchor='w', padx=5)
            
    def _render_title_section(self, parent):
        """Renders the title section"""
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            title_frame, 
            text=self.title,
            font=('TkDefaultFont', 12, 'bold')
        ).pack()

    def _render_chart_section(self, parent, df):
        """Renders the chart visualization section"""
        self.fig = self.create_figure(df)
        self._apply_theme()
        
        canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self._canvas = canvas  # Maintain reference
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    def _render_stats_section(self, parent, df):
        """Renders the statistics section (completely separate from chart)"""
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        # Create two rows for stats display
        top_row = ttk.Frame(stats_frame)
        top_row.pack(fill=tk.X)
        bottom_row = ttk.Frame(stats_frame)
        bottom_row.pack(fill=tk.X)

        # Get statistics from implementation
        stats = self._calculate_statistics(df)
        
        # Distribute stats across two rows
        for i, (label, value) in enumerate(stats.items()):
            row = top_row if i < len(stats)//2 else bottom_row
            col = i if i < len(stats)//2 else i - len(stats)//2
            
            ttk.Label(row, text=f"{label}:", width=16, anchor='e').grid(
                row=0, column=col*2, padx=5, sticky='e')
            ttk.Label(row, text=value, width=12, anchor='w').grid(
                row=0, column=col*2+1, padx=5, sticky='w')
            
            row.columnconfigure(col*2, weight=1)
            row.columnconfigure(col*2+1, weight=1)

    def _render_empty_state(self, chart_container, stats_container):
        """Handles empty data state for both sections"""
        ttk.Label(chart_container, text="No data available").pack()
        ttk.Label(stats_container, text="No statistics available").pack()

    def _render_error_state(self, chart_container, stats_container, error_msg):
        """Handles error state for both sections"""
        ttk.Label(chart_container, text=f"Chart Error: {error_msg}", foreground="red").pack()
        ttk.Label(stats_container, text=f"Stats Error: {error_msg}", foreground="red").pack()

    def _calculate_statistics(self, df):
        """Default statistics calculation - should be overridden by subclasses"""
        return {
            "Records": str(len(df)),
            "First Entry": df.iloc[0][0] if len(df) > 0 else "N/A",
            "Last Entry": df.iloc[-1][0] if len(df) > 0 else "N/A"
        }

    def _apply_theme(self):
        """Applies consistent dark theme to matplotlib figure"""
        if self.fig:
            self.fig.patch.set_facecolor('#2E2E2E')
            for ax in self.fig.axes:
                ax.set_facecolor('#333333')
                # Set spine colors
                for spine in ax.spines.values():
                    spine.set_color('#FFFFFF')
                for element in [ax.title, ax.xaxis.label, ax.yaxis.label]:
                    element.set_color('#FFFFFF')
                ax.tick_params(colors='#FFFFFF', which='both')

    @abstractmethod
    def fetch_data(self, **kwargs):
        """Abstract method to fetch data - must be implemented by subclasses"""
        pass

    @abstractmethod
    def create_figure(self, df, **kwargs):
        """Abstract method to create visualization - must be implemented by subclasses"""
        pass

    def render(self, parent, **kwargs):
        """Unified render entry point for AnalyticsTab: builds title, chart, and stats areas."""
        # Clean previous content
        for widget in parent.winfo_children():
            widget.destroy()
    
        try:
            df = self.fetch_data(**kwargs)
    
            # Title
            self._render_title_section(parent)
    
            # Main body frames
            chart_container = ttk.Frame(parent)
            chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
            stats_container = ttk.Frame(parent)
            stats_container.pack(fill=tk.X, padx=5, pady=5)
    
            if df.empty:
                self._render_empty_state(chart_container, stats_container)
            else:
                self._render_chart_section(chart_container, df)
                self._render_stats_section(stats_container, df)
    
            return self.fig
    
        except Exception as e:
            # Create empty containers for error messages
            chart_container = ttk.Frame(parent)
            chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
            stats_container = ttk.Frame(parent)
            stats_container.pack(fill=tk.X, padx=5, pady=5)
    
            self._render_error_state(chart_container, stats_container, str(e))
    
            return None
