import os
import webbrowser
from datetime import date, datetime, time, timedelta
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

import mysql.connector

from database import expire_overdue_loans
from pages.admin_page import AdminPageMixin
from pages.login_page import LoginPageMixin
from pages.student_page import StudentPageMixin
from ui_theme import (
    ACCENT,
    ACCENT_LIGHT,
    BACKGROUND,
    BORDER,
    HEADER_DARK,
    MUTED,
    PANEL,
    PANEL_LIGHT,
    TEXT,
)


class ELibraryApp(
    tk.Tk,
    LoginPageMixin,
    StudentPageMixin,
    AdminPageMixin,
):
    def __init__(self):
        super().__init__()
        self.title("ERAUTAMA — Perpustakaan Digital")
        self.geometry("1920x1080")
        self.minsize(760, 600)
        self.configure(bg=BACKGROUND)
        available_fonts = set(tkfont.families(self))
        self.font_body = "Calibri" if "Calibri" in available_fonts else self.font_body
        self.font_display = (
            "Bahnschrift" if "Bahnschrift" in available_fonts else self.font_body
        )
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
            rowheight=40,
            borderwidth=0,
            padding=(8, 3),
            relief="flat",
            font=(self.font_body, 10),
        )
        style.configure(
            "Library.Treeview.Heading",
            background=HEADER_DARK,
            foreground="#ffffff",
            font=(self.font_display, 10, "bold"),
            relief="flat",
        )
        style.configure(
            "Library.Vertical.TScrollbar",
            background=PANEL_LIGHT,
            troughcolor=BACKGROUND,
            bordercolor=BACKGROUND,
            arrowcolor=MUTED,
        )
        style.configure(
            "Library.Horizontal.TScrollbar",
            background=PANEL_LIGHT,
            troughcolor=BACKGROUND,
            bordercolor=BACKGROUND,
            arrowcolor=MUTED,
        )
        style.map(
            "Library.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "TCombobox",
            fieldbackground=PANEL_LIGHT,
            background=PANEL_LIGHT,
            foreground=TEXT,
            arrowcolor=ACCENT,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", PANEL_LIGHT)],
            foreground=[("readonly", TEXT)],
        )
        self.container = tk.Frame(self, bg=BACKGROUND)
        self.container.pack(fill="both", expand=True)
        self.show_login_screen()
        self.schedule_loan_expiration()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def schedule_loan_expiration(self, delay_ms=None):
        if delay_ms is None:
            next_midnight = datetime.combine(
                date.today() + timedelta(days=1), time.min
            )
            delay_ms = max(
                1000, int((next_midnight - datetime.now()).total_seconds() * 1000)
            )
        self.loan_expiration_after = self.after(
            delay_ms, self.expire_due_loans
        )

    def expire_due_loans(self):
        self.loan_expiration_after = None
        try:
            expired_count = expire_overdue_loans()
        except mysql.connector.Error as error:
            messagebox.showerror(
                "Pengembalian otomatis gagal",
                str(error),
                parent=self,
            )
            self.schedule_loan_expiration(60_000)
            return

        if expired_count and hasattr(self, "book_catalogue_data"):
            self.book_catalogue_data = None
            if (
                hasattr(self, "grid_frame")
                and self.grid_frame.winfo_exists()
            ):
                try:
                    self.render_book_grid()
                except mysql.connector.Error as error:
                    messagebox.showerror(
                        "Katalog tidak dapat diperbarui",
                        str(error),
                        parent=self,
                    )
        self.schedule_loan_expiration()

    def make_button(self, parent, text, command, *, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT if primary else PANEL,
            fg="#ffffff" if primary else TEXT,
            activebackground="#5669d1" if primary else ACCENT_LIGHT,
            activeforeground="#ffffff" if primary else TEXT,
            relief="flat",
            bd=0 if primary else 1,
            highlightthickness=0 if primary else 1,
            highlightbackground=BORDER,
            padx=13,
            pady=9,
            cursor="hand2",
            font=(self.font_body, 9, "bold"),
        )

    def build_header(self):
        header = tk.Frame(self.container, bg=HEADER_DARK, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, height=3).place(
            relx=0, rely=1, relwidth=1, anchor="sw"
        )
        brand = tk.Frame(header, bg=HEADER_DARK)
        brand.pack(side="left")
        tk.Label(
            brand, text="ERAUTAMA", bg=HEADER_DARK, fg="#ffffff",
            font=(self.font_display, 15, "bold"),
        ).pack(side="left", padx=(22, 10))
        tk.Label(
            brand, text="SISTEM INFORMASI PERPUSTAKAAN",
            bg=HEADER_DARK, fg="#d9defb",
            font=(self.font_body, 9, "bold"),
        ).pack(side="left")
        self.make_button(header, "Keluar", self.show_login_screen).pack(
            side="right", padx=(10, 18), pady=12
        )
        tk.Label(
            header, text=self.current_user_name, bg=HEADER_DARK, fg="#ffffff",
            font=(self.font_body, 10, "bold"),
        ).pack(side="right", padx=8)

        shell = tk.Frame(self.container, bg=BACKGROUND)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=PANEL, width=190)
        self.sidebar.pack(side="left", fill="y", padx=(14, 0), pady=14)
        self.sidebar.pack_propagate(False)
        tk.Label(
            self.sidebar, text="MENU", bg=PANEL, fg=MUTED,
            font=(self.font_display, 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(22, 12))
        self.sidebar_buttons = {}
        self.workspace = tk.Frame(shell, bg=BACKGROUND)
        self.workspace.pack(
            side="left", fill="both", expand=True, padx=16, pady=14
        )
        return self.workspace

    def add_sidebar_item(self, label, command, *, selected=False):
        button = tk.Button(
            self.sidebar,
            text=label,
            command=command,
            anchor="w",
            bg=ACCENT_LIGHT if selected else PANEL,
            fg=ACCENT if selected else TEXT,
            activebackground=ACCENT_LIGHT,
            activeforeground=ACCENT,
            relief="flat",
            bd=0,
            padx=15,
            pady=10,
            cursor="hand2",
            font=(self.font_body, 10, "bold" if selected else "normal"),
        )
        button.pack(fill="x", padx=10, pady=3)
        self.sidebar_buttons[label] = button
        return button

    def select_sidebar_item(self, selected_label):
        for label, button in self.sidebar_buttons.items():
            active = label == selected_label
            button.configure(
                bg=ACCENT_LIGHT if active else PANEL,
                fg=ACCENT if active else TEXT,
                font=(self.font_body, 10, "bold" if active else "normal"),
            )

    def center_popup(self, dialog):
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

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
