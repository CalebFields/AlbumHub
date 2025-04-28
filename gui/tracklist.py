import tkinter as tk
from tkinter import ttk

class TracklistWindow:
    def __init__(self, root, database):
        self.root = root
        self.database = database

    def open_tracklist_window(self, album_id):
        # Create a new top-level window for the tracklist
        win = tk.Toplevel(self.root)
        win.title("Tracklist")

        # Set window size and padding
        win.geometry("500x400")
        win.resizable(False, False)

        # Apply the same theme from the main GUI to the tracklist window
        dark_bg = "#2E2E2E"
        light_fg = "#FFFFFF"
        header_bg = "#3C3F41"
        treeview_bg = "#333333"

        # Styling for the treeview
        style = ttk.Style(win)
        style.configure("Treeview",
                        font=('Helvetica', 9),  # Smaller font size for rows
                        rowheight=25,  # Row height
                        background=treeview_bg,  # Dark background color for rows
                        foreground=light_fg,  # White text color
                        fieldbackground=treeview_bg
        )
        style.configure("Treeview.Heading",
                        font=('Helvetica', 10, 'bold'),  # Slightly smaller bold font for headings
                        background=header_bg,  # Header background color (dark)
                        foreground=light_fg,  # White text for headings
                        padding=(5, 2)  # Padding to make headers look cleaner
        )

        # Create a Treeview widget for displaying the tracklist
        tree = ttk.Treeview(win, columns=('#', 'Title', 'Duration'), show='headings', style="Treeview")
        tree.heading('#', text='No.', anchor='center')
        tree.heading('Title', text='Track Title', anchor='center')
        tree.heading('Duration', text='Duration (min:sec)', anchor='center')

        # Add zebra striping effect for rows
        tree.tag_configure('odd', background="#e2e2e2")  # Light grey for odd rows
        tree.tag_configure('even', background="#f9f9f9")  # White for even rows

        # Add vertical scrollbar
        sb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Query the database to get the track details
        cur = self.database.cursor()
        cur.execute("SELECT track_number, title, duration_sec FROM tracklist WHERE album_id=? ORDER BY track_number", (album_id,))

        # Insert rows into the Treeview with alternating row colors (zebra striping)
        for idx, (num, title, dur) in enumerate(cur.fetchall()):
            # Convert duration from seconds to minutes:seconds
            minutes = dur // 60
            seconds = dur % 60
            formatted_duration = f"{minutes}:{seconds:02d}"

            tag = 'odd' if idx % 2 == 0 else 'even'  # Alternate row colors
            tree.insert('', 'end', values=(num, title, formatted_duration), tags=(tag,))

        # Update the display after inserting items
        win.update_idletasks()  # Forces the window to refresh and apply styles

    def show_tracks(self, album_id):
        # Placeholder method for additional functionality
        pass
