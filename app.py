import os
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from pages.admin_page import AdminPageMixin
from pages.login_page import LoginPageMixin
from pages.student_page import StudentPageMixin
from ui_theme import ACCENT, BACKGROUND, MUTED, PANEL, PANEL_LIGHT, TEXT


class ELibraryApp(
    tk.Tk,
    LoginPageMixin,
    StudentPageMixin,
    AdminPageMixin,
):
    def __init__(self):
        super().__init__()
        self.title("Ruang Baca — Perpustakaan Digital")
        self.geometry("1180x780")
        self.minsize(760, 600)
        self.configure(bg=BACKGROUND)
        self.current_user_id = None
        self.current_user_name = ""
        self.current_user_role = ""
        self.search_var = tk.StringVar()
        self.active_filter = "Semua Buku"

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Library.Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=32,
            borderwidth=0,
        )
        style.configure(
            "Library.Treeview.Heading",
            background=PANEL_LIGHT,
            foreground=TEXT,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map(
            "Library.Treeview",
            background=[("selected", "#315e57")],
            foreground=[("selected", TEXT)],
        )
        self.container = tk.Frame(self, bg=BACKGROUND)
        self.container.pack(fill="both", expand=True)
        self.show_login_screen()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def make_button(self, parent, text, command, *, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT if primary else PANEL_LIGHT,
            fg="#10201d" if primary else TEXT,
            activebackground="#76d9b8" if primary else "#303b4b",
            activeforeground=TEXT if not primary else "#10201d",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )

    def build_header(self, title, subtitle):
        header = tk.Frame(self.container, bg=BACKGROUND)
        header.pack(fill="x", padx=34, pady=(22, 12))
        brand = tk.Frame(header, bg=BACKGROUND)
        brand.pack(side="left")
        tk.Label(
            brand, text=title, bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand, text=subtitle, bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))
        self.make_button(header, "Keluar", self.show_login_screen).pack(side="right")
        tk.Label(
            header, text=self.current_user_name, bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="right", padx=16)
        return header

    def open_book(self, file_path, parent):
        if not file_path:
            messagebox.showerror("File tidak tersedia", "Buku ini belum memiliki file.", parent=parent)
            return
        path = Path(file_path)
        if not path.is_file():
            messagebox.showerror(
                "File tidak ditemukan", f"File buku tidak ditemukan:\n{path}", parent=parent
            )
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                webbrowser.open(path.resolve().as_uri())
        except OSError as error:
            messagebox.showerror("Tidak dapat membuka buku", str(error), parent=parent)
