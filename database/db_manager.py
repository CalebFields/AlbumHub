import os
import sqlite3
import pandas as pd
import csv
from tkinter import messagebox

class DatabaseManager:
    def __init__(self, db_name='music.db', table_name='albums', db_dir='database'):
        # Ensure the database directory exists
        os.makedirs(db_dir, exist_ok=True)
        self.db_name = os.path.join(db_dir, db_name)
        self.table_name = table_name
        self.connect()
        self.create_tables()

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def create_tables(self):
        # Create the albums table with a Rating column
        self.cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            Artist TEXT,
            Title TEXT,
            Rating TEXT,
            Release_Date TEXT,
            Genres TEXT,
            Styles TEXT,
            Label TEXT,
            Country TEXT,
            Format TEXT,
            Tracklist TEXT,
            CoverArt TEXT,
            DiscogsID TEXT
        )""")
        self.conn.commit()

    def save_album(self, album):
        # ── 0) Only store albums with a valid DiscogsID ──
        discogs_id = str(album.get('DiscogsID', '') or '').strip()
        if not discogs_id:
            return  # skip albums not enriched via Discogs

        # ── 1) Ensure connection is open ──
        try:
            self.conn.execute("SELECT 1")
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            self.connect()

        # ── 2) Use the unified Artist field ──
        artist = str(album.get('Artist', '')).strip()

        # ── 3) Determine Release_Date (prefers explicit, falls back to DiscogsYear) ──
        release_date = album.get('Release_Date') or album.get('DiscogsYear') or ''

        # ── 4) Assemble record matching table columns, including Rating ──
        record = {
            'Artist':       artist,
            'Title':        album.get('Title', ''),
            'Rating':       str(album.get('Rating', '')).strip(),
            'Release_Date': release_date,
            'Genres':       album.get('Genres', ''),
            'Styles':       album.get('Styles', ''),
            'Label':        album.get('Label', ''),
            'Country':      album.get('Country', ''),
            'Format':       album.get('Format', ''),
            'Tracklist':    album.get('Tracklist', ''),
            'CoverArt':     album.get('CoverArt', ''),
            'DiscogsID':    discogs_id
        }

        # ── 5) Filter record to only existing columns ──
        self.cursor.execute(f"PRAGMA table_info({self.table_name})")
        valid_cols = {row[1] for row in self.cursor.fetchall()}
        cols = [c for c in record if c in valid_cols]
        vals = [record[c] for c in cols]

        # ── 6) Insert into database ──
        placeholders = ", ".join("?" for _ in cols)
        col_list     = ", ".join(cols)
        sql = f"INSERT INTO {self.table_name} ({col_list}) VALUES ({placeholders})"
        self.cursor.execute(sql, vals)
        self.conn.commit()

    def import_csv_data(self, filepath):
        try:
            df = pd.read_csv(filepath)
            df.to_sql(self.table_name, self.conn, if_exists='replace', index=False)
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def export_csv(self, filepath):
        try:
            df = pd.read_sql(f"SELECT * FROM {self.table_name}", self.conn)
            df.to_csv(filepath, index=False)
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def count_unique_artists(self):
        self.cursor.execute(f"SELECT COUNT(DISTINCT Artist) FROM {self.table_name}")
        return self.cursor.fetchone()[0]

    def export_albums_csv(self, csv_path='enriched_albums.csv'):
        """
        Dump the entire `albums` table (all columns) into a CSV.
        """
        cur = self.conn.cursor()
        # Fetch column names:
        cur.execute(f"PRAGMA table_info({self.table_name})")
        cols = [row[1] for row in cur.fetchall()]

        # Fetch all rows:
        cur.execute(f"SELECT * FROM {self.table_name}")
        rows = cur.fetchall()

        # Write out:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)
