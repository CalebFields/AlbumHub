import sqlite3
import pandas as pd
from matplotlib.figure import Figure
from .analytics_base import AnalyticsBase
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk, messagebox


class GenreAverageRatings(AnalyticsBase):
    """
    Compute average album ratings grouped by genre, with proper Release_Date handling.
    """
    def fetch_data(self, artist: str = None, genre: str = None, decade: str = None) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT Genres, Rating, Release_Date FROM albums", conn
            )
            conn.close()

            # Drop missing data and coerce types
            df = df.dropna(subset=['Genres', 'Release_Date'])
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
            df = df.dropna(subset=['Rating'])

            # Expand genres into separate rows
            df = df.assign(
                genre=df['Genres'].str.split(',')
            ).explode('genre')
            df['genre'] = df['genre'].str.strip()

            # Filter by decade
            if decade and decade != 'All':
                df['year'] = pd.to_numeric(
                    df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0],
                    errors='coerce'
                )
                df = df[df['year'].between(int(decade.rstrip('s')), int(decade.rstrip('s')) + 9)]

            # Filter by genre
            if genre and genre != 'All':
                df = df[df['genre'] == genre]

            # Return empty DataFrame if no data
            if df.empty:
                return pd.DataFrame(columns=['genre', 'avg_rating'])

            # Compute average ratings per genre
            result = (
                df.groupby('genre')['Rating']
                  .mean()
                  .reset_index(name='avg_rating')
                  .sort_values('avg_rating', ascending=False)
            )

            return result

        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame(columns=['genre', 'avg_rating'])

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(1, 1, 1)
        ax.bar(df['genre'], df['avg_rating'])
        ax.set_ylabel("Average Rating")
        ax.set_title(self.title)

        # Rotate genre labels to improve readability
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df['genre'], rotation=45, ha='right')
        fig.tight_layout()

        return fig

    def render(self, parent: ttk.Frame, **kwargs):
        super().render(parent, **kwargs)

        # Locate "Additional Analysis" frame created by base.render
        stats_box = next(
            (c for c in parent.winfo_children()
             if isinstance(c, ttk.LabelFrame) and c.cget('text') == 'Additional Analysis'),
            None
        )
        if stats_box is None:
            return

        # Fetch the data
        df = self.fetch_data(**kwargs)
        total_genres = df.shape[0]
        overall_avg = df['avg_rating'].mean() if total_genres > 0 else 0

        # Clear previous stats using grid_forget to avoid destroying the layout
        for widget in stats_box.winfo_children():
            widget.grid_forget()

        # Display summary
        ttk.Label(
            stats_box,
            text=f"You have data for {total_genres} genres."
        ).grid(anchor='w', padx=5, pady=2)
        ttk.Label(
            stats_box,
            text=f"Overall average rating: {overall_avg:.2f}."
        ).grid(anchor='w', padx=5, pady=2)

        if total_genres > 0:
            top = df.iloc[0]
            bottom = df.iloc[-1]
            ttk.Label(
                stats_box,
                text=f"Highest-rated genre: {top['genre']} ({top['avg_rating']:.2f})."
            ).grid(anchor='w', padx=5, pady=2)
            ttk.Label(
                stats_box,
                text=f"Lowest-rated genre: {bottom['genre']} ({bottom['avg_rating']:.2f})."
            ).grid(anchor='w', padx=5, pady=2)
