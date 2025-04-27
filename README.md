# AlbumHub

AlbumHub is a desktop application for managing and ranking your music album collection. It imports your RateYourMusic exports (or any CSV file with artist, album, and rating), enriches them with metadata from the Discogs API, stores them in a local SQLite database, and provides an intuitive GUI for browsing, analyzing, and ranking your albums.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Module Overview](#module-overview)
- [License](#license)

## Features

- **Import & Enrich**: Load CSV exports from RateYourMusic or compatible files and enrich each album with metadata (genres, styles, cover art, etc.) from Discogs.
- **Browse Collection**: View your album collection with cover art thumbnails, filter by artist or genre, and sort by any field.
- **Ranking Game**: Play a tournament-style ranking game to sort albums by preference using a merge-sort–inspired interface.
- **Analytics Tab**: Visualize genre trends, artist ratings, rating distributions, and more with interactive charts.
- **Persistence**: Store all data in a local SQLite database; export and import your enriched collection to/from CSV.

## Prerequisites

- **Python 3.8+**
- Internet connection for Discogs API calls

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/AlbumHub.git
   cd AlbumHub
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Or, manually:

   ```bash
   pip install pandas requests python-dotenv Pillow
   ```

## Configuration

1. Create a `.env` file in the project root with your Discogs API credentials:

   ```ini
   DISCOGS_KEY=your_discogs_key
   DISCOGS_SECRET=your_discogs_secret
   ```

2. (Optional) Adjust settings in `AlbumHubMain.py`’s `load_configuration` method.

## Usage

Run the application:

```bash
python AlbumHubMain.py
```

- **Import Tab**: Select your RateYourMusic CSV (or a compatible file with artist/album/rating columns) and click **Process File** to load and enrich albums.
- **Browse Collection Tab**: Browse, filter, and sort your collection.
- **Album Ranker Tab**: Play the ranking game and save or export your results.
- **Analytics Tab**: Explore graphical analysis of your collection.

## Project Structure

```
AlbumHub/
├── AlbumHubMain.py         # Entry point and app orchestration
├── .env                    # Discogs API credentials
├── api/
│   └── discogs_client.py   # Discogs API integration
├── analytics/
│   ├── analytics_base.py   # Base class for visualizations
│   ├── album_count.py      # Albums per artist chart
│   ├── artist_ratings.py   # Average artist ratings
│   ├── genre_ratings.py    # Ratings by genre
│   ├── rating_distro.py    # Distribution of ratings
│   ├── decade_trends.py    # Trends by decade
│   └── __init__.py
├── database/
│   └── db_manager.py       # SQLite database management
├── gui/
│   ├── __init__.py         # Main GUI initialization
│   ├── import_tab.py       # Import/enrichment tab
│   ├── browser_tab.py      # Collection browser tab
│   ├── ranker_tab.py       # Album ranking game tab
│   └── analytics_tab.py    # Analytics/visualization tab
├── processing/
│   └── data_cleaner.py     # Data loading and cleaning utilities
├── ranking/
│   └── ranking_system.py   # Merge sort–style ranking engine
├── utilities/
│   └── helpers.py          # Shared utilities
├── build/                  # Build artifacts (if compiled)
├── dist/                   # Distribution folder (if compiled)
├── .gitignore              # Git ignored files
├── LICENSE                 # GPLv3 License
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## Dependencies

- **tkinter** (built-in) for GUI
- **pandas** for data manipulation
- **requests** for Discogs API calls
- **python-dotenv** for loading environment variables
- **Pillow** for image processing
- **matplotlib** for analytics visualizations

## Module Overview

- **AlbumHubMain.py**: Initializes database, Discogs client, data processor, GUI, analytics, and ranking systems.
- **discogs_client.py**: Discogs API client with rate limiting.
- **analytics/**: Folder of modular analytics graphs (each extend `AnalyticsBase`).
- **data_cleaner.py**: CSV/Excel loading, data normalization.
- **db_manager.py**: Manages schema, inserts, queries, CSV import/export.
- **gui/**: GUI tabs (Import, Browse, Rank, Analytics).
- **ranking_system.py**: Tournament-style ranking algorithm.
- **helpers.py**: Utility functions (e.g., logging, string formatting).

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3). See [LICENSE](LICENSE) for details.
