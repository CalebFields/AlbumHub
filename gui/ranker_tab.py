# gui/ranker_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
import base64
import io
import re
import math
from PIL import Image, ImageTk

class RankerTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        self._photo_refs = []        # keep PhotoImage refs alive
        self.bold_font = Font(self.root, weight="bold")
        self.start_button = None
        self.save_button = None

        # merge‐sort state
        self.sort_gen = None
        self.current_match = None
        self.comparisons_done = 0
        self.total_comparisons = 0

    def setup_ranker_tab(self):
        self.ranker_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ranker_tab, text='Album Ranker')

        main = ttk.Frame(self.ranker_tab)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.setup_ranker_controls(main)
        self.setup_filter_controls(main)
        self.setup_comparison_interface(main)

        self.comparison_frame.pack_forget()
        self.reset_ranking_state()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def setup_ranker_controls(self, parent):
        ctrl = ttk.Frame(parent)
        ctrl.pack(fill=tk.X, pady=(0,20))
        self.start_button = ttk.Button(ctrl, text="Start Tournament", command=self.start_ranking_game)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(ctrl, text="Save Results",
                                      command=self.save_ranking_results,
                                      state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

    def setup_filter_controls(self, parent):
        frm = ttk.LabelFrame(parent, text="Ranking Filters")
        frm.pack(fill=tk.X, pady=(0,20))

        ttk.Label(frm, text="Rank by:").pack(side=tk.LEFT, padx=5)
        self.filter_type = tk.StringVar(value='all')
        for txt, val in [("All Albums","all"), ("Genre","genre"),
                         ("Artist","artist"), ("Decade","decade")]:
            ttk.Radiobutton(frm, text=txt, variable=self.filter_type,
                            value=val, command=self.update_filter_combo).pack(side=tk.LEFT, padx=5)

        self.filter_value = tk.StringVar()
        self.filter_combo = ttk.Combobox(frm, textvariable=self.filter_value,
                                         state='disabled', width=20)
        self.filter_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(frm, text="Apply Filter", command=self.apply_ranking_filter)\
            .pack(side=tk.LEFT, padx=5)

        self.update_filter_combo()

    def setup_comparison_interface(self, parent):
        self.comparison_frame = ttk.Frame(parent)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0,20))
        self.comparison_frame.columnconfigure((0,1), weight=1)
        self.comparison_frame.rowconfigure(0, weight=3)
        self.comparison_frame.rowconfigure(1, weight=1)
        self.comparison_frame.rowconfigure(2, weight=0)

        # Left album
        self.album1_btn = ttk.Button(self.comparison_frame,
                                     command=lambda: self.record_choice('L'))
        self.album1_btn.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        self.album1_info = self._make_info_text(self.comparison_frame)
        self.album1_info.grid(row=1, column=0, sticky='nsew', padx=10)

        # Right album
        self.album2_btn = ttk.Button(self.comparison_frame,
                                     command=lambda: self.record_choice('R'))
        self.album2_btn.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        self.album2_info = self._make_info_text(self.comparison_frame)
        self.album2_info.grid(row=1, column=1, sticky='nsew', padx=10)

        # Progress bar
        prog = ttk.Frame(self.comparison_frame)
        prog.grid(row=2, column=0, columnspan=2, sticky='ew', padx=10)
        self.progress_var = tk.StringVar(value='Ready')
        ttk.Label(prog, textvariable=self.progress_var).pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(prog, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _make_info_text(self, parent):
        dark_bg = self.root.cget('bg')
        style = ttk.Style()
        fg = style.lookup('TLabel','foreground',default='white')
        txt = tk.Text(parent, wrap='word', height=4,
                      bd=0, relief='flat', bg=dark_bg, fg=fg)
        txt.tag_configure('artist', foreground='#81a1c1', font=self.bold_font)
        txt.tag_configure('title',  foreground='#eceff4')
        txt.tag_configure('rating', foreground='#a3be8c')
        txt.config(state='disabled')
        return txt

    def reset_ranking_state(self):
        self.start_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)
        self.progress_var.set('Ready')
        self.progress_bar['value'] = 0
        self._photo_refs.clear()
        self.sort_gen = None
        self.current_match = None
        self.comparisons_done = 0
        self.total_comparisons = 0

    def update_filter_combo(self):
        cur = self.app.database.conn.cursor()
        f = self.filter_type.get()
        opts = ['All'] if f == 'all' else []
        if f == 'artist':
            cur.execute("SELECT DISTINCT Artist FROM albums")
            opts = sorted(r[0] for r in cur.fetchall() if r[0])
        elif f == 'genre':
            cur.execute("SELECT Genres FROM albums")
            gs = set()
            for (g,) in cur.fetchall():
                gs.update(p.strip() for p in (g or '').split(','))
            opts = sorted(gs)
        elif f == 'decade':
            cur.execute("SELECT Release_Date FROM albums")
            ds = {f"{int(m.group(1))//10*10}s"
                  for (d,) in cur.fetchall()
                  if (m := re.search(r"(\d{4})", str(d)))}
            opts = sorted(ds)

        self.filter_combo['values'] = opts
        self.filter_combo.config(state='readonly' if opts else 'disabled')
        self.filter_value.set(opts[0] if opts else '')

    def apply_ranking_filter(self):
        self.reset_ranking_state()
        messagebox.showinfo("Filter Applied",
                            f"{self.filter_type.get()} = {self.filter_value.get()}")

    def start_ranking_game(self):
        self.reset_ranking_state()
        self.start_button.config(state=tk.DISABLED)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0,20))

        cur = self.app.database.conn.cursor()
        ft, fv = self.filter_type.get(), self.filter_value.get()
        clause, params = [], []
        if ft == 'artist' and fv != 'All':
            clause.append("Artist=?"); params.append(fv)
        if ft == 'genre' and fv != 'All':
            clause.append("Genres LIKE ?"); params.append(f"%{fv}%")
        if ft == 'decade' and fv != 'All':
            sd, ed = int(fv[:-1]), int(fv[:-1]) + 9
            clause.append("CAST(substr(Release_Date,1,4) AS INT) BETWEEN ? AND ?")
            params += [sd, ed]

        sql = "SELECT DiscogsID FROM albums"
        if clause:
            sql += " WHERE " + " AND ".join(clause)
        rows = cur.execute(sql, params).fetchall()
        if not rows:
            return messagebox.showwarning("No Albums", "No albums found")

        ids = [r[0] for r in rows]
        n = len(ids)
        L = math.ceil(math.log2(n)) if n > 1 else 0
        # worst-case comparisons for mergesort = n·L - n + 1
        self.total_comparisons = n*L - n + 1 if n > 1 else 0
        self.progress_bar.config(maximum=self.total_comparisons)

        # initialize merge‐sort generator
        self.sort_gen = self._mergesort(ids)
        self._advance_match()

    def _advance_match(self, choice=None):
        try:
            if choice is None:
                left, right = next(self.sort_gen)
            else:
                left, right = self.sort_gen.send(choice)
            self.current_match = (left, right)
            self._display_pair(left, right)
        except StopIteration as e:
            self.sorted_final = e.value
            self.save_button.config(state=tk.NORMAL)
            self.display_ranking_results()

    def _mergesort(self, items):
        if len(items) <= 1:
            return items
        mid = len(items) // 2
        left = yield from self._mergesort(items[:mid])
        right = yield from self._mergesort(items[mid:])
        merged, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            choice = yield (left[i], right[j])
            if choice == 'L':
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
            self.comparisons_done += 1
            self.progress_bar['value'] = self.comparisons_done
            self.progress_var.set(f"{self.comparisons_done}/{self.total_comparisons} completed")
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged

    def record_choice(self, choice):
        self._advance_match(choice)

    def _display_pair(self, lid, rid):
        d1 = self._fetch_album(lid)
        d2 = self._fetch_album(rid)
        for btn, rec, info in [
            (self.album1_btn, d1, self.album1_info),
            (self.album2_btn, d2, self.album2_info)
        ]:
            img_data = rec.get('cover')
            if img_data:
                try:
                    img = Image.open(io.BytesIO(base64.b64decode(img_data)))
                    img.thumbnail((350,350))
                    tkimg = ImageTk.PhotoImage(img)
                    btn.config(image=tkimg)
                    self._photo_refs.append(tkimg)
                except:
                    btn.config(image='')
            else:
                btn.config(image='')

            info.config(state='normal')
            info.delete('1.0', tk.END)
            info.insert('end', rec['artist'] + '\n', 'artist')
            info.insert('end', rec['title'] + '\n',  'title')
            info.insert('end', f"Rating: {rec['rating']}", 'rating')
            info.config(state='disabled')

    def _fetch_album(self, aid):
        rec = self.app.database.conn.execute(
            "SELECT CoverArt, Artist, Title, Rating FROM albums WHERE DiscogsID=?",
            (aid,)
        ).fetchone()
        return {'cover': rec[0], 'artist': rec[1], 'title': rec[2], 'rating': rec[3]}

    def display_ranking_results(self):
        gui = self.app.gui
        style = ttk.Style()
        style.configure('Dark.Treeview',
                        background=gui.treeview_bg,
                        fieldbackground=gui.treeview_bg,
                        foreground=gui.light_fg)
        style.configure('Dark.Treeview.Heading',
                        background=gui.header_bg,
                        foreground=gui.light_fg)
        style.configure('Dark.TButton',
                        background=gui.button_bg,
                        foreground=gui.button_fg)

        win = tk.Toplevel(self.root)
        win.title("Your Tournament Rankings")
        win.configure(bg=gui.dark_bg)

        tv = ttk.Treeview(win, columns=('Album',), show='headings',
                          style='Dark.Treeview')
        tv.heading('Album', text='Album')
        tv.pack(fill=tk.BOTH, expand=True)

        for idx, aid in enumerate(self.sorted_final, 1):
            rec = self._fetch_album(aid)
            tv.insert('', 'end',
                      values=(f"{idx}. {rec['artist']} - {rec['title']}",))

        ttk.Button(win, text="Close", command=win.destroy,
                   style='Dark.TButton').pack(pady=10)

    def save_ranking_results(self):
        # TODO: implement CSV export for self.sorted_final
        pass

    def on_tab_changed(self, event):
        cur = event.widget.nametowidget(event.widget.select())
        if cur is getattr(self, 'ranker_tab', None):
            self.reset_ranking_state()
