import tkinter as tk
from tkinter import ttk, messagebox
import importlib, pkgutil, re
import analytics
from analytics.analytics_base import AnalyticsBase

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
    """
    Analytics tab with dynamic module discovery and visualization.
    """
    def __init__(self, app, notebook):
        self.app = app
        self.root = app.root
        self.notebook = notebook
        self.analysis_type = tk.StringVar()
        self.filter_type = tk.StringVar(value='all')
        self.filter_value = tk.StringVar()
        self.chart_frame = None

    def setup_analytics_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Analytics")

        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Controls
        self._setup_controls(container)

        # Chart box below controls
        chart_box = ttk.LabelFrame(container, text="Chart")
        chart_box.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.chart_frame = ttk.Frame(chart_box)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self.apply_filters_and_draw()

    def _setup_controls(self, parent):
        control_frame = ttk.LabelFrame(parent, text="Analytics Options")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Filter by:").pack(side=tk.LEFT, padx=5)
        for txt, val in [("All Albums", "all"), ("Genre", "genre"),
                         ("Artist", "artist"), ("Decade", "decade")]:
            ttk.Radiobutton(control_frame, text=txt,
                            variable=self.filter_type, value=val,
                            command=self._update_filter_values).pack(side=tk.LEFT, padx=5)

        self.filter_combo = ttk.Combobox(control_frame, textvariable=self.filter_value,
                                         state='disabled', width=20)
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters_and_draw())

        ttk.Label(control_frame, text="Analysis:").pack(side=tk.LEFT, padx=15)
        sorted_names = sorted(ANALYTICS_CLASSES.keys())
        default = sorted_names[0] if sorted_names else ''
        self.analysis_type.set(default)
        self.analysis_combo = ttk.Combobox(control_frame, textvariable=self.analysis_type,
                                           values=sorted_names, state='readonly', width=20)
        self.analysis_combo.pack(side=tk.LEFT, padx=5)
        self.analysis_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters_and_draw())

        self._update_filter_values()

    def _update_filter_values(self):
        cur = self.app.database.conn.cursor()
        f = self.filter_type.get()
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
                gs.update(p.strip() for p in (g or '').split(','))
            opts = sorted(gs)
        elif f == 'decade':
            cur.execute("SELECT Release_Date FROM albums")
            ds = set()
            for (d,) in cur.fetchall():
                m = re.search(r"(\d{4})", str(d))
                if m:
                    ds.add(f"{int(m.group(1))//10*10}s")
            opts = sorted(ds)
        if 'All' not in opts:
            opts.insert(0, 'All')
        self.filter_combo['values'] = opts
        self.filter_combo.config(state='readonly' if opts else 'disabled')
        self.filter_value.set(opts[0] if opts else '')

        if self.chart_frame:
            self.apply_filters_and_draw()

    def apply_filters_and_draw(self):
        # clear chart area
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        kwargs = {}
        v = self.filter_value.get()
        if v != 'All':
            kwargs[self.filter_type.get()] = v

        analysis = self.analysis_type.get()
        cls = ANALYTICS_CLASSES.get(analysis)
        if not cls:
            ttk.Label(self.chart_frame, text=f"Analysis '{analysis}' not found.",
                      anchor='center').pack(expand=True)
            return

        chart = cls(self.app.database.db_name, title=analysis)
        chart.render(self.chart_frame, **kwargs)