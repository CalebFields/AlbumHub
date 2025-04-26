# gui/ranker_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
import base64
import io
import re
from PIL import Image, ImageTk

class RankerTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        # Keep PhotoImage refs alive
        self._photo_refs = []

    def setup_ranker_tab(self):
        try:
            self.ranker_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.ranker_tab, text='Album Ranker')

            main = ttk.Frame(self.ranker_tab, style='TFrame')
            main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            self.setup_ranker_controls(main)
            self.setup_filter_controls(main)
            self.setup_comparison_interface(main)
            self.setup_progress_display(main)

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
                                         state='disabled', width=20, style='TCombobox')
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(frm, text="Apply Filter", command=self.apply_ranking_filter).pack(side=tk.LEFT, padx=5)
        self.update_filter_combo()

    def setup_comparison_interface(self, parent):
        frame = ttk.LabelFrame(parent, text="Which album do you prefer?", style='TFrame')
        frame.pack(fill=tk.BOTH, expand=True, pady=(0,20))
        self.album1_image = ttk.Label(frame)
        self.album1_image.pack(side=tk.LEFT, expand=True, padx=10, pady=10)
        self.album1_info = ttk.Label(frame, text="Album 1 info will appear here",
                                     style='TLabel', wraplength=300)
        self.album1_info.pack(side=tk.LEFT, padx=10)
        self.choose_album1 = ttk.Button(frame, text="Choose Album 1",
                                        command=lambda: self.record_choice('L'), state=tk.DISABLED)
        self.choose_album1.pack(side=tk.LEFT, padx=10)
        self.album2_image = ttk.Label(frame)
        self.album2_image.pack(side=tk.RIGHT, expand=True, padx=10, pady=10)
        self.album2_info = ttk.Label(frame, text="Album 2 info will appear here",
                                     style='TLabel', wraplength=300)
        self.album2_info.pack(side=tk.RIGHT, padx=10)
        self.choose_album2 = ttk.Button(frame, text="Choose Album 2",
                                        command=lambda: self.record_choice('R'), state=tk.DISABLED)
        self.choose_album2.pack(side=tk.RIGHT, padx=10)

    def setup_progress_display(self, parent):
        frame = ttk.Frame(parent, style='TFrame')
        frame.pack(fill=tk.X, pady=(0,10))
        self.progress_var = tk.StringVar(value='Ready')
        ttk.Label(frame, textvariable=self.progress_var, style='TLabel').pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def reset_ranking_state(self):
        self.start_button['state'] = tk.NORMAL
        self.save_button['state'] = tk.DISABLED
        self.choose_album1['state'] = tk.DISABLED
        self.choose_album2['state'] = tk.DISABLED
        self.album1_image.config(image='')
        self.album2_image.config(image='')
        self.album1_info.config(text='Album 1 info will appear here')
        self.album2_info.config(text='Album 2 info will appear here')
        self.progress_var.set('Ready')
        self.progress_bar['value'] = 0

    def update_filter_combo(self):
        f = self.filter_type.get()
        cur = self.app.database.conn.cursor()
        opts = []
        if f == 'all':
            opts = ['All']
        elif f == 'artist':
            cur.execute("SELECT DISTINCT Artist FROM albums")
            opts = sorted(r[0] for r in cur.fetchall() if r[0])
        elif f == 'genre':
            cur.execute("SELECT Genres FROM albums")
            gs = set()
            for (g,) in cur.fetchall():
                if g:
                    for p in g.split(','): gs.add(p.strip())
            opts = sorted(gs)
        elif f == 'decade':
            cur.execute("SELECT Release_Date FROM albums")
            ds = set()
            for (d,) in cur.fetchall():
                m = re.search(r"(\d{4})", str(d or ''))
                if m: ds.add(f"{int(m.group(1))//10*10}s")
            opts = sorted(ds)
        self.filter_combo['values'] = opts
        self.filter_combo.config(state='readonly' if opts else 'disabled')
        self.filter_value.set(opts[0] if opts else '')

    def apply_ranking_filter(self):
        self.reset_ranking_state()
        messagebox.showinfo("Filter", f"{self.filter_type.get()} = {self.filter_value.get()}")

    def start_ranking_game(self):
        self.reset_ranking_state()
        # fetch
        cur = self.app.database.conn.cursor()
        where, prm = [], []
        ft, fv = self.filter_type.get(), self.filter_value.get()
        if ft=='artist' and fv!='All': where.append("Artist=?"); prm.append(fv)
        if ft=='genre'  and fv!='All': where.append("Genres LIKE ?"); prm.append(f"%{fv}%")
        if ft=='decade' and fv!='All':
            sd=int(fv[:-1]); ed=sd+9
            where.append("CAST(substr(Release_Date,1,4)AS INT) BETWEEN ? AND ?"); prm.extend([sd,ed])
        sql="SELECT DiscogsID,CoverArt,Artist,Title FROM albums"
        if where: sql+=" WHERE "+" AND ".join(where)
        rows=cur.execute(sql,prm).fetchall()
        if not rows: messagebox.showwarning("No Albums","No albums found"); return
        # init
        self.album_graph={rid:{'cover':cov,'artist':art,'title':tit} for rid,cov,art,tit in rows}
        ids=[rid for rid,_,_,_ in rows]
        self.merge_queue=[[i] for i in ids]
        self.next_merge()
        self.show_next_pair()

    def next_merge(self):
        if len(self.merge_queue)>1:
            self.left=self.merge_queue.pop(0)
            self.right=self.merge_queue.pop(0)
            self.merged=[]
            self.li=0; self.ri=0
        else:
            self.sorted_final=self.merge_queue[0]

    def show_next_pair(self):
        if hasattr(self,'sorted_final'):
            self.save_button['state']=tk.NORMAL
            self.display_ranking_results(); return
        # compare left[li] vs right[ri]
        lid=self.left[self.li]; rid=self.right[self.ri]
        for data,widget,info in [
            (self.album_graph[lid], self.album1_image, self.album1_info),
            (self.album_graph[rid], self.album2_image, self.album2_info)
        ]:
            widget.config(image='')
            if data.get('cover'):
                try:
                    img=Image.open(io.BytesIO(base64.b64decode(data['cover'])))
                    img.thumbnail((150,150))
                    tkimg=ImageTk.PhotoImage(img); widget.config(image=tkimg)
                    self._photo_refs.append(tkimg)
                except: pass
            info.config(text=f"{data['artist']} - {data['title']}")
        self.choose_album1['state']=tk.NORMAL; self.choose_album2['state']=tk.NORMAL

    def record_choice(self, choice):
        if choice=='L':
            self.merged.append(self.left[self.li]); self.li+=1
        else:
            self.merged.append(self.right[self.ri]); self.ri+=1
        # exhausted one side?
        if self.li==len(self.left) or self.ri==len(self.right):
            self.merged.extend(self.left[self.li:]); self.merged.extend(self.right[self.ri:])
            self.merge_queue.append(self.merged)
            self.next_merge()
        self.choose_album1['state']=tk.DISABLED; self.choose_album2['state']=tk.DISABLED
        self.show_next_pair()

    def display_ranking_results(self):
        win=tk.Toplevel(self.root); win.title("Your Rankings")
        tv=ttk.Treeview(win,columns=('Album',),show='headings');
        tv.heading('Album',text='Album'); tv.pack(fill=tk.BOTH,expand=True)
        for idx,rid in enumerate(self.sorted_final,1):
            a=self.album_graph[rid]; name=f"{idx}. {a['artist']} - {a['title']}"
            tv.insert('', 'end', values=(name,))
        ttk.Button(win,text="Close",command=win.destroy).pack(pady=10)

    def save_ranking_results(self):
        # optional CSV export
        pass

    def on_tab_changed(self,event):
        cur=event.widget.nametowidget(event.widget.select())
        if cur is self.ranker_tab: self.reset_ranking_state()