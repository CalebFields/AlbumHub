import tkinter as tk
from tkinter import ttk, messagebox

from gui.import_tab import ImportTab
from gui.browser_tab import BrowserTab
from gui.ranker_tab import RankerTab

class MainGUI:
    def __init__(self, app_controller, root):
        self.app = app_controller
        self.root = root
        self.root.title("AlbumHub")
        self.root.geometry("1200x800")

        self.setup_theme()
        self.setup_notebook()
        self.setup_tabs()

    def setup_theme(self):
        self.dark_bg = "#2E2E2E"
        self.light_fg = "#FFFFFF"
        self.button_bg = "#444444"
        self.button_fg = "#FFFFFF"
        self.header_bg = "#3C3F41"
        self.treeview_bg = "#333333"
        self.entry_bg = "#444444"
        self.select_bg = "#4A6984"
        self.select_fg = "#FFFFFF"

        self.root.configure(bg=self.dark_bg)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # reinforce global palette for any ttk widgets
        self.root.tk_setPalette(
            background=self.dark_bg,
            foreground=self.light_fg,
            activeBackground=self.dark_bg,
            activeForeground=self.light_fg
        )
        self.style.configure('.', background=self.dark_bg, foreground=self.light_fg)


        self.style.configure("Treeview", background=self.treeview_bg, foreground=self.light_fg, fieldbackground=self.treeview_bg)
        self.style.configure("Treeview.Heading", background=self.header_bg, foreground=self.light_fg)
        self.style.map('Treeview', background=[('selected', self.select_bg)], foreground=[('selected', self.select_fg)])
        self.style.configure('TLabel', background=self.dark_bg, foreground=self.light_fg)
        self.style.configure('TFrame', background=self.dark_bg)
        self.style.configure('TButton', background=self.button_bg, foreground=self.button_fg)
        self.style.map('TButton', background=[('active', self.select_bg)], foreground=[('active', self.select_fg)])
        self.style.configure('TCombobox', fieldbackground=self.entry_bg, background=self.dark_bg, foreground=self.light_fg)
        self.style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)], background=[('readonly', self.dark_bg)], foreground=[('readonly', self.light_fg)], selectbackground=[('readonly', self.select_bg)], selectforeground=[('readonly', self.select_fg)])
        self.style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.light_fg, insertcolor=self.light_fg)
        self.style.configure('TNotebook', background=self.dark_bg)
        self.style.configure('TNotebook.Tab', background=self.button_bg, foreground=self.light_fg)
        self.style.map('TNotebook.Tab', background=[('selected', self.select_bg)], foreground=[('selected', self.select_fg)])

    def setup_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

    def setup_tabs(self):
        self.import_tab = ImportTab(self.app, self.notebook)
        self.browser_tab = BrowserTab(self.app, self.notebook)
        self.ranker_tab = RankerTab(self.app, self.notebook)
        self.import_tab.setup_import_tab()
        self.browser_tab.setup_browser_tab()
        self.ranker_tab.setup_ranker_tab()

        # Bind to Notebook tab changes to refresh browser tab
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        selected_frame = event.widget.nametowidget(event.widget.select())
        if selected_frame is self.browser_tab.browser_tab:
            self.browser_tab.introspect_columns()
            self.browser_tab.load_filters()
            self.browser_tab.update_results()

    def update_status(self, message):
        try:
            self.import_tab.status_var.set(message)
        except Exception:
            print(f"[Status Update] {message}")

    def update_progress(self, current, total, message):
        if hasattr(self.import_tab, 'progress_bar'):
            progress_pct = int((current / total) * 100)
            self.import_tab.progress_bar['value'] = progress_pct
            self.import_tab.progress_var.set(message)

    def clear_progress(self):
        if hasattr(self.import_tab, 'progress_bar'):
            self.import_tab.progress_bar['value'] = 0
            self.import_tab.progress_var.set("Idle")

    def enable_controls(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        for child in self.import_tab.import_tab.winfo_children():
            if isinstance(child, ttk.Button):
                child['state'] = state

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def bind(self, sequence, handler):
        self.root.bind(sequence, handler)

    def update_database_view(self):
        self.browser_tab.update_results()
