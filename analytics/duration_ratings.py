import sqlite3
import pandas as pd
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase

class DurationRatingAnalytics(AnalyticsBase):
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        # SQL query to join albums and tracklist, summing durations
        sql = """
        SELECT
          a.id,
          a.Artist,
          a.Title,
          a.Rating,
          SUM(t.duration_sec) AS total_sec
        FROM albums a
        JOIN tracklist t ON t.album_id = a.id
        GROUP BY a.id
        HAVING COUNT(t.id) > 0
        """
        # Read the data into a DataFrame
        df = pd.read_sql_query(sql, sqlite3.connect(self.db_path))

        # Debug: Print column names to check for issues
        print("Columns in DataFrame:", df.columns)

        # Strip any extra whitespace from column names (if any)
        df.columns = df.columns.str.strip()

        # Debug: Print the cleaned column names
        print("Cleaned Columns in DataFrame:", df.columns)

        # Check if 'Rating' exists and matches the exact column name
        if 'Rating' not in df.columns:
            raise KeyError("The 'Rating' column is missing from the DataFrame")

        # Convert to minutes for readability
        df['duration_min'] = df['total_sec'] / 60

        # Return the cleaned and prepared DataFrame
        return df

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(6, 4))
        ax = fig.add_subplot(1, 1, 1)
        
        # Scatter plot of duration vs rating
        ax.scatter(df['duration_min'], df['Rating'], alpha=0.6)
        
        ax.set_xlabel('Total Duration (min)')
        ax.set_ylabel('Rating')
        ax.set_title('Album Duration vs. Rating')

        # Improve the readability of the plot
        ax.tick_params(axis='x', rotation=45)
        
        return fig

    def compute_insights(self, df: pd.DataFrame) -> str:
        """
        Compute insights based on the data (e.g., correlation, min/max values, averages).
        """
        # Ensure the 'rating' column exists and convert to numeric
        df.columns = df.columns.str.strip().str.lower()  # Make sure columns are cleaned and lowercase
        if 'rating' not in df.columns:
            raise KeyError("The 'rating' column is missing from the DataFrame")

        # Convert 'rating' to numeric, coercing errors to NaN
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

        # Handle any NaN values by dropping them (this applies to both duration and rating)
        df = df.dropna(subset=['duration_min', 'rating'])

        # Calculate correlation between duration and rating
        corr = df['duration_min'].corr(df['rating'])

        # Get the best and worst rated albums
        best = df.loc[df['rating'].idxmax()]
        worst = df.loc[df['rating'].idxmin()]

        # Additional insights
        avg_rating = df['rating'].mean()
        total_duration = df['duration_min'].sum()
        min_duration = df['duration_min'].min()
        max_duration = df['duration_min'].max()

        # Return formatted insights
        return (
            f"Correlation (duration vs rating): {corr:.2f}\n"
            f"Highest-rated: “{best['title']}” by {best['artist']} "
            f"({best['duration_min']:.1f} min, rating {best['rating']})\n"
            f"Lowest-rated:  “{worst['title']}” by {worst['artist']} "
            f"({worst['duration_min']:.1f} min, rating {worst['rating']})\n"
            f"Average Rating: {avg_rating:.2f}\n"
            f"Total Duration of Albums: {total_duration:.1f} min\n"
            f"Shortest Album: {min_duration:.1f} min\n"
            f"Longest Album: {max_duration:.1f} min"
        )
