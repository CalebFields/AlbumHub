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
        self._image_cache = []  # hold references to PhotoImage

    def setup_browser_tab(self):
        self.browser_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.browser_tab, text="Browse Collection")

        main_frame = ttk.Frame(self.browser_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.setup_search_filter_section(main_frame)
        self.setup_results_treeview(main_frame)

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

        style = ttk.Style(self.root)
        style.configure("Treeview",
                        font=('Helvetica', 10),
                        rowheight=70,  # match or slightly exceed thumbnail height
                        background="#333333",
                        foreground="#FFFFFF",
                        fieldbackground="#333333"
        )
        style.configure("Treeview.Heading",
                        font=('Helvetica', 11, 'bold'),
                        background="#3C3F41",
                        foreground="#FFFFFF",
                        padding=(5, 2)
        )

        style.map("Treeview", background=[('selected', '#4A6984')], foreground=[('selected', '#FFFFFF')])

        self.tree = ttk.Treeview(tree_frame, show='tree headings')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)

    def introspect_columns(self):
        cur = self.app.database.conn.cursor()
        try:
            cur.execute("PRAGMA table_info(albums)")
            cols = [row[1] for row in cur.fetchall()]
        except sqlite3.OperationalError:
            cols = []

        self.all_cols = cols
        self.image_col = 'CoverArt' if 'CoverArt' in cols else None
        self.id_col = 'id' if 'id' in cols else None

        display_cols = [c for c in cols if c not in (self.image_col, self.id_col)]
        display_cols.append('Tracks')
        self.display_cols = display_cols

        self.tree.config(columns=display_cols)
        self.tree.heading('#0', text=self.image_col or '')
        self.tree.column('#0', width=120, anchor='center')

        for col in display_cols:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
            if col == 'Tracks':
                self.tree.column(col, width=80, anchor='center')
            else:
                width = 200 if col.lower() in ('artist', 'title') else 100
                self.tree.column(col, width=width)

    def load_filters(self):
        cur = self.app.database.conn.cursor()
        artists = set()
        for (a,) in cur.execute('SELECT Artist FROM albums'):
            if a:
                for p in re.split(r'\s*(?:,|&|and)\s*', a):
                    if p.strip():
                        artists.add(p.strip())
        artist_opts = ["All"] + sorted(artists)
        menu = self.artist_menu['menu']
        menu.delete(0, 'end')
        for art in artist_opts:
            menu.add_command(label=art, command=lambda v=art: (self.artist_var.set(v), self.on_filter()))
        self.artist_var.set("All")

        genres = set()
        if 'Genres' in self.all_cols:
            for (g,) in cur.execute('SELECT Genres FROM albums'):
                if g:
                    for part in re.split(r'\s*(?:,|&|and)\s*', g):
                        if part.strip():
                            genres.add(part.strip())
        genre_opts = ["All"] + sorted(genres)
        gmenu = self.genre_menu['menu']
        gmenu.delete(0, 'end')
        for gen in genre_opts:
            gmenu.add_command(label=gen, command=lambda v=gen: (self.genre_var.set(v), self.on_filter()))
        self.genre_var.set("All")

    def update_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._image_cache.clear()

        cols = self.all_cols.copy()
        cols_sql = [f'"{c}"' for c in cols]
        sql = f"SELECT {', '.join(cols_sql)} FROM albums"
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
            rows = cur.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []

        for row in rows:
            data = dict(zip(self.all_cols, row))
            img = None
            if self.image_col:
                b64 = data.get(self.image_col)
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
            album_id = data.get(self.id_col)
            values = [data.get(c, '') for c in self.display_cols[:-1]] + ['View']
            if img:
                self.tree.insert('', 'end', text='', image=img, values=values, tags=(str(album_id),))
            else:
                self.tree.insert('', 'end', text='', values=values, tags=(str(album_id),))

    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col = self.tree.identify_column(event.x)
        col_idx = int(col.replace('#','')) - 1
        col_name = self.tree['columns'][col_idx]
        if col_name != 'Tracks':
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        tags = self.tree.item(item, 'tags')
        if not tags:
            return
        album_id = tags[0]
        self.open_tracklist_window(album_id)

    def open_tracklist_window(self, album_id):
        win = tk.Toplevel(self.root)
        win.title("Tracklist")
        tree = ttk.Treeview(win, columns=('#', 'Title', 'Duration'), show='headings')
        tree.heading('#', text='No.')
        tree.heading('Title', text='Track Title')
        tree.heading('Duration', text='Duration (s)')
        sb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        cur = self.app.database.conn.cursor()
        cur.execute("SELECT track_number, title, duration_sec FROM tracklist WHERE album_id=? ORDER BY track_number", (album_id,))
        for num, title, dur in cur.fetchall():
            minutes = dur // 60
            seconds = dur % 60
            tree.insert('', 'end', values=(num, title, f"{minutes}:{seconds:02d}"))

    def on_filter(self, _=None):
        self.update_results()

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (_, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
