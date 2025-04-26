import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import csv
from datetime import datetime
from api.discogs_client import DiscogsClient

class ImportTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        # Fixed rate-limit interval (seconds)
        self.delay = float(self.app.config.get('api_delay', 1.2))
        # Initialize processing queue before passing logger
        self.processing_queue = queue.Queue()
        # Discogs client uses our internal log_message to report status
        self.discogs = DiscogsClient(logger=self.log_message)

    def log_message(self, message):
        """
        Receives log messages from DiscogsClient and routes them to the UI.
        """
        ts = datetime.now().strftime('%H:%M:%S')
        self.processing_queue.put(("message", f"[{ts}] {message}"))

    def setup_import_tab(self):
        # Main container
        self.import_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.import_tab, text='Import Data')

        main_frame = ttk.Frame(self.import_tab, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # State variables
        self.file_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready to import data")
        self.stop_event = threading.Event()
        self.processing_thread = None

        # Build UI
        self.setup_instructions_section(main_frame)
        self.setup_file_selection_section(main_frame)
        self.setup_status_section(main_frame)
        self.setup_action_buttons(main_frame)
        self.setup_log_output(main_frame)

    def setup_instructions_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Instructions", style='TFrame')
        frame.pack(fill=tk.X, pady=(0, 20))
        text = (
            "1. Export your RateYourMusic collection to CSV\n"
            "2. Select the file below\n"
            "3. Click 'Process File' to enrich with Discogs metadata\n"
            "4. View progress in the log"
        )
        ttk.Label(frame, text=text, style='TLabel', justify=tk.LEFT).pack(padx=10, pady=10)

    def setup_file_selection_section(self, parent):
        frame = ttk.Frame(parent, style='TFrame')
        frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(frame, text="Selected file:", style='TLabel').pack(side=tk.LEFT, padx=5)
        ttk.Entry(frame, textvariable=self.file_path_var, width=50, style='TEntry').pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Browse...", command=self.select_input_file).pack(side=tk.LEFT, padx=5)

    def setup_status_section(self, parent):
        ttk.Label(parent, textvariable=self.status_var, style='TLabel').pack(fill=tk.X, pady=(0, 20))

    def setup_action_buttons(self, parent):
        frame = ttk.Frame(parent, style='TFrame')
        frame.pack(fill=tk.X)
        self.process_button = ttk.Button(frame, text="Process File", command=self.process_file_wrapper)
        self.process_button.pack(side=tk.LEFT, padx=5)

    def setup_log_output(self, parent):
        frame = ttk.LabelFrame(parent, text="Processing Log", style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(frame, bg="#333333", fg="#FFFFFF", wrap=tk.WORD)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def select_input_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files","*.csv"), ("All files","*")]
        )
        if path:
            self.file_path_var.set(path)
            self.app.current_file = path
            self.status_var.set(f"Selected: {path}")

    def process_file_wrapper(self):
        input_file = self.file_path_var.get()
        if not input_file:
            messagebox.showwarning("No File", "Please select a CSV file.")
            return
        # Count total records
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                self.total_albums = sum(1 for _ in csv.DictReader(f))
        except Exception as e:
            self.processing_queue.put(("error", f"Failed to read file: {e}"))
            return

        # Prepare UI
        self.process_button['state'] = tk.DISABLED
        self.status_var.set(f"Starting... 0/{self.total_albums}")
        self.log_text.delete('1.0', tk.END)
        self.processing_queue = queue.Queue()
        self.stop_event.clear()

        # Launch thread
        self.processing_thread = threading.Thread(
            target=self._threaded_process,
            args=(input_file,),
            daemon=True
        )
        self.processing_thread.start()
        self.root.after(100, self.check_processing_queue)

    def _threaded_process(self, filepath):
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
            rating = album.get('Rating', '')

            # Skip if already in DB
            cur = self.app.database.conn.cursor()
            cur.execute(
                "SELECT 1 FROM albums WHERE artist = ? AND title = ? LIMIT 1",
                (artist, title)
            )
            if cur.fetchone():
                ts = datetime.now().strftime('%H:%M:%S')
                self.processing_queue.put(("message", f"[{ts}] Skipping: {artist} - {title}"))
                continue

            # Perform API call with fixed delay throttle
            start_proc = time.monotonic()
            try:
                enriched = self.discogs.enrich_album(album)
                enriched['Rating'] = rating
                self.app.database.save_album(enriched)
            except Exception as e:
                err_msg = f"Discogs retrieval failed for {artist} - {title}: {e}"
                self.processing_queue.put(("message", err_msg))
                self.processing_queue.put(("error", err_msg))
                time.sleep(self.delay)
                continue

            # Sleep fixed delay to throttle
            time.sleep(self.delay)

            # timing & ETA
            end_proc = time.monotonic()
            proc_time = end_proc - start_proc
            remaining = (self.total_albums - idx) * proc_time
            mins, secs = divmod(int(remaining), 60)
            eta = f"{mins}m {secs}s"
            marker = '✓' if enriched.get('CoverArt') else '✗'
            ts = datetime.now().strftime('%H:%M:%S')
            msg = (
                f"[{ts} | {proc_time:.1f}s | ETA: {eta}] "
                f"Processing: {artist} - {title} ({idx}/{self.total_albums}) {marker}"
            )
            self.processing_queue.put(("message", msg))

        self.processing_queue.put(("complete",))

    def check_processing_queue(self):
        try:
            while True:
                kind, *data = self.processing_queue.get_nowait()
                if kind == 'message':
                    msg, = data
                    # Were we already at the bottom?
                    at_bottom = self.log_text.yview()[1] >= 0.999
                    self.log_text.insert(tk.END, msg + "\n")
                    # Only auto-scroll if the user was already looking at the tail
                    if at_bottom:
                        self.log_text.see(tk.END)
                    if 'Processing:' in msg:
                        self.status_var.set(msg.split('] ')[-1])
                elif kind == 'error':
                    err, = data
                    self.log_text.insert(tk.END, "🔴 " + err + "\n")
                    self.log_text.see(tk.END)
                    messagebox.showerror("Error", err)
                elif kind == 'complete':
                    return self._on_processing_complete()
        except queue.Empty:
            pass
        if self.processing_thread and self.processing_thread.is_alive():
            self.root.after(100, self.check_processing_queue)
        else:
            self.process_button['state'] = tk.NORMAL

    def _on_processing_complete(self):
        self.log_text.insert(tk.END, "✅ All done!\n")
        self.log_text.see(tk.END)
        self.status_var.set("Completed successfully")
        self.process_button['state'] = tk.NORMAL

        try:
            csv_path = 'enriched_albums.csv'
            self.app.database.export_csv(csv_path)
            self.log_text.insert(tk.END, f"✅ Exported enriched data to {csv_path}\n")
            self.log_text.see(tk.END)
        except Exception as e:
            err = f"Failed to export enriched_albums.csv: {e}"
            self.log_text.insert(tk.END, f"🔴 {err}\n")
            self.log_text.see(tk.END)
            messagebox.showerror("Export Error", err)

        try:
            default_csv = self.app.config.get('default_csv', csv_path)
            self.app.database.import_csv_data(default_csv)
            self.log_text.insert(tk.END, f"✅ Loaded {default_csv} into the collection view\n")
            self.log_text.see(tk.END)
        except Exception as e:
            err = f"Failed to import CSV into view: {e}"
            self.log_text.insert(tk.END, f"🔴 {err}\n")
            self.log_text.see(tk.END)

    def on_close(self):
        self.stop_event.set()
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2)