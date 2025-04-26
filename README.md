# AlbumHub

AlbumHub is a desktop application for managing and ranking your music album collection. It imports your RateYourMusic exports, enriches them with metadata from the Discogs API, stores them in a local SQLite database, and provides an intuitive GUI for browsing and ranking your albums.

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

- **Import & Enrich**: Load CSV exports from RateYourMusic and enrich each album with metadata (genres, styles, cover art, etc.) from Discogs.
- **Browse Collection**: View your album collection with cover art thumbnails, filter by artist or genre, and sort by any field.
- **Ranking Game**: Play a tournament-style ranking game to sort albums by preference using a merge-sort–inspired interface.
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

   Or, if you don’t have a `requirements.txt`:

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

- **Import Tab**: Select your RateYourMusic CSV and click **Process File** to load and enrich albums.
- **Browse Collection Tab**: Browse, filter, and sort your collection.
- **Album Ranker Tab**: Play the ranking game and save or export your results.

## Project Structure

```
AlbumHub/
├── AlbumHubMain.py         # Entry point and app orchestration
├── .env                    # Discogs API credentials
├── enriched_albums.csv     # Default CSV export/import
├── api/
│   └── discogs_client.py   # Discogs API integration and enrichment logic
├── database/
│   └── db_manager.py       # SQLite DB management, import/export utilities
├── gui/
│   ├── __init__.py         # MainGUI orchestration
│   ├── import_tab.py       # UI & logic for importing/enriching albums
│   ├── browser_tab.py      # UI & logic for browsing collection
│   └── ranker_tab.py       # UI & logic for ranking albums
├── processing/
│   └── data_cleaner.py     # CSV loading and data cleaning utilities
├── ranking/
│   └── ranking_system.py   # Merge-sort–style ranking engine
├── utilities/
│   └── helpers.py          # Shared helper functions (logging, formatting)
└── requirements.txt        # Python dependencies
```

## Dependencies

- **tkinter** (built-in) for GUI
- **pandas** for CSV/Excel loading and data manipulation
- **requests** for HTTP calls to Discogs
- **python-dotenv** for configuration
- **Pillow** for image handling

## Module Overview

- **AlbumHubMain.py**: Initializes core services (DB, GUI, Discogs client, processor, ranking), and wires events.
- **discogs_client.py**: Handles rate-limited Discogs API requests; enriches album records with metadata.
- **data_cleaner.py**: Cleans raw CSV/Excel data, decodes HTML entities, and splits multi-artist fields.
- **db_manager.py**: Creates the `albums` table, saves enriched records, and supports CSV import/export.
- **import_tab.py**: GUI for selecting and processing CSV files in a background thread with progress logging.
- **browser_tab.py**: GUI for browsing and filtering your album collection with cover art thumbnails.
- **ranker_tab.py**: GUI for playing a pairwise ranking game to order albums by preference.
- **helpers.py**: Utility functions for formatting durations, logging messages, and resource paths.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3). You may redistribute and/or modify it under the terms of the GPLv3 as published by the Free Software Foundation. A copy of the license is included in the repository at [LICENSE](LICENSE), or you can view it online at https://www.gnu.org/licenses/gpl-3.0.en.html.

