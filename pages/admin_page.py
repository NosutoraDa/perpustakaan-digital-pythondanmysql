import shutil
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mysql.connector

from database import connect_database, replace_book_pdf
from ui_theme import ACCENT, BACKGROUND, MUTED, PANEL, PANEL_LIGHT, TEXT


class AdminPageMixin:
    def show_admin_dashboard(self):
        self.clear_container()
        self.build_header("Kelola perpustakaan", "Unggah koleksi dan pantau buku")
        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=34, pady=(10, 30))
        catalogue = tk.Frame(notebook, bg=BACKGROUND)
        add_book = tk.Frame(notebook, bg=BACKGROUND)
        notebook.add(catalogue, text="  Koleksi Buku  ")
        notebook.add(add_book, text="  Tambah Buku  ")
        self.build_admin_catalogue(catalogue)
        self.build_book_form(add_book)

    def build_admin_catalogue(self, parent):
        top = tk.Frame(parent, bg=BACKGROUND)
        top.pack(fill="x", padx=18, pady=16)
        tk.Label(
            top, text="Koleksi buku", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        self.make_button(
            top, "Ganti PDF buku terpilih", self.replace_selected_book_pdf,
        ).pack(side="right", padx=(8, 0))
        self.make_button(top, "Hapus buku terpilih", self.delete_selected_book).pack(side="right")
        columns = ("id", "judul", "penulis", "penerbit", "tanggal")
        self.book_tree = ttk.Treeview(
            parent, columns=columns, show="headings", style="Library.Treeview",
        )
        for key, label, width in (
            ("id", "ID", 55), ("judul", "Judul", 260),
            ("penulis", "Penulis", 180), ("penerbit", "Penerbit", 180),
            ("tanggal", "Tanggal unggah", 130),
        ):
            self.book_tree.heading(key, text=label)
            self.book_tree.column(key, width=width, anchor="w")
        self.book_tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.load_admin_books()

    def load_admin_books(self):
        for item in self.book_tree.get_children():
            self.book_tree.delete(item)
        connection = connect_database()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id_buku, judul_buku, penulis, penerbit, tgl_diunggah "
                "FROM buku_digital ORDER BY id_buku DESC"
            )
            rows = cursor.fetchall()
        finally:
            connection.close()
        for row in rows:
            self.book_tree.insert("", "end", iid=str(row[0]), values=row)

    def delete_selected_book(self):
        selection = self.book_tree.selection()
        if not selection:
            messagebox.showwarning("Pilih buku", "Pilih buku yang ingin dihapus.")
            return
        if not messagebox.askyesno("Hapus buku", "Hapus buku terpilih dari katalog?"):
            return
        connection = connect_database()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM buku_digital WHERE id_buku = %s", (int(selection[0]),)
            )
            connection.commit()
        except mysql.connector.IntegrityError:
            messagebox.showerror(
                "Buku memiliki riwayat",
                "Buku yang pernah dipinjam tidak dapat dihapus agar riwayat tetap tersimpan.",
            )
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error))
        else:
            self.load_admin_books()
        finally:
            connection.close()

    def replace_selected_book_pdf(self):
        selection = self.book_tree.selection()
        if not selection:
            messagebox.showwarning("Pilih buku", "Pilih buku yang PDF-nya ingin diganti.")
            return

        source_path = filedialog.askopenfilename(
            title="Pilih PDF pengganti",
            filetypes=(("PDF", "*.pdf"),),
        )
        if not source_path:
            return

        try:
            replace_book_pdf(int(selection[0]), source_path)
        except (OSError, ValueError, mysql.connector.Error) as error:
            messagebox.showerror("Gagal mengganti PDF", str(error))
            return

        self.load_admin_books()
        messagebox.showinfo(
            "Berhasil",
            "PDF buku berhasil diganti. Metadata dan riwayat peminjaman tetap tersimpan.",
        )

    def build_book_form(self, parent):
        form = tk.Frame(parent, bg=PANEL, padx=24, pady=22)
        form.pack(fill="x", padx=18, pady=20, anchor="n")
        tk.Label(
            form, text="Tambahkan buku baru", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))
        fields = {}
        for row, (key, label) in enumerate(
            (("judul", "Judul buku"), ("penulis", "Penulis"), ("penerbit", "Penerbit")),
            start=1,
        ):
            tk.Label(form, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=7)
            entry = tk.Entry(
                form, bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                relief="flat", font=("Segoe UI", 10), width=48,
            )
            entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(16, 0), ipady=8)
            fields[key] = entry
        paths = {"book": "", "cover": ""}
        selected_labels = {}
        for row, (key, label, types) in enumerate(
            (
                ("book", "File buku (PDF)", [("PDF", "*.pdf")]),
                ("cover", "Sampul", [("Gambar", "*.png *.gif *.jpg *.jpeg")]),
            ),
            start=4,
        ):
            tk.Label(form, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=8)
            selected_labels[key] = tk.Label(
                form, text="Belum dipilih", bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9), anchor="w",
            )
            selected_labels[key].grid(row=row, column=1, sticky="ew", padx=(16, 10))

            def choose_file(file_key=key, file_types=types):
                path = filedialog.askopenfilename(filetypes=file_types)
                if path:
                    paths[file_key] = path
                    selected_labels[file_key].configure(
                        text=Path(path).name, fg=ACCENT
                    )

            self.make_button(
                form, "Pilih file", choose_file,
            ).grid(row=row, column=2, sticky="e")
        form.grid_columnconfigure(1, weight=1)

        def save_book():
            title = fields["judul"].get().strip()
            if not title or not paths["book"]:
                messagebox.showerror(
                    "Data belum lengkap", "Judul dan PDF buku wajib diisi."
                )
                return
            stored_cover = None
            try:
                book_path = Path(paths["book"])
                if book_path.suffix.lower() != ".pdf":
                    raise ValueError("Select a PDF file.")
                file_data = book_path.read_bytes()
                if paths["cover"]:
                    cover_source = Path(paths["cover"])
                    cover_destination = Path("uploads/covers") / (
                        f"{uuid.uuid4().hex}_{cover_source.name}"
                    )
                    shutil.copy2(cover_source, cover_destination)
                    stored_cover = cover_destination
                connection = connect_database()
                try:
                    cursor = connection.cursor()
                    cursor.execute(
                        """
                        INSERT INTO buku_digital
                            (judul_buku, penulis, penerbit, tautan_file,
                             cover_buku, file_data, tgl_diunggah)
                        VALUES (%s, %s, %s, NULL, %s, %s, CURRENT_DATE)
                        """,
                        (
                            title, fields["penulis"].get().strip(),
                            fields["penerbit"].get().strip(),
                            str(stored_cover) if stored_cover else None,
                            file_data,
                        ),
                    )
                    connection.commit()
                finally:
                    connection.close()
            except (OSError, ValueError, mysql.connector.Error) as error:
                if stored_cover is not None:
                    stored_cover.unlink(missing_ok=True)
                messagebox.showerror("Gagal menyimpan buku", str(error))
                return
            for entry in fields.values():
                entry.delete(0, tk.END)
            for key in paths:
                paths[key] = ""
                selected_labels[key].configure(text="Belum dipilih", fg=MUTED)
            self.load_admin_books()
            messagebox.showinfo(
                "Berhasil", "Buku dan isi PDF berhasil disimpan di database."
            )

        self.make_button(form, "Simpan buku", save_book, primary=True).grid(
            row=6, column=1, sticky="w", padx=(16, 0), pady=(20, 0)
        )
