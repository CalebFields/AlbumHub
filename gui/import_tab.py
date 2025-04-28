import os
import time
import csv
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from api.discogs_client import DiscogsClient

class ImportTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        # Rate-limit interval comes from config
        self.delay = float(self.app.config.get('api_delay', 1.2))
        # Processing queue for thread communication
        self.processing_queue = queue.Queue()
        self.discogs = DiscogsClient(logger=self.log_message)

    def log_message(self, message: str):
        """
        Receives log messages from DiscogsClient and routes them to the UI.
        """
        ts = datetime.now().strftime('%H:%M:%S')
        self.processing_queue.put(("message", f"[{ts}] {message}"))

    def setup_import_tab(self):
        self.import_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.import_tab, text='Import Data')

        main = ttk.Frame(self.import_tab)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.file_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready to import data")
        self.stop_event = threading.Event()
        self.processing_thread = None

        self._build_ui(main)

    def _build_ui(self, parent):
        # Instructions
        instruct = ttk.LabelFrame(parent, text="Instructions")
        instruct.pack(fill=tk.X, pady=10)
        ttk.Label(instruct, text=(
            "1. Export your RateYourMusic collection to CSV\n"
            "2. Select the file below\n"
            "3. Click 'Process File' to enrich with Discogs metadata\n"
            "4. View progress in the log"
        ), justify=tk.LEFT).pack(padx=10, pady=10)

        # File selection
        fs = ttk.Frame(parent)
        fs.pack(fill=tk.X, pady=10)
        ttk.Label(fs, text="Selected file:").pack(side=tk.LEFT)
        ttk.Entry(fs, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(fs, text="Browse...", command=self.select_input_file).pack(side=tk.LEFT)

        # Status and action
        ttk.Label(parent, textvariable=self.status_var).pack(fill=tk.X, pady=10)
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)
        self.process_button = ttk.Button(btn_frame, text="Process File", command=self.process_file_wrapper)
        self.process_button.pack(side=tk.LEFT)

        # Log output
        log_frame = ttk.LabelFrame(parent, text="Processing Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_text = tk.Text(log_frame, bg="#333", fg="#fff", wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def select_input_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")]
        )
        if path:
            self.file_path_var.set(path)
            self.status_var.set(f"Selected: {path}")

    def process_file_wrapper(self):
        input_file = self.file_path_var.get()
        if not input_file:
            messagebox.showwarning("No File", "Please select a CSV file.")
            return
        # Count total records
        try:
            with open(input_file, encoding='utf-8') as f:
                self.total_albums = sum(1 for _ in csv.DictReader(f))
        except Exception as e:
            self.processing_queue.put(("error", f"Failed to read file: {e}"))
            return

        # Prepare UI
        self.process_button.config(state=tk.DISABLED)
        self.status_var.set(f"Starting... 0/{self.total_albums}")
        self.log_text.delete('1.0', tk.END)
        self.processing_queue = queue.Queue()
        self.stop_event.clear()

        # Launch processing thread
        self.processing_thread = threading.Thread(
            target=self._threaded_process, args=(input_file,), daemon=True
        )
        self.processing_thread.start()
        self.root.after(100, self.check_processing_queue)

    def _threaded_process(self, filepath: str):
        try:
            albums = self.app.processor.load_albums(filepath)
        except Exception as e:
            self.processing_queue.put(("error", f"Load error: {e}"))
            return

        for idx, album in enumerate(albums, start=1):
            if self.stop_event.is_set():
                self.processing_queue.put(("error", "Stopped by user"))
                return

            artist = album.get('Artist', '').strip()
            title = album.get('Title', '').strip()

            # Skip if already in DB
            cur = self.app.database.conn.cursor()
            cur.execute(
                "SELECT 1 FROM albums WHERE Artist = ? AND Title = ? LIMIT 1",
                (artist, title)
            )
            if cur.fetchone():
                self.log_message(f"Skipping existing: {artist} - {title}")
                continue

            start_time = time.monotonic()
            try:
                enriched = self.discogs.enrich_album(album)
                enriched['Rating'] = album.get('Rating', '')
                self.app.database.save_album(enriched)
            except Exception as e:
                self.processing_queue.put(("error", f"Discogs error for {artist} - {title}: {e}"))
                time.sleep(self.delay)
                continue

            # Throttle
            time.sleep(self.delay)

            elapsed = time.monotonic() - start_time
            eta_secs = (self.total_albums - idx) * elapsed
            mins, secs = divmod(int(eta_secs), 60)
            eta = f"{mins}m {secs}s"
            ts = datetime.now().strftime('%H:%M:%S')
            marker = '✓' if enriched.get('CoverArt') else '✗'
            msg = f"[{ts} | {elapsed:.1f}s | ETA: {eta}] Processing: {artist} - {title} ({idx}/{self.total_albums}) {marker}"
            self.processing_queue.put(("message", msg))

        self.processing_queue.put(("complete",))

    def check_processing_queue(self):
        try:
            while True:
                kind, *data = self.processing_queue.get_nowait()
                if kind == "message":
                    msg, = data
                    at_bot = self.log_text.yview()[1] >= 0.999
                    self.log_text.insert(tk.END, msg + "\n")
                    if at_bot:
                        self.log_text.see(tk.END)
                    if 'Processing:' in msg:
                        self.status_var.set(msg.split('] ')[-1])
                elif kind == "error":
                    err, = data
                    self.log_text.insert(tk.END, "🔴 " + err + "\n")
                    self.log_text.see(tk.END)
                    messagebox.showerror("Error", err)
                elif kind == "complete":
                    return self._on_processing_complete()
        except queue.Empty:
            pass

        if self.processing_thread and self.processing_thread.is_alive():
            self.root.after(100, self.check_processing_queue)
        else:
            self.process_button.config(state=tk.NORMAL)

    def _on_processing_complete(self):
        self.log_text.insert(tk.END, "✅ All done!\n")
        self.log_text.see(tk.END)
        self.status_var.set("Completed successfully")
        self.process_button.config(state=tk.NORMAL)

        # Auto-export enriched albums CSV
        try:
            out = 'enriched_albums.csv'
            self.app.database.export_csv(out)
            self.log_text.insert(tk.END, f"✅ Exported enriched data to {out}\n")
            self.log_text.see(tk.END)
        except Exception as e:
            self.log_text.insert(tk.END, f"🔴 Export failed: {e}\n")
            self.log_text.see(tk.END)
            messagebox.showerror("Export Error", str(e))

        # Auto-load default CSV into view
        try:
            default = self.app.config.get('default_csv', 'enriched_albums.csv')
            self.app.database.import_csv_data(default)
            self.log_text.insert(tk.END, f"✅ Loaded {default} into the collection view\n")
            self.log_text.see(tk.END)
        except Exception as e:
            self.log_text.insert(tk.END, f"🔴 Load into view failed: {e}\n")
            self.log_text.see(tk.END)

    def on_close(self):
        self.stop_event.set()
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2)
