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
from ui_theme import (
    ACCENT,
    ACCENT_LIGHT,
    BACKGROUND,
    BORDER,
    MUTED,
    PANEL,
    PANEL_LIGHT,
    SUCCESS,
    TEXT,
)

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class StudentPageMixin:
    def show_student_dashboard(self):
        self.clear_container()
        self.build_header()
        self.book_catalogue_data = None
        self.cover_image_cache = {}
        self.search_after_id = None
        self.add_sidebar_item(
            "Koleksi Buku",
            lambda: self.select_sidebar_item("Koleksi Buku"),
            selected=True,
        )

        page_title = tk.Label(
            self.workspace, text="Koleksi Buku", bg=BACKGROUND, fg=TEXT,
            font=(self.font_display, 23, "bold"),
        )
        page_title.pack(anchor="w", padx=3, pady=(2, 2))
        tk.Label(
            self.workspace, text="Jelajahi dan pinjam buku dari perpustakaan.",
            bg=BACKGROUND, fg=MUTED, font=(self.font_body, 9),
        ).pack(anchor="w", padx=3, pady=(0, 14))

        section = tk.Frame(
            self.workspace, bg=PANEL, highlightthickness=1,
            highlightbackground=BORDER,
        )
        section.pack(fill="both", expand=True)
        toolbar = tk.Frame(section, bg=PANEL)
        toolbar.pack(fill="x", padx=18, pady=(18, 12))
        search_box = tk.Frame(
            toolbar, bg=PANEL_LIGHT, highlightthickness=1,
            highlightbackground=BORDER,
        )
        search_box.pack(fill="x", pady=(0, 10))
        tk.Label(search_box, text="⌕", bg=PANEL_LIGHT, fg=MUTED,
                 font=(self.font_body, 16)).pack(side="left", padx=(12, 4))
        search = tk.Entry(
            search_box, textvariable=self.search_var, bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=(self.font_body, 10),
            highlightthickness=0,
        )
        search.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))
        search.insert(0, "")
        search.bind("<KeyRelease>", self.schedule_book_search)
        self.filter_buttons = tk.Frame(toolbar, bg=PANEL)
        self.filter_buttons.pack(anchor="w")
        self.filter_button_widgets = {}
        for label in ("Semua Buku", "Tersedia", "Dipinjam"):
            button = self.make_button(
                self.filter_buttons, label,
                lambda value=label: self.set_filter(value),
                primary=label == self.active_filter,
            )
            button.pack(side="left", padx=(0, 7))
            self.filter_button_widgets[label] = button

        section_header = tk.Frame(section, bg=PANEL)
        section_header.pack(fill="x", padx=18, pady=(0, 10))
        tk.Label(
            section_header, text="Katalog buku",
            bg=PANEL, fg=TEXT, font=(self.font_display, 13, "bold"),
        ).pack(side="left")
        self.result_label = tk.Label(
            section_header, text="", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        )
        self.result_label.pack(side="right")

        self.grid_canvas = tk.Canvas(
            section, bg=PANEL, highlightthickness=0, borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(section, orient="vertical",
                                 command=self.grid_canvas.yview,
                                 style="Library.Vertical.TScrollbar")
        self.grid_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 12))
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.grid_canvas, bg=PANEL)
        self.grid_columns = 0
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
            self.resize_book_grid,
        )
        self.unbind_all("<MouseWheel>")
        self.grid_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.render_book_grid()

    def schedule_book_search(self, _event=None):
        if self.search_after_id is not None:
            self.after_cancel(self.search_after_id)
        self.search_after_id = self.after(180, self.render_book_grid)

    def resize_book_grid(self, event):
        self.grid_canvas.itemconfigure(self.grid_window, width=event.width)
        columns = max(2, min(6, max(event.width, 380) // 190))
        if columns != self.grid_columns:
            self.grid_columns = columns
            self.render_book_grid()

    def on_mousewheel(self, event):
        if hasattr(self, "grid_canvas") and self.grid_canvas.winfo_exists():
            self.grid_canvas.yview_scroll(int(-event.delta / 120), "units")

    def set_filter(self, value):
        self.active_filter = value
        for label, button in self.filter_button_widgets.items():
            active = label == value
            button.configure(
                bg=ACCENT if active else PANEL,
                fg="#ffffff" if active else TEXT,
                activebackground="#5669d1" if active else ACCENT_LIGHT,
            )
        self.render_book_grid()

    def render_book_grid(self):
        if not hasattr(self, "grid_frame") or not self.grid_frame.winfo_exists():
            return
        for child in self.grid_frame.winfo_children():
            child.destroy()
        if self.book_catalogue_data is None:
            self.book_catalogue_data = get_books(self.current_user_id)
        if self.search_after_id is not None:
            self.after_cancel(self.search_after_id)
            self.search_after_id = None
        books = self.book_catalogue_data
        search = self.search_var.get().strip().casefold()
        if search:
            books = [
                book for book in books
                if search in " ".join(
                    str(part or "") for part in (*book[1:4], book[11])
                ).casefold()
            ]
        if self.active_filter == "Tersedia":
                books = [book for book in books if not book[6] and book[9] > 0]
        elif self.active_filter == "Dipinjam":
                books = [book for book in books if book[6] == "Dipinjam"]

        self.result_label.configure(text=f"{len(books)} buku")
        width = max(self.grid_canvas.winfo_width(), 380)
        columns = max(2, min(6, width // 190))
        self.grid_columns = columns
        if not books:
            message = "Belum ada buku dalam koleksi ini." if not search else "Buku tidak ditemukan."
            tk.Label(
                self.grid_frame, text=message, bg=PANEL, fg=MUTED,
                font=(self.font_body, 11),
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
        card = tk.Frame(
            self.grid_frame,
            bg=PANEL,
            width=176,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
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
                font=(self.font_body, 14, "bold"),
            )
            cover.create_text(
                14, 197, text=(book[2] or "Penulis tidak diketahui"),
                anchor="w", width=140, fill="#e0e5eb",
                font=(self.font_body, 8),
            )
        if book[6] == "Dipinjam":
            cover.create_rectangle(0, 0, 168, 23, fill=SUCCESS, outline="")
            cover.create_text(
                84, 11, text="ADA DI KOLEKSI SAYA",
                fill="#ffffff", font=(self.font_body, 7, "bold"),
            )
        cover.bind("<Button-1>", lambda _event, selected=book: self.show_book_detail(selected))
        title = tk.Label(
            card, text=book[1], bg=PANEL, fg=TEXT,
            font=(self.font_display, 10, "bold"), anchor="w",
            wraplength=166, justify="left",
        )
        title.pack(fill="x", pady=(9, 2))
        author = tk.Label(
            card, text=book[2] or "Penulis tidak diketahui",
            bg=PANEL, fg=MUTED, font=(self.font_body, 8), anchor="w",
        )
        author.pack(fill="x")
        for widget in (title, author):
            widget.bind("<Button-1>", lambda _event, selected=book: self.show_book_detail(selected))
            widget.configure(cursor="hand2")
        return card

    def load_cover_image(self, cover, width=168, height=236):
        if not cover:
            return None
        key = (id(cover), width, height)
        if key in self.cover_image_cache:
            return self.cover_image_cache[key]
        try:
            if Image is not None and ImageTk is not None:
                image = Image.open(BytesIO(cover)).convert("RGB")
                image.thumbnail((width, height))
                result = ImageTk.PhotoImage(image)
            else:
                image = tk.PhotoImage(
                    data=base64.b64encode(cover).decode("ascii")
                )
                factor = max(
                    1,
                    (image.width() + width - 1) // width,
                    (image.height() + height - 1) // height,
                )
                result = image.subsample(factor, factor)
        except (OSError, tk.TclError):
            result = None
        if len(self.cover_image_cache) >= 64:
            self.cover_image_cache.pop(next(iter(self.cover_image_cache)))
        self.cover_image_cache[key] = result
        return result

    def show_book_detail(self, book):
        dialog = tk.Toplevel(self)
        dialog.title(book[1])
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("760x500")
        self.center_popup(dialog)
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
                font=(self.font_body, 18, "bold"),
            )
            cover_canvas.create_text(
                18, 285, text=(book[2] or "Penulis tidak diketahui"),
                anchor="w", width=195, fill="#e0e5eb",
                font=(self.font_body, 10),
            )

        details = tk.Frame(body, bg=PANEL)
        details.grid(row=0, column=1, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        tk.Label(
            details, text=book[1], bg=PANEL, fg=TEXT,
            font=(self.font_display, 21, "bold"), wraplength=430,
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            details,
            text=f"{book[2] or 'Penulis tidak diketahui'}"
                 f"   ·   {book[3] or 'Penerbit tidak diketahui'}",
            bg=PANEL, fg=MUTED, font=(self.font_body, 9),
        ).pack(anchor="w", pady=(7, 18))
        status_text = (
            f"Sedang dipinjam — batas pengembalian {book[7]}"
            if book[6] == "Dipinjam"
            else (
                f"{book[9]} dari {book[8]} salinan tersedia. "
                "Pilih durasi pinjaman 1–7 hari."
                if book[9] > 0
                else f"Semua {book[8]} salinan sedang dipinjam."
            )
        )
        tk.Label(
            details, text=status_text, bg=PANEL, fg=ACCENT,
            font=(self.font_body, 10, "bold"),
        ).pack(anchor="w", pady=(0, 16))
        tags_frame = tk.Frame(details, bg=PANEL)
        tags_frame.pack(anchor="w", fill="x", pady=(0, 14))
        tk.Label(
            tags_frame, text="Tag materi", bg=PANEL, fg=TEXT,
            font=(self.font_body, 10, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        tags = [tag.strip() for tag in (book[11] or "").split(",") if tag.strip()]
        if tags:
            tag_buttons = tk.Frame(tags_frame, bg=PANEL)
            tag_buttons.pack(anchor="w", fill="x")
            for index, tag in enumerate(tags):
                tag_button = tk.Button(
                    tag_buttons,
                    text=tag,
                    command=lambda value=tag: self.search_books_by_tag(
                        value, dialog
                    ),
                    bg=PANEL_LIGHT,
                    fg=ACCENT,
                    activebackground=ACCENT_LIGHT,
                    activeforeground=ACCENT,
                    relief="flat",
                    bd=0,
                    padx=9,
                    pady=5,
                    cursor="hand2",
                    font=(self.font_body, 9, "bold"),
                )
                tag_button.grid(
                    row=index // 3,
                    column=index % 3,
                    sticky="w",
                    padx=(0, 6),
                    pady=(0, 5),
                )
        else:
            tk.Label(
                tags_frame,
                text="Belum ada tag materi. Admin dapat menambahkannya.",
                bg=PANEL,
                fg=MUTED,
                font=(self.font_body, 9),
            ).pack(anchor="w")
        tk.Label(
            details, text="Deskripsi Materi Pembelajaran",
            bg=PANEL, fg=TEXT,
            font=(self.font_body, 11, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        synopsis_frame = tk.Frame(details, bg=PANEL)
        synopsis_frame.pack(fill="both", expand=True)
        synopsis_text = tk.Text(
            synopsis_frame, height=8, wrap="word", bg=PANEL,
            fg=MUTED, font=(self.font_body, 10), relief="flat",
            padx=0, pady=0, spacing1=2, cursor="arrow",
        )
        synopsis_scrollbar = ttk.Scrollbar(
            synopsis_frame, orient="vertical", command=synopsis_text.yview,
        )
        synopsis_text.configure(yscrollcommand=synopsis_scrollbar.set)
        synopsis_text.insert(
            "1.0", book[10] or "Deskripsi materi belum tersedia."
        )
        synopsis_text.configure(state="disabled")
        synopsis_text.pack(side="left", fill="both", expand=True)
        synopsis_scrollbar.pack(side="right", fill="y")
        tk.Label(
            details, text=f"Diunggah: {book[5] or '-'}",
            bg=PANEL, fg=MUTED, font=(self.font_body, 9),
        ).pack(anchor="w", pady=(12, 0))
        actions = tk.Frame(body, bg=PANEL)
        actions.grid(row=1, column=1, sticky="ew", pady=(18, 0))

        def loan_action(action, rental_days=7):
            try:
                success, message = update_loan(
                    self.current_user_id, book[0], action, rental_days
                )
                if not success:
                    messagebox.showwarning("Informasi", message, parent=dialog)
                    return
                messagebox.showinfo("Berhasil", message, parent=dialog)
                dialog.destroy()
                self.book_catalogue_data = None
                self.cover_image_cache.clear()
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
                tk.Label(
                    actions, text="Durasi (hari)", bg=PANEL, fg=MUTED,
                    font=(self.font_body, 9),
                ).pack(side="left", padx=(0, 6))
                rental_days = tk.StringVar(master=dialog, value="7")
                ttk.Combobox(
                    actions,
                    textvariable=rental_days,
                    values=tuple(str(days) for days in range(1, 8)),
                    state="readonly",
                    width=3,
                ).pack(side="left", padx=(0, 10))
                self.make_button(
                    actions, "Pinjam",
                    lambda: loan_action("borrow", int(rental_days.get())),
                    primary=True,
                ).pack(side="left")
            else:
                tk.Label(
                    actions, text="Stok habis", bg=PANEL, fg=MUTED,
                    font=(self.font_body, 9, "bold"),
                ).pack(side="left")
        self.make_button(actions, "Tutup", dialog.destroy).pack(side="right")

    def search_books_by_tag(self, tag, dialog):
        dialog.destroy()
        self.search_var.set(tag)
        self.set_filter("Semua Buku")

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
