import os
import re
from html import unescape

import pandas as pd

class DataProcessor:
    def clean_imported_data(self, value):
        """Clean individual values, preserving quotes and decoding entities."""
        # Handle missing or NaN values
        try:
            if pd.isna(value) or value is None:
                return ''
        except Exception:
            if value is None:
                return ''

        # Convert to string and decode HTML entities
        text = str(value)
        prev = None
        while text != prev:
            prev = text
            text = unescape(text)
        # Numeric entities
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
        # Strip control chars
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return text.strip()

    def _split_artists(self, artist_str):
        """
        Given a raw artist field, split into individual names.
        Splits on commas, ampersands (&), or the word 'and', then trims.
        """
        parts = re.split(r'\s*(?:,|&|and)\s*', artist_str)
        return [p for p in (p.strip() for p in parts) if p]

    def load_albums(self, filepath):
        """
        Load albums from CSV or Excel, auto-detecting format:
         • Split‑name CSV   → constructs 'Artist' from 'First Name' + 'Last Name'
         • Simple CSV       → 'artist','album',[rating]
         • Legacy RYM CSV   → fallback (expects 'Title' etc already present)
        Returns: list of cleaned dicts.
        """
        ext = os.path.splitext(filepath)[1].lower()
        # 1) Read into DataFrame
        if ext == '.csv':
            df = pd.read_csv(filepath, quotechar='"', escapechar='\\')
        elif ext in ('.xls', '.xlsx'):
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # Normalize header names
        df.columns = df.columns.str.strip()
        # Build lowercase→original map for lookup
        cols_lc = {col.lower(): col for col in df.columns}

        # 2) Detect & reshape
        # --- Split‑name format? ---
        if 'first name' in cols_lc or 'last name' in cols_lc:
            fn_col = cols_lc.get('first name', '')
            ln_col = cols_lc.get('last name', '')
            def make_artist(row):
                first = self.clean_imported_data(row.get(fn_col, ''))
                last  = self.clean_imported_data(row.get(ln_col, ''))
                return ' '.join(filter(None, [first, last]))
            df['Artist'] = df.apply(make_artist, axis=1)

        # --- Simple CSV format? ---
        elif 'artist' in cols_lc and 'album' in cols_lc:
            df = df.rename(columns={
                cols_lc['artist']: 'Artist',
                cols_lc['album']:  'Title',
                **({cols_lc['rating']: 'Rating'} if 'rating' in cols_lc else {})
            })

        # --- Legacy RYM export: leave columns as-is (expects Title, etc) ---
        else:
            pass

        # 3) Clean every cell
        for col in df.columns:
            df[col] = df[col].apply(self.clean_imported_data)

        # 4) Convert to list of dicts
        records = df.to_dict(orient='records')

        # 5) Split multi-artist entries
        for rec in records:
            raw = rec.get('Artist', '')
            rec['ArtistList'] = self._split_artists(raw)

        return records
