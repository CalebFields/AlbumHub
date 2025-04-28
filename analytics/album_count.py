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