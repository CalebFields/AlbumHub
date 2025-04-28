import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import importlib, pkgutil, re, os
import analytics
from analytics.analytics_base import AnalyticsBase
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from export.exporters import export_chart_and_insights

# Dynamically discover AnalyticsBase subclasses
ANALYTICS_CLASSES = {}
for finder, module_name, is_pkg in pkgutil.iter_modules(analytics.__path__, analytics.__name__ + "."):
    if module_name.endswith("analytics_base"):
        continue
    module = importlib.import_module(module_name)
    for attr in dir(module):
        cls = getattr(module, attr)
        if isinstance(cls, type) and issubclass(cls, AnalyticsBase) and cls is not AnalyticsBase:
            ANALYTICS_CLASSES[cls.__name__] = cls

class AnalyticsTab:
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        self.analysis_type = tk.StringVar()
        self.filter_type = tk.StringVar(value='all')
        self.filter_value = tk.StringVar()
        self.current_analysis = None
        self.chart_frame = None
        self.canvas = None
        self.canvas_window = None

    def setup_analytics_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Analytics")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        container = ttk.Frame(frame)
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._setup_controls(container)

        chart_box = ttk.LabelFrame(container, text="Chart & Insights")
        chart_box.grid(row=1, column=0, sticky='nsew', pady=(10, 0))
        chart_box.grid_rowconfigure(0, weight=1)
        chart_box.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(chart_box)
        v_scroll = ttk.Scrollbar(chart_box, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(chart_box, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        self.canvas.grid(row=0, column=0, sticky='nsew')

        scroll_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        scroll_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.chart_frame = scroll_frame

        export_btn = ttk.Button(chart_box, text="Export", command=self.on_export_clicked)
        export_btn.grid(row=2, column=0, padx=5, pady=5, sticky='e')

    def _setup_controls(self, parent):
        control_frame = ttk.LabelFrame(parent, text="Analytics Options")
        control_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        ttk.Label(control_frame, text="Filter by:").pack(side=tk.LEFT, padx=5)
        for txt, val in [("All Albums", "all"), ("Genre", "genre"), ("Artist", "artist"), ("Decade", "decade")]:
            ttk.Radiobutton(
                control_frame, text=txt, variable=self.filter_type, value=val,
                command=self._update_filter_values
            ).pack(side=tk.LEFT, padx=5)

        self.filter_combo = ttk.Combobox(
            control_frame, textvariable=self.filter_value,
            state='disabled', width=20
        )
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters_and_draw())

        ttk.Label(control_frame, text="Analysis:").pack(side=tk.LEFT, padx=15)
        names = sorted(ANALYTICS_CLASSES.keys())
        self.analysis_type.set(names[0] if names else '')
        self.analysis_combo = ttk.Combobox(
            control_frame, textvariable=self.analysis_type,
            values=names, state='readonly', width=20
        )
        self.analysis_combo.pack(side=tk.LEFT, padx=5)
        self.analysis_combo.bind('<<ComboboxSelected>>', lambda e: self.safe_apply_filters_and_draw())

    def _update_filter_values(self):
        cur = self.app.database.conn.cursor()
        f = self.filter_type.get()
        opts = []
        if f == 'all':
            opts = ['All']
        elif f == 'artist':
            cur.execute("SELECT Artist FROM albums")
            artists = set()
            for (a,) in cur.fetchall():
                if a:
                    for part in re.split(r"\s*(?:,|&|and)\s*", a):
                        if part.strip():
                            artists.add(part.strip())
            opts = ['All'] + sorted(artists)
        elif f == 'genre':
            cur.execute("SELECT Genres FROM albums")
            genres = set()
            for (g,) in cur.fetchall():
                if g:
                    for part in re.split(r"\s*(?:,|&|and)\s*", g):
                        if part.strip():
                            genres.add(part.strip())
            opts = ['All'] + sorted(genres)
        elif f == 'decade':
            cur.execute("SELECT Release_Date FROM albums")
            decades = set()
            for (d,) in cur.fetchall():
                m = re.search(r"(\d{4})", str(d))
                if m:
                    decades.add(f"{int(m.group(1))//10*10}s")
            opts = ['All'] + sorted(decades)
        self.filter_combo['values'] = opts
        self.filter_combo.config(state='readonly' if opts else 'disabled')
        self.filter_value.set(opts[0] if opts else '')

    def safe_apply_filters_and_draw(self):
        try:
            self.apply_filters_and_draw()
        except Exception:
            self._update_filter_values()

    def apply_filters_and_draw(self):
        if not self.chart_frame:
            return
        analysis = self.analysis_type.get()
        if not analysis:
            return
        self.show_loading_message("Working...")
        self.root.after(100, self._draw_chart)

    def _draw_chart(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        v = self.filter_value.get()
        kwargs = {} if v == 'All' else {self.filter_type.get(): v}

        cls = ANALYTICS_CLASSES.get(self.analysis_type.get())
        if not cls:
            ttk.Label(self.chart_frame, text="Analysis not found", anchor='center').pack(fill='both', expand=True)
            return

        self.current_analysis = cls(self.app.database.db_name, title=self.analysis_type.get())
        self.current_analysis.render(self.chart_frame, **kwargs)

        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def on_export_clicked(self):
        if not self.current_analysis:
            messagebox.showwarning("No Chart", "No chart available to export.")
            return
    
        export_dir = filedialog.askdirectory(title="Select Export Directory")
        if not export_dir:
            return
    
        try:
            # Prepare current filters
            v = self.filter_value.get()
            kwargs = {} if v == 'All' else {self.filter_type.get(): v}
    
            # Use the analytics base export method
            base_path = self.current_analysis.export(export_dir, **kwargs)
    
            messagebox.showinfo(
                "Export Complete",
                f"Exported:\n{base_path}.png\n{base_path}.txt"
            )
    
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


    def show_loading_message(self, message="Working..."):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        ttk.Label(
            self.chart_frame,
            text=message,
            anchor='center',
            font=("Segoe UI", 14, "bold")
        ).pack(fill='both', expand=True)
