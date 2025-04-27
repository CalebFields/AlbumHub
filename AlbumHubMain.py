import tkinter as tk
from tkinter import messagebox
import sqlite3

from gui import MainGUI
from database.db_manager import DatabaseManager
from api.discogs_client import DiscogsClient
from processing.data_cleaner import DataProcessor
from ranking.ranking_system import RankingSystem


class AlbumHub:
    def __init__(self, root):
        self.root = root
        self.config = self.load_configuration()

        # Core services
        # Initialize database first so GUI tabs can access it
        self.database = DatabaseManager()
        # Re-open DB for thread-safe access
        self.database.disconnect()
        self.database.conn   = sqlite3.connect(self.database.db_name, check_same_thread=False)
        self.database.cursor = self.database.conn.cursor()

        # Then setup the GUI (tabs will reference self.database)
        self.gui = MainGUI(self, root)

        # Discogs, data cleaning, and ranking systems
        self.discogs   = DiscogsClient()
        self.processor = DataProcessor()
        self.ranker    = RankingSystem()

        # Wire import-tab logic
        self.gui.import_tab.process_button.configure(
            command=self.gui.import_tab.process_file_wrapper
        )

        # ——— Hook in AnalyticsTab ———
        from gui.analytics_tab import AnalyticsTab
        # give it the same app and the notebook reference from MainGUI
        self.gui.analytics_tab = AnalyticsTab(self, self.gui.notebook)
        self.gui.analytics_tab.setup_analytics_tab()
        # ————————————————————————

        # Handle database import/export notifications
        self.gui.bind('<<DatabaseUpdate>>', self.handle_database_update)

    def load_configuration(self):
        return {
            'api_delay':    1.5,
            'default_csv': 'enriched_albums.csv'
        }

    def handle_database_update(self, event):
        try:
            op, fname = event.data['operation'], event.data['filename']
            if op == 'export':
                self.database.export_csv(fname)
            elif op == 'import':
                self.database.import_csv_data(fname)
            self.gui.update_database_view()
        except Exception as e:
            self.handle_error("Database update failed", e)

    def handle_error(self, context, error):
        msg = f"{context}: {error}"
        self.gui.update_status(msg)
        self.gui.show_error("Application Error", msg)
        self.database.rollback()

    def shutdown(self):
        # Ensure import thread stops cleanly
        try:
            self.gui.import_tab.on_close()
        except Exception:
            pass
        self.database.disconnect()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = AlbumHub(root)
    root.protocol("WM_DELETE_WINDOW", app.shutdown)
    root.mainloop()
