import sqlite3
import pandas as pd
import tkinter as tk
import textwrap
from math import ceil
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .analytics_base import AnalyticsBase

class RegionRatings(AnalyticsBase):
    """
    Computes and visualizes average album ratings by country and super-region.
    Each country contributes to its own bar and its region's bar,
    but if the Country field itself is a region (e.g., 'Europe'), it appears only once as a region.
    """
    # Define known super-regions and bar colors
    REGIONS = {'North America', 'Europe', 'Asia', 'Oceania', 'South America', 'Africa', 'Other'}
    REGION_COLOR = '#81a1c1'   # accent for regions
    COUNTRY_COLOR = '#4b72b8'  # accent for countries

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        artist = kwargs.get('artist')
        genre_filter = kwargs.get('genre')
        decade = kwargs.get('decade')
        self.last_filters = {'artist': artist, 'genre': genre_filter, 'decade': decade}

        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT Artist, Genres, Country, Release_Date, Rating FROM albums", conn
        )
        conn.close()

        # Clean and preprocess
        df = df.dropna(subset=['Country', 'Rating'])
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
        df = df.dropna(subset=['Rating'])
        df['year'] = df['Release_Date'].astype(str).str.extract(r"(\d{4})")[0].astype(float, errors='ignore')
        df['decade'] = (df['year'] // 10 * 10).astype(int).astype(str) + 's'

        # Apply filters
        if artist and artist != 'All':
            df = df[df['Artist'].str.contains(artist, na=False, regex=False)]
        if genre_filter and genre_filter != 'All':
            df = df[df['Genres'].astype(str).str.contains(genre_filter, na=False, regex=False)]
        if decade and decade != 'All':
            start = int(decade[:-1])
            df = df[(df['year'] >= start) & (df['year'] < start + 10)]

        if df.empty:
            return pd.DataFrame(columns=['Label', 'avg_rating', 'count'])

        # Split multi-country entries
        df = df.assign(
            CountryList=df['Country'].astype(str).str.split(r',\s*|\s*&\s*|\s+and\s+')
        ).explode('CountryList')
        df['Country'] = df['CountryList'].str.strip()
        df = df[df['Country'] != '']

        # Map each country to a super-region
        df['Region'] = df['Country'].apply(self._map_country_to_region)

        # Aggregate country-level data, excluding rows where country equals a region name
        country_agg = (
            df.groupby('Country', observed=True)
              .agg(avg_rating=('Rating', 'mean'), count=('Rating', 'size'))
              .reset_index()
        )
        country_agg = country_agg[~country_agg['Country'].isin(self.REGIONS)]

        # Aggregate region-level data
        region_agg = (
            df.groupby('Region', observed=True)
              .agg(avg_rating=('Rating', 'mean'), count=('Rating', 'size'))
              .reset_index()
        )

        # Prepare unified DataFrame
        country_agg.rename(columns={'Country': 'Label'}, inplace=True)
        region_agg.rename(columns={'Region': 'Label'}, inplace=True)
        full_df = pd.concat([region_agg, country_agg], ignore_index=True)
        full_df = full_df.sort_values('avg_rating', ascending=False)[['Label', 'avg_rating', 'count']]
        return full_df

    def _map_country_to_region(self, country: str) -> str:
        key = country.lower()
        if key in {'usa', 'united states', 'canada', 'mexico'}:
            return 'North America'
        if key in {'uk', 'united kingdom', 'germany', 'france', 'italy', 'spain', 'netherlands', 'sweden', 'norway', 'switzerland'}:
            return 'Europe'
        if key in {'china', 'japan', 'south korea', 'india', 'taiwan'}:
            return 'Asia'
        if key in {'australia', 'new zealand'}:
            return 'Oceania'
        if key in {'brazil', 'argentina', 'chile', 'colombia'}:
            return 'South America'
        if key in {'south africa', 'nigeria', 'egypt'}:
            return 'Africa'
        return 'Other'

    def create_figure(self, df: pd.DataFrame, **kwargs) -> Figure:
        labels = df['Label'].tolist()
        wrapped = [textwrap.fill(lbl, 12) for lbl in labels]
        colors = [
            self.REGION_COLOR if lbl in self.REGIONS else self.COUNTRY_COLOR
            for lbl in labels
        ]

        fig = Figure(figsize=(max(12, len(labels) * 0.8), 6), constrained_layout=False)
        ax = fig.add_subplot(111)
        ax.bar(range(len(labels)), df['avg_rating'], color=colors, edgecolor='#444444', width=0.8)

        # Theme styling
        fig.patch.set_facecolor('#2E2E2E')
        ax.set_facecolor('#333333')
        ax.yaxis.grid(True, color='#555555', linestyle='--', linewidth=0.5)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.tick_params(axis='y', colors='white')

        ax.set_xticks(range(len(wrapped)))
        ax.set_xticklabels(wrapped, rotation=60, ha='right', va='top', color='white', fontsize=9)

        fig.subplots_adjust(bottom=0.4, left=0.05, right=0.95)

        ax.set_xlabel('Country / Region', color='white', fontsize=12)
        ax.set_ylabel('Average Rating', color='white', fontsize=12)
        ax.set_title(self.title, color='white', fontsize=14, pad=10)
        return fig

    def render(self, parent: ttk.Frame, **kwargs) -> Figure:
        for w in parent.winfo_children():
            w.destroy()
        df = self.fetch_data(**kwargs)
        vis = ttk.Labelframe(parent, text='Visualization')
        vis.pack(fill=tk.BOTH, expand=False, pady=(0, 5))
        fig = self.create_figure(df, **kwargs)
        FigureCanvasTkAgg(fig, master=vis).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Insights
        info = ttk.Labelframe(parent, text='Insights')
        info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats = self._calculate_insights(df)

        metrics = [(k, v) for k, v in stats.items() if not k.lower().startswith(('top', 'bottom'))]
        lists = [(k, v) for k, v in stats.items() if k.lower().startswith(('top', 'bottom'))]

        # Determine columns: stretch metrics to fill width
        cols = max(len(metrics), 1)
        # Configure equal weight for all columns
        for c in range(cols):
            info.grid_columnconfigure(c, weight=1)

        # Place metrics in a single row across all columns
        for idx, (k, v) in enumerate(metrics):
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=0, column=idx, sticky='nsew', padx=2, pady=2)

        # Place lists starting on the next row
        bottom_start = 1
        for idx, (k, v) in enumerate(lists):
            r = bottom_start + (idx // cols)
            c = idx % cols
            lbl = ttk.Label(info, text=f"{k}: {v}", anchor='w', relief='solid', borderwidth=1, padding=5)
            lbl.grid(row=r, column=c, sticky='nsew', padx=2, pady=2)

        return fig

    def _calculate_insights(self, df: pd.DataFrame) -> dict:
        insights = {}
        if df.empty:
            insights['Status'] = 'No data'
            return insights
        ratings = df['avg_rating']
        insights['Entries Analyzed'] = len(df)
        insights['Overall Avg Rating'] = f"{ratings.mean():.2f}"
        insights['Median Avg Rating'] = f"{ratings.median():.2f}"
        insights['Rating Std Dev'] = f"{ratings.std():.2f}"
        insights['Rating Range'] = f"{ratings.max() - ratings.min():.2f}"
        # Lists
        for field, col in [('Album Count', 'count'), ('Avg Rating', 'avg_rating')]:
            top3 = df.nlargest(3, col)
            bottom3 = df.nsmallest(3, col)
            insights[f"Top 3 by {field}"] = "; ".join(
                f"{row.Label} ({getattr(row, col) if field=='Album Count' else f'{getattr(row, col):.2f}'})"
                for row in top3.itertuples()
            )
            insights[f"Bottom 3 by {field}"] = "; ".join(
                f"{row.Label} ({getattr(row, col) if field=='Album Count' else f'{getattr(row, col):.2f}'})"
                for row in bottom3.itertuples()
            )
        return insights
