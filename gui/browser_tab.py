import tkinter as tk
from tkinter import ttk
import sqlite3
import base64
import io
from PIL import Image, ImageTk
import re

class BrowserTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        # Cache for PhotoImage references to avoid GC
        self._image_cache = []

    def setup_browser_tab(self):
        self.browser_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.browser_tab, text="Browse Collection")

        main_frame = ttk.Frame(self.browser_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Build UI
        self.setup_search_filter_section(main_frame)
        self.setup_results_treeview(main_frame)

        # Inspect table schema and load data
        self.introspect_columns()
        self.load_filters()
        self.update_results()

    def setup_search_filter_section(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.filter_frame = ttk.Frame(control_frame)
        self.filter_frame.pack(side=tk.RIGHT)

        ttk.Label(self.filter_frame, text="Artist:").pack(side=tk.LEFT, padx=(0, 5))
        self.artist_var = tk.StringVar(value="All")
        self.artist_menu = tk.OptionMenu(
            self.filter_frame,
            self.artist_var,
            "All",
            command=self.on_filter
        )
        self.artist_menu.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(self.filter_frame, text="Genre:").pack(side=tk.LEFT, padx=(0, 5))
        self.genre_var = tk.StringVar(value="All")
        self.genre_menu = tk.OptionMenu(
            self.filter_frame,
            self.genre_var,
            "All",
            command=self.on_filter
        )
        self.genre_menu.pack(side=tk.LEFT)

    def setup_results_treeview(self, parent):
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Set row height to accommodate cover art thumbnails
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=70)

        # allow images in the first column (#0)
        self.tree = ttk.Treeview(
            tree_frame,
            show='tree headings'
        )

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def introspect_columns(self):
        # Dynamically detect all album columns
        cur = self.app.database.conn.cursor()
        try:
            cur.execute("PRAGMA table_info(albums)")
            cols = [row[1] for row in cur.fetchall()]
        except sqlite3.OperationalError:
            cols = []

        self.all_cols = cols
        self.image_col = 'CoverArt' if 'CoverArt' in cols else None

        # Configure tree columns and headings
        if self.image_col:
            display_cols = [c for c in cols if c != self.image_col]
            self.tree.config(columns=display_cols)
            self.tree.heading('#0', text=self.image_col)
            self.tree.column('#0', width=120, anchor='center')
        else:
            self.tree.config(columns=cols)

        for col in cols:
            if col == self.image_col:
                continue
            # set up sortable heading
            self.tree.heading(col, text=col,
                              command=lambda c=col: self.sort_column(c, False))
            width = 200 if col.lower() in ('artist', 'title') else 100
            self.tree.column(col, width=width)

    def load_filters(self):
        cur = self.app.database.conn.cursor()
        artists = set()
        try:
            cur.execute('SELECT "Artist" FROM albums')
            for (a,) in cur.fetchall():
                if a:
                    for p in re.split(r'\s*(?:,|&|and)\s*', a):
                        if p.strip(): artists.add(p.strip())
        except sqlite3.OperationalError:
            pass

        genres = set()
        if 'Genres' in self.all_cols:
            try:
                cur.execute('SELECT "Genres" FROM albums')
                for (g,) in cur.fetchall():
                    if g:
                        for part in str(g).split(','):
                            genres.add(part.strip())
            except sqlite3.OperationalError:
                pass

        artist_opts = ["All"] + sorted(artists)
        m = self.artist_menu['menu']
        m.delete(0, 'end')
        for art in artist_opts:
            m.add_command(label=art, command=lambda v=art: (self.artist_var.set(v), self.on_filter()))
        self.artist_var.set("All")

        genre_opts = ["All"] + sorted(genres)
        gm = self.genre_menu['menu']
        gm.delete(0, 'end')
        for gen in genre_opts:
            gm.add_command(label=gen, command=lambda v=gen: (self.genre_var.set(v), self.on_filter()))
        self.genre_var.set("All")

    def update_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._image_cache.clear()

        cols = self.all_cols.copy()
        sql_cols = [f'"{c}"' for c in cols]
        sql = f"SELECT {', '.join(sql_cols)} FROM albums"
        clauses, params = [], []
        if self.artist_var.get() != "All":
            clauses.append('"Artist" = ?')
            params.append(self.artist_var.get())
        if self.genre_var.get() != "All" and 'Genres' in cols:
            clauses.append('"Genres" LIKE ?')
            params.append(f"%{self.genre_var.get()}%")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY Artist, Title"

        cur = self.app.database.conn.cursor()
        try:
            cur.execute(sql, params)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []

        for row in rows:
            data = dict(zip(self.all_cols, row))
            img = None
            if self.image_col:
                b64 = data.pop(self.image_col)
                if b64:
                    try:
                        raw = base64.b64decode(b64)
                        buf = io.BytesIO(raw)
                        pil = Image.open(buf)
                        pil.thumbnail((64, 64))
                        tk_img = ImageTk.PhotoImage(pil)
                        self._image_cache.append(tk_img)
                        img = tk_img
                    except:
                        img = None
            values = [data[c] for c in self.all_cols if c != self.image_col]
            if img:
                self.tree.insert("", "end", text="", image=img, values=values)
            else:
                self.tree.insert("", "end", text="", values=values)

    def on_filter(self, _=None):
        self.update_results()

    def sort_column(self, col, reverse):
        # grab all values and sort
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        # rearrange
        for index, (_, k) in enumerate(l):
            self.tree.move(k, '', index)
        # reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def log_message(self, message):
        print(f"[BrowserTab] {message}")