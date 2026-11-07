import base64
from io import BytesIO
import os
import tempfile
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector

from database import get_book_file, get_books, update_loan
from ui_theme import ACCENT, BACKGROUND, MUTED, PANEL, PANEL_LIGHT, TEXT

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class StudentPageMixin:
    def show_student_dashboard(self):
        self.clear_container()
        self.build_header("Perpustakaan Digital", f"Halo, {self.current_user_name}")

        toolbar = tk.Frame(self.container, bg=BACKGROUND)
        toolbar.pack(fill="x", padx=34, pady=(6, 14))
        search_box = tk.Frame(toolbar, bg=PANEL, highlightthickness=1,
                              highlightbackground="#303846")
        search_box.pack(side="left", fill="x", expand=True, padx=(0, 14))
        tk.Label(search_box, text="⌕", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 16)).pack(side="left", padx=(12, 4))
        search = tk.Entry(
            search_box, textvariable=self.search_var, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        search.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 10))
        search.insert(0, "")
        search.bind("<KeyRelease>", lambda _event: self.render_book_grid())
        self.filter_buttons = tk.Frame(toolbar, bg=BACKGROUND)
        self.filter_buttons.pack(side="right")
        for label in ("Semua Buku", "Tersedia", "Dipinjam"):
            self.make_button(
                self.filter_buttons, label,
                lambda value=label: self.set_filter(value),
                primary=label == self.active_filter,
            ).pack(side="left", padx=(5, 0))

        section = tk.Frame(self.container, bg=BACKGROUND)
        section.pack(fill="both", expand=True, padx=34, pady=(0, 28))
        section_header = tk.Frame(section, bg=BACKGROUND)
        section_header.pack(fill="x", pady=(0, 12))
        tk.Label(
            section_header, text="Jelajahi koleksi",
            bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        self.result_label = tk.Label(
            section_header, text="", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.result_label.pack(side="right")

        self.grid_canvas = tk.Canvas(
            section, bg=BACKGROUND, highlightthickness=0, borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(section, orient="vertical",
                                 command=self.grid_canvas.yview)
        self.grid_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.grid_canvas, bg=BACKGROUND)
        self.grid_window = self.grid_canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw"
        )
        self.grid_frame.bind(
            "<Configure>",
            lambda _event: self.grid_canvas.configure(
                scrollregion=self.grid_canvas.bbox("all")
            ),
        )
        self.grid_canvas.bind(
            "<Configure>",
            lambda event: self.grid_canvas.itemconfigure(
                self.grid_window, width=event.width
            ),
        )
        self.grid_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.render_book_grid()

    def on_mousewheel(self, event):
        if hasattr(self, "grid_canvas") and self.grid_canvas.winfo_exists():
            self.grid_canvas.yview_scroll(int(-event.delta / 120), "units")

    def set_filter(self, value):
        self.active_filter = value
        self.show_student_dashboard()

    def render_book_grid(self):
        if not hasattr(self, "grid_frame") or not self.grid_frame.winfo_exists():
            return
        for child in self.grid_frame.winfo_children():
            child.destroy()
        books = get_books(self.current_user_id)
        search = self.search_var.get().strip().casefold()
        if search:
            books = [
                book for book in books
                if search in " ".join(str(part or "") for part in book[1:4]).casefold()
            ]
        if self.active_filter == "Tersedia":
                books = [book for book in books if not book[6] and book[9] > 0]
        elif self.active_filter == "Dipinjam":
                books = [book for book in books if book[6] == "Dipinjam"]

        self.result_label.configure(text=f"{len(books)} buku")
        width = max(self.grid_canvas.winfo_width(), 760)
        columns = max(2, min(6, width // 190))
        if not books:
            message = "Belum ada buku dalam koleksi ini." if not search else "Buku tidak ditemukan."
            tk.Label(
                self.grid_frame, text=message, bg=BACKGROUND, fg=MUTED,
                font=("Segoe UI", 11),
            ).grid(row=0, column=0, columnspan=columns, pady=72)
            return
        for column in range(columns):
            self.grid_frame.grid_columnconfigure(column, weight=1)
        for index, book in enumerate(books):
            self.make_book_card(book).grid(
                row=index // columns, column=index % columns,
                padx=8, pady=(0, 24), sticky="n",
            )

    def make_book_card(self, book):
        card = tk.Frame(self.grid_frame, bg=BACKGROUND, width=168)
        card.grid_propagate(False)
        cover = tk.Canvas(
            card, width=168, height=236, bg=PANEL_LIGHT,
            highlightthickness=0, cursor="hand2",
        )
        cover.pack()
        cover_image = self.load_cover_image(book[4])
        if cover_image:
            cover.create_image(84, 118, image=cover_image)
            cover.image = cover_image
        else:
            palette = ["#245d68", "#785342", "#514a76", "#35634e",
                       "#76535f", "#3c587b", "#7b6743", "#345d55"]
            color = palette[book[0] % len(palette)]
            cover.create_rectangle(0, 0, 168, 236, fill=color, outline="")
            cover.create_polygon(
                0, 0, 168, 0, 168, 130, 0, 195,
                fill="#ffffff", outline="", stipple="gray50",
            )
            cover.create_oval(104, 28, 196, 120, fill="#ffffff",
                              outline="", stipple="gray50")
            cover.create_polygon(
                0, 182, 168, 120, 168, 236, 0, 236,
                fill="#10151d", outline="", stipple="gray50",
            )
            cover.create_text(
                14, 108, text=(book[1] or "Tanpa judul").upper(),
                anchor="w", width=140, fill=TEXT,
                font=("Segoe UI", 14, "bold"),
            )
            cover.create_text(
                14, 197, text=(book[2] or "Penulis tidak diketahui"),
                anchor="w", width=140, fill="#e0e5eb",
                font=("Segoe UI", 8),
            )
        if book[6] == "Dipinjam":
            cover.create_rectangle(0, 0, 168, 23, fill=ACCENT, outline="")
            cover.create_text(
                84, 11, text="ADA DI KOLEKSI SAYA",
                fill="#10201d", font=("Segoe UI", 7, "bold"),
            )
        cover.bind("<Button-1>", lambda _event, selected=book: self.show_book_detail(selected))
        title = tk.Label(
            card, text=book[1], bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 9, "bold"), anchor="w",
            wraplength=166, justify="left",
        )
        title.pack(fill="x", pady=(9, 2))
        author = tk.Label(
            card, text=book[2] or "Penulis tidak diketahui",
            bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 8), anchor="w",
        )
        author.pack(fill="x")
        for widget in (title, author):
            widget.bind("<Button-1>", lambda _event, selected=book: self.show_book_detail(selected))
            widget.configure(cursor="hand2")
        return card

    def load_cover_image(self, cover, width=168, height=236):
        if not cover:
            return None
        try:
            if Image is not None and ImageTk is not None:
                image = Image.open(BytesIO(cover)).convert("RGB")
                image.thumbnail((width, height))
                return ImageTk.PhotoImage(image)
            image = tk.PhotoImage(data=base64.b64encode(cover).decode("ascii"))
            factor = max(
                1,
                (image.width() + width - 1) // width,
                (image.height() + height - 1) // height,
            )
            return image.subsample(factor, factor)
        except (OSError, tk.TclError):
            return None

    def show_book_detail(self, book):
        dialog = tk.Toplevel(self)
        dialog.title(book[1])
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("760x500")
        body = tk.Frame(dialog, bg=PANEL)
        body.pack(fill="both", expand=True, padx=26, pady=24)
        cover_frame = tk.Frame(body, bg=PANEL_LIGHT, width=230, height=340)
        cover_frame.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 24))
        cover_frame.grid_propagate(False)
        cover_canvas = tk.Canvas(
            cover_frame, width=230, height=340, bg=PANEL_LIGHT,
            highlightthickness=0,
        )
        cover_canvas.pack()
        cover_image = self.load_cover_image(book[4], 230, 340)
        if cover_image:
            cover_canvas.create_image(115, 170, image=cover_image)
            cover_canvas.image = cover_image
        else:
            palette = ["#245d68", "#785342", "#514a76", "#35634e",
                       "#76535f", "#3c587b", "#7b6743", "#345d55"]
            color = palette[book[0] % len(palette)]
            cover_canvas.create_rectangle(0, 0, 230, 340, fill=color, outline="")
            cover_canvas.create_polygon(
                0, 0, 230, 0, 230, 188, 0, 265,
                fill="#ffffff", outline="", stipple="gray50",
            )
            cover_canvas.create_polygon(
                0, 250, 230, 175, 230, 340, 0, 340,
                fill="#10151d", outline="", stipple="gray50",
            )
            cover_canvas.create_text(
                18, 165, text=(book[1] or "Tanpa judul").upper(),
                anchor="w", width=195, fill=TEXT,
                font=("Segoe UI", 18, "bold"),
            )
            cover_canvas.create_text(
                18, 285, text=(book[2] or "Penulis tidak diketahui"),
                anchor="w", width=195, fill="#e0e5eb",
                font=("Segoe UI", 10),
            )

        details = tk.Frame(body, bg=PANEL)
        details.grid(row=0, column=1, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        tk.Label(
            details, text=book[1], bg=PANEL, fg=TEXT,
            font=("Segoe UI", 19, "bold"), wraplength=430,
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            details,
            text=f"{book[2] or 'Penulis tidak diketahui'}"
                 f"   ·   {book[3] or 'Penerbit tidak diketahui'}",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(7, 18))
        status_text = (
            f"Sedang dipinjam — batas pengembalian {book[7]}"
            if book[6] == "Dipinjam"
            else (
                f"{book[9]} dari {book[8]} salinan tersedia "
                "untuk dipinjam selama 7 hari."
                if book[9] > 0
                else f"Semua {book[8]} salinan sedang dipinjam."
            )
        )
        tk.Label(
            details, text=status_text, bg=PANEL, fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 16))
        tk.Label(
            details, text="Sinopsis", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        synopsis_frame = tk.Frame(details, bg=PANEL)
        synopsis_frame.pack(fill="both", expand=True)
        synopsis_text = tk.Text(
            synopsis_frame, height=8, wrap="word", bg=PANEL,
            fg=MUTED, font=("Segoe UI", 10), relief="flat",
            padx=0, pady=0, spacing1=2, cursor="arrow",
        )
        synopsis_scrollbar = ttk.Scrollbar(
            synopsis_frame, orient="vertical", command=synopsis_text.yview,
        )
        synopsis_text.configure(yscrollcommand=synopsis_scrollbar.set)
        synopsis_text.insert(
            "1.0", book[10] or "Sinopsis belum tersedia."
        )
        synopsis_text.configure(state="disabled")
        synopsis_text.pack(side="left", fill="both", expand=True)
        synopsis_scrollbar.pack(side="right", fill="y")
        tk.Label(
            details, text=f"Diunggah: {book[5] or '-'}",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(12, 0))
        actions = tk.Frame(body, bg=PANEL)
        actions.grid(row=1, column=1, sticky="ew", pady=(18, 0))

        def loan_action(action):
            try:
                success, message = update_loan(
                    self.current_user_id, book[0], action
                )
                if not success:
                    messagebox.showwarning("Informasi", message, parent=dialog)
                    return
                messagebox.showinfo("Berhasil", message, parent=dialog)
                dialog.destroy()
                self.render_book_grid()
            except mysql.connector.Error as error:
                messagebox.showerror("Kesalahan database", str(error), parent=dialog)

        if book[6] == "Dipinjam":
            self.make_button(
                actions, "Kembalikan buku",
                lambda: loan_action("return"), primary=True,
            ).pack(side="left")
            self.make_button(
                actions, "Baca buku",
                lambda: self.open_book_record(book, dialog),
            ).pack(side="left", padx=8)
        else:
            if book[9] > 0:
                self.make_button(
                    actions, "Pinjam 7 hari",
                    lambda: loan_action("borrow"), primary=True,
                ).pack(side="left")
            else:
                tk.Label(
                    actions, text="Stok habis", bg=PANEL, fg=MUTED,
                    font=("Segoe UI", 9, "bold"),
                ).pack(side="left")
        self.make_button(actions, "Tutup", dialog.destroy).pack(side="right")

    def open_book_record(self, book, parent):
        try:
            file_data = get_book_file(book[0])
            if not file_data:
                messagebox.showerror(
                    "File tidak tersedia",
                    "Buku ini belum memiliki file PDF.",
                    parent=parent,
                )
                return
            cache_dir = Path(tempfile.gettempdir()) / "ruang-baca"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_file = cache_dir / f"{uuid.uuid4().hex}.pdf"
            cached_file.write_bytes(file_data)
            self.open_book(cached_file, parent)
        except (OSError, ValueError, mysql.connector.Error) as error:
            messagebox.showerror("Tidak dapat membuka buku", str(error), parent=parent)
