# analytics/average_ratings.py
"""
Subclass of AnalyticsBase to compute and plot average album ratings by artist.
"""
import sqlite3
import pandas as pd
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase

class AverageRatings(AnalyticsBase):
    """
    Analytics for computing average album ratings per artist.
    """
    def fetch_data(self, artist: str = None) -> pd.DataFrame:
        """
        Fetches average ratings, optionally filtering by a single artist.
        Ensures consistent lowercase column names.
        """
        conn = sqlite3.connect(self.db_path)
        params = []
        sql = (
            """
            SELECT artist, AVG(rating) AS avg_rating
            FROM albums
            """
        )
        if artist and artist != "All":
            sql += " WHERE artist = ?"
            params.append(artist)
        sql += " GROUP BY artist ORDER BY avg_rating DESC"
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()

        # normalize column names to lowercase
        df.columns = [col.strip().lower() for col in df.columns]
        return df

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        """
        Creates a bar chart of average ratings using explicit tick positions.
        """
        # dynamically pick the first two columns
        x_col, y_col = df.columns[:2]
        labels = df[x_col].tolist()
        values = df[y_col].tolist()

        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)

        # plot against integer positions, then label those ticks
        positions = list(range(len(labels)))
        ax.bar(positions, values)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha='right')

        ax.set_xlabel(x_col.title())
        ax.set_ylabel(y_col.replace('_', ' ').title())
        ax.set_title(self.title)
        fig.tight_layout()
        return fig
