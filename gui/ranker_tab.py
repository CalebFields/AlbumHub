import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
import base64
import io
import re
import random
from PIL import Image, ImageTk

class RankerTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        self._photo_refs = []  # keep PhotoImage refs alive
        self.bold_font = Font(self.root, weight="bold")

    def setup_ranker_tab(self):
        try:
            self.ranker_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.ranker_tab, text='Album Ranker')

            main = ttk.Frame(self.ranker_tab, style='TFrame')
            main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            self.setup_ranker_controls(main)
            self.setup_filter_controls(main)
            self.setup_comparison_interface(main)

            # hide comparison (and progress) until start
            self.comparison_frame.pack_forget()

            self.reset_ranking_state()
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        except Exception as e:
            messagebox.showerror("Init Error", f"Ranking tab init failed: {e}")

    def setup_ranker_controls(self, parent):
        frame = ttk.Frame(parent, style='TFrame')
        frame.pack(fill=tk.X, pady=(0,20))
        self.start_button = ttk.Button(frame, text="Start Ranking", command=self.start_ranking_game)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(frame, text="Save Results", command=self.save_ranking_results, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

    def setup_filter_controls(self, parent):
        frm = ttk.LabelFrame(parent, text="Ranking Filters", style='TFrame')
        frm.pack(fill=tk.X, pady=(0,20))
        ttk.Label(frm, text="Rank by:", style='TLabel').pack(side=tk.LEFT, padx=5)
        self.filter_type = tk.StringVar(value='all')
        for text,val in [("All Albums","all"),("Genre","genre"),
                         ("Artist","artist"),("Decade","decade")]:
            ttk.Radiobutton(frm, text=text, variable=self.filter_type, value=val,
                            command=self.update_filter_combo).pack(side=tk.LEFT, padx=5)
        self.filter_value = tk.StringVar()
        self.filter_combo = ttk.Combobox(frm, textvariable=self.filter_value,
                                         state='disabled', width=20)
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(frm, text="Apply Filter", command=self.apply_ranking_filter).pack(side=tk.LEFT, padx=5)
        self.update_filter_combo()

    def setup_comparison_interface(self, parent):
        # Comparison + progress area: hidden until start
        self.comparison_frame = ttk.Frame(parent, style='TFrame')
        self.comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0,20))
        # allow both columns/rows to expand
        self.comparison_frame.columnconfigure((0,1), weight=1)
        self.comparison_frame.rowconfigure((0,), weight=3)
        self.comparison_frame.rowconfigure((1,), weight=1)
        self.comparison_frame.rowconfigure((2,), weight=0)

        # Left album button + image
        self.album1_btn = ttk.Button(self.comparison_frame, command=lambda: self.record_choice('L'))
        self.album1_btn.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        # Left album text area
        root_bg = self.root.cget('bg')
        self.album1_info = tk.Text(
            self.comparison_frame,
            wrap='word',
            height=4,
            bd=0,
            bg=root_bg,
            highlightthickness=0,
            relief='flat'
        )
        self.album1_info.grid(row=1, column=0, pady=(0,5), padx=10, sticky='nsew')
        # configure tag colors: artist, title, rating
        self.album1_info.tag_configure('artist', foreground='#81a1c1', font=self.bold_font)
        self.album1_info.tag_configure('title',  foreground='#eceff4')
        self.album1_info.tag_configure('rating', foreground='#a3be8c')
        self.album1_info.config(state='disabled')

        # Right album button + image
        self.album2_btn = ttk.Button(self.comparison_frame, command=lambda: self.record_choice('R'))
        self.album2_btn.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        # Right album text area
        self.album2_info = tk.Text(
            self.comparison_frame,
            wrap='word',
            height=4,
            bd=0,
            bg=root_bg,
            highlightthickness=0,
            relief='flat'
        )
        self.album2_info.grid(row=1, column=1, pady=(0,5), padx=10, sticky='nsew')
        # same tag configuration
        self.album2_info.tag_configure('artist', foreground='#81a1c1', font=self.bold_font)
        self.album2_info.tag_configure('title',  foreground='#eceff4')
        self.album2_info.tag_configure('rating', foreground='#a3be8c')
        self.album2_info.config(state='disabled')

        # Progress bar under comparisons
        prog_frame = ttk.Frame(self.comparison_frame)
        prog_frame.grid(row=2, column=0, columnspan=2, pady=(10,0), sticky='ew', padx=10)
        self.progress_var = tk.StringVar(value='Ready')
        ttk.Label(prog_frame, textvariable=self.progress_var).pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def reset_ranking_state(self):
        self.start_button['state'] = tk.NORMAL
        self.save_button['state'] = tk.DISABLED
        self.progress_var.set('Ready')
        self.progress_bar['value'] = 0
        self._photo_refs.clear()

    def update_filter_combo(self):
        f = self.filter_type.get()
        cur = self.app.database.conn.cursor()
        opts = []
        if f == 'all': opts = ['All']
        elif f == 'artist':
            cur.execute("SELECT DISTINCT Artist FROM albums")
            opts = sorted(r[0] for r in cur.fetchall() if r[0])
        elif f == 'genre':
            cur.execute("SELECT Genres FROM albums")
            gs = set()
            for (g,) in cur.fetchall():
                for p in (g or '').split(','): gs.add(p.strip())
            opts = sorted(gs)
        elif f == 'decade':
            cur.execute("SELECT Release_Date FROM albums")
            ds = {f"{int(m.group(1))//10*10}s" for (d,) in cur.fetchall() if (m:=re.search(r"(\d{4})", str(d)))}
            opts = sorted(ds)
        self.filter_combo['values'] = opts
        self.filter_combo.config(state='readonly' if opts else 'disabled')
        self.filter_value.set(opts[0] if opts else '')

    def apply_ranking_filter(self):
        self.reset_ranking_state()
        messagebox.showinfo("Filter", f"{self.filter_type.get()} = {self.filter_value.get()}")

    def start_ranking_game(self):
        self.reset_ranking_state()
        self.start_button['state'] = tk.DISABLED
        self.comparison_frame.pack(fill=tk.BOTH, expand=True, pady=(0,20))

        # fetch/filter
        cur = self.app.database.conn.cursor()
        where, prm = [], []
        ft, fv = self.filter_type.get(), self.filter_value.get()
        if ft=='artist' and fv!='All': where.append("Artist=?"); prm.append(fv)
        if ft=='genre'  and fv!='All': where.append("Genres LIKE ?"); prm.append(f"%{fv}%")
        if ft=='decade' and fv!='All':
            sd=int(fv[:-1]); ed=sd+9
            where.append("CAST(substr(Release_Date,1,4)AS INT) BETWEEN ? AND ?"); prm.extend([sd,ed])
        sql="SELECT DiscogsID,CoverArt,Artist,Title,Rating FROM albums"
        if where: sql += " WHERE " + " AND ".join(where)
        rows = cur.execute(sql, prm).fetchall()
        if not rows:
            messagebox.showwarning("No Albums","No albums found")
            return
        try: rows = sorted(rows, key=lambda r: float(r[4] or 0), reverse=True)
        except: pass
        ids = [r[0] for r in rows]
        random.shuffle(ids)

        self.total_comparisons = len(ids) - 1
        self.comparisons_done = 0
        self.progress_bar.config(maximum=self.total_comparisons)
        self.progress_var.set(f"0/{self.total_comparisons} completed")

        self.album_graph = {r[0]: {'cover':r[1],'artist':r[2],'title':r[3],'rating':r[4]} for r in rows}
        self.merge_queue = [[i] for i in ids]
        self.next_merge()
        self.show_next_pair()

    def next_merge(self):
        if len(self.merge_queue) > 1:
            self.left = self.merge_queue.pop(0)
            self.right = self.merge_queue.pop(0)
            self.merged = []
            self.li = self.ri = 0
        else:
            self.sorted_final = self.merge_queue[0]

    def show_next_pair(self):
        if hasattr(self, 'sorted_final'):
            self.save_button['state'] = tk.NORMAL
            self.display_ranking_results()
            return

        lid, rid = self.left[self.li], self.right[self.ri]
        for btn, info, idx in [
            (self.album1_btn, self.album1_info, lid),
            (self.album2_btn, self.album2_info, rid)
        ]:
            data = self.album_graph[idx]

            # update image on button
            if img_data := data.get('cover'):
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

            # update text with colored tags
            info.config(state='normal')
            info.delete('1.0', tk.END)
            info.insert('end', data['artist'] + '\n', 'artist')
            info.insert('end', data['title'] + '\n', 'title')
            info.insert('end', f"Rating: {data['rating']}", 'rating')
            info.config(state='disabled')

        self.comparisons_done += 1
        self.progress_bar['value'] = self.comparisons_done
        self.progress_var.set(f"{self.comparisons_done}/{self.total_comparisons} completed")

    def record_choice(self, choice):
        if choice == 'L': self.merged.append(self.left[self.li]); self.li += 1
        else:             self.merged.append(self.right[self.ri]); self.ri += 1
        if self.li == len(self.left) or self.ri == len(self.right):
            self.merged.extend(self.left[self.li:]); self.merged.extend(self.right[self.ri:])
            self.merge_queue.append(self.merged)
            self.next_merge()
        self.show_next_pair()

    def display_ranking_results(self):
        win = tk.Toplevel(self.root); win.title("Your Rankings")
        tv = ttk.Treeview(win, columns=('Album',), show='headings'); tv.heading('Album', text='Album'); tv.pack(fill=tk.BOTH, expand=True)
        for idx, rid in enumerate(self.sorted_final,1):
            a=self.album_graph[rid]; name=f"{idx}. {a['artist']} - {a['title']}"
            tv.insert('', 'end', values=(name,))
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def save_ranking_results(self):
        # TODO: implement CSV export
        pass

    def on_tab_changed(self, event):
        cur = event.widget.nametowidget(event.widget.select())
        if cur is self.ranker_tab:
            self.reset_ranking_state()
