import base64
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import mysql.connector

from database import (
    connect_database,
    get_admin_book,
    get_users,
    replace_book_pdf,
    update_book_details,
    update_user_account,
    update_book_stock,
)
from ui_theme import ACCENT, BACKGROUND, MUTED, PANEL, PANEL_LIGHT, TEXT

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class AdminPageMixin:
    def show_admin_dashboard(self):
        self.clear_container()
        self.build_header("Kelola perpustakaan", "Unggah koleksi dan pantau buku")
        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=34, pady=(10, 30))
        catalogue = tk.Frame(notebook, bg=BACKGROUND)
        add_book = tk.Frame(notebook, bg=BACKGROUND)
        users = tk.Frame(notebook, bg=BACKGROUND)
        notebook.add(catalogue, text="  Koleksi Buku  ")
        notebook.add(add_book, text="  Tambah Buku  ")
        notebook.add(users, text="  Pengguna  ")
        self.build_admin_catalogue(catalogue)
        self.build_book_form(add_book)
        self.build_user_management(users)

    def build_admin_catalogue(self, parent):
        top = tk.Frame(parent, bg=BACKGROUND)
        top.pack(fill="x", padx=18, pady=16)
        tk.Label(
            top, text="Koleksi buku", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        self.make_button(
            top, "Ubah detail buku", self.edit_selected_book,
        ).pack(side="right", padx=(8, 0))
        self.make_button(
            top, "Ganti PDF buku terpilih", self.replace_selected_book_pdf,
        ).pack(side="right", padx=(8, 0))
        self.make_button(top, "Ubah stok buku", self.change_selected_book_stock).pack(
            side="right", padx=(8, 0)
        )
        self.make_button(top, "Hapus buku terpilih", self.delete_selected_book).pack(side="right")
        columns = (
            "id", "judul", "penulis", "penerbit", "stok", "tanggal",
            "sampul", "sinopsis",
        )
        self.book_tree = ttk.Treeview(
            parent, columns=columns, show="headings", style="Library.Treeview",
        )
        for key, label, width in (
            ("id", "ID", 55), ("judul", "Judul", 260),
            ("penulis", "Penulis", 180), ("penerbit", "Penerbit", 180),
            ("stok", "Salinan", 80), ("tanggal", "Tanggal unggah", 130),
            ("sampul", "Sampul", 90), ("sinopsis", "Sinopsis", 100),
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
                "SELECT id_buku, judul_buku, penulis, penerbit, jumlah_stok, "
                "tgl_diunggah, "
                "CASE WHEN cover_data IS NULL THEN 'Belum ada' ELSE 'Ada' END, "
                "CASE WHEN sinopsis IS NULL OR TRIM(sinopsis) = '' "
                "THEN 'Belum ada' ELSE 'Ada' END "
                "FROM buku_digital ORDER BY id_buku DESC"
            )
            rows = cursor.fetchall()
        finally:
            connection.close()
        for row in rows:
            self.book_tree.insert("", "end", iid=str(row[0]), values=row)
        self.book_tree.bind(
            "<Double-1>", lambda _event: self.edit_selected_book()
        )

    def edit_selected_book(self):
        selection = self.book_tree.selection()
        if not selection:
            messagebox.showwarning("Pilih buku", "Pilih buku yang ingin diubah.")
            return
        try:
            book = get_admin_book(int(selection[0]))
        except (ValueError, mysql.connector.Error) as error:
            messagebox.showerror("Gagal membuka buku", str(error))
            return

        dialog = tk.Toplevel(self)
        dialog.title("Ubah detail buku")
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("720x540")
        body = tk.Frame(dialog, bg=PANEL, padx=22, pady=20)
        body.pack(fill="both", expand=True)
        cover_frame = tk.Frame(body, bg=PANEL_LIGHT, width=205, height=300)
        cover_frame.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 22))
        cover_frame.grid_propagate(False)
        cover_preview = tk.Label(
            cover_frame, text="Sampul belum dipilih",
            bg=PANEL_LIGHT, fg=MUTED, wraplength=175,
            font=("Segoe UI", 10),
        )
        cover_preview.place(relx=0.5, rely=0.5, anchor="center")
        cover_state = {"data": book[5], "image": None}

        def display_cover(data):
            cover_state["data"] = data
            cover_state["image"] = None
            if not data:
                cover_preview.configure(image="", text="Sampul belum dipilih")
                return
            try:
                if Image is not None and ImageTk is not None:
                    image = Image.open(BytesIO(data)).convert("RGB")
                    image.thumbnail((205, 300))
                    photo = ImageTk.PhotoImage(image)
                else:
                    photo = tk.PhotoImage(data=base64.b64encode(data).decode("ascii"))
                    factor = max(
                        1,
                        (photo.width() + 204) // 205,
                        (photo.height() + 299) // 300,
                    )
                    photo = photo.subsample(factor, factor)
                cover_state["image"] = photo
                cover_preview.configure(image=photo, text="")
            except (OSError, tk.TclError):
                cover_preview.configure(
                    image="", text="Format sampul tidak dapat ditampilkan"
                )

        fields = {}
        for row, (label, value) in enumerate(
            (
                ("Judul", book[1] or ""),
                ("Penulis", book[2] or ""),
                ("Penerbit", book[3] or ""),
            )
        ):
            tk.Label(
                body, text=label, bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9),
            ).grid(row=row, column=1, sticky="w", pady=4)
            entry = tk.Entry(
                body, bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                relief="flat", font=("Segoe UI", 10),
            )
            entry.insert(0, value)
            entry.grid(row=row, column=2, sticky="ew", padx=(12, 0), ipady=7)
            fields[label] = entry

        tk.Label(
            body, text="Sinopsis", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=3, column=1, sticky="nw", pady=6)
        synopsis_frame = tk.Frame(body, bg=PANEL_LIGHT)
        synopsis_frame.grid(
            row=3, column=2, sticky="nsew", padx=(12, 0), pady=4
        )
        synopsis = tk.Text(
            synopsis_frame, height=9, wrap="word", bg=PANEL_LIGHT,
            fg=TEXT, insertbackground=TEXT, relief="flat",
            font=("Segoe UI", 10),
        )
        synopsis_scrollbar = ttk.Scrollbar(
            synopsis_frame, orient="vertical", command=synopsis.yview,
        )
        synopsis.configure(yscrollcommand=synopsis_scrollbar.set)
        synopsis.insert("1.0", book[4] or "")
        synopsis.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        synopsis_scrollbar.pack(side="right", fill="y")
        cover_actions = tk.Frame(body, bg=PANEL)
        cover_actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        def choose_cover():
            path = filedialog.askopenfilename(
                parent=dialog,
                title="Pilih sampul buku",
                filetypes=(("Gambar", "*.png *.gif *.jpg *.jpeg"),),
            )
            if not path:
                return
            try:
                cover_data = Path(path).read_bytes()
                display_cover(cover_data)
            except OSError as error:
                messagebox.showerror(
                    "Sampul tidak dapat dibuka", str(error), parent=dialog
                )

        self.make_button(
            cover_actions, "Pilih sampul", choose_cover,
        ).pack(side="left")
        self.make_button(
            cover_actions, "Hapus sampul", lambda: display_cover(None),
        ).pack(side="left", padx=(8, 0))
        actions = tk.Frame(body, bg=PANEL)
        actions.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(16, 0))
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(3, weight=1)

        def save_details():
            try:
                message = update_book_details(
                    int(book[0]),
                    fields["Judul"].get(),
                    fields["Penulis"].get(),
                    fields["Penerbit"].get(),
                    synopsis.get("1.0", "end-1c"),
                    cover_state["data"],
                )
            except (ValueError, mysql.connector.Error) as error:
                messagebox.showerror(
                    "Gagal menyimpan buku", str(error), parent=dialog
                )
                return
            self.load_admin_books()
            dialog.destroy()
            messagebox.showinfo("Berhasil", message, parent=self)

        display_cover(book[5])
        self.make_button(
            actions, "Simpan perubahan", save_details, primary=True,
        ).pack(side="left")
        self.make_button(
            actions, "Tutup", dialog.destroy,
        ).pack(side="right")

    def change_selected_book_stock(self):
        selection = self.book_tree.selection()
        if not selection:
            messagebox.showwarning("Pilih buku", "Pilih buku yang stoknya ingin diubah.")
            return

        values = self.book_tree.item(selection[0], "values")
        stock = simpledialog.askinteger(
            "Ubah stok buku",
            "Jumlah salinan yang dapat dipinjam bersamaan:",
            initialvalue=int(values[4]),
            minvalue=0,
            parent=self,
        )
        if stock is None:
            return

        try:
            success, message = update_book_stock(int(selection[0]), stock)
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error))
            return
        if not success:
            messagebox.showwarning("Stok tidak dapat diubah", message)
            return
        self.load_admin_books()
        messagebox.showinfo("Berhasil", message)

    def build_user_management(self, parent):
        top = tk.Frame(parent, bg=BACKGROUND)
        top.pack(fill="x", padx=18, pady=16)
        tk.Label(
            top, text="Kelola pengguna", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        self.make_button(
            top, "Kelola pengguna terpilih", self.edit_selected_user,
        ).pack(side="right")
        columns = ("nim", "nama", "role", "status")
        self.user_tree = ttk.Treeview(
            parent, columns=columns, show="headings", style="Library.Treeview",
        )
        for key, label, width in (
            ("nim", "NIM", 140),
            ("nama", "Nama", 260),
            ("role", "Peran", 150),
            ("status", "Akun", 160),
        ):
            self.user_tree.heading(key, text=label)
            self.user_tree.column(key, width=width, anchor="w")
        self.user_tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.load_users()

    def load_users(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        for user in get_users():
            status = "Siap masuk" if user[4] else "Belum mengatur password"
            self.user_tree.insert(
                "", "end", iid=str(user[0]),
                values=(user[1], user[2], user[3], status),
            )
        self.user_tree.bind(
            "<Double-1>", lambda _event: self.edit_selected_user()
        )

    def edit_selected_user(self):
        selection = self.user_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Pilih pengguna", "Pilih pengguna yang ingin dikelola."
            )
            return

        user_id = int(selection[0])
        values = self.user_tree.item(selection[0], "values")
        dialog = tk.Toplevel(self)
        dialog.title("Kelola pengguna")
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("480x440")
        body = tk.Frame(dialog, bg=PANEL, padx=26, pady=24)
        body.pack(fill="both", expand=True)
        tk.Label(
            body, text="Data pengguna", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        for row, (label, value) in enumerate(
            (("NIM", values[0]), ("Nama", values[1]), ("Status akun", values[3])),
            start=1,
        ):
            tk.Label(
                body, text=label, bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9),
            ).grid(row=row, column=0, sticky="w", pady=8)
            tk.Label(
                body, text=value, bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10),
            ).grid(row=row, column=1, sticky="w", padx=(18, 0), pady=8)

        tk.Label(
            body, text="Peran", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=4, column=0, sticky="w", pady=8)
        role = tk.StringVar(value=values[2])
        role_picker = ttk.Combobox(
            body, textvariable=role, state="readonly",
            values=("Admin-CRUD", "Siswa-Rent"),
        )
        role_picker.grid(row=4, column=1, sticky="ew", padx=(18, 0), pady=8)

        tk.Label(
            body, text="Password baru", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=5, column=0, sticky="w", pady=8)
        password = tk.Entry(
            body, show="*", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        password.grid(row=5, column=1, sticky="ew", padx=(18, 0), ipady=7)
        tk.Label(
            body, text="Ulangi password", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=6, column=0, sticky="w", pady=8)
        confirmation = tk.Entry(
            body, show="*", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        confirmation.grid(
            row=6, column=1, sticky="ew", padx=(18, 0), ipady=7
        )
        tk.Label(
            body, text="Kosongkan password jika tidak ingin mereset.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8),
        ).grid(row=7, column=1, sticky="w", padx=(18, 0), pady=(2, 0))
        body.grid_columnconfigure(1, weight=1)
        actions = tk.Frame(body, bg=PANEL)
        actions.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(22, 0))

        def save_user():
            new_password = password.get()
            repeated_password = confirmation.get()
            if bool(new_password) != bool(repeated_password):
                messagebox.showerror(
                    "Password tidak lengkap",
                    "Isi kedua kolom password untuk mereset password.",
                    parent=dialog,
                )
                return
            if new_password and new_password != repeated_password:
                messagebox.showerror(
                    "Password tidak cocok",
                    "Password yang dimasukkan berbeda.",
                    parent=dialog,
                )
                return
            try:
                success, message = update_user_account(
                    self.current_user_id,
                    user_id,
                    role.get(),
                    new_password or None,
                )
            except ValueError as error:
                messagebox.showerror(
                    "Data tidak valid", str(error), parent=dialog
                )
                return
            except mysql.connector.Error as error:
                messagebox.showerror(
                    "Kesalahan database", str(error), parent=dialog
                )
                return
            if not success:
                messagebox.showwarning(
                    "Perubahan tidak dapat disimpan", message, parent=dialog
                )
                return
            self.load_users()
            dialog.destroy()
            messagebox.showinfo("Berhasil", message, parent=self)

        self.make_button(
            actions, "Simpan perubahan", save_user, primary=True,
        ).pack(side="left")
        self.make_button(actions, "Tutup", dialog.destroy).pack(side="right")

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
            (
                ("judul", "Judul buku"),
                ("penulis", "Penulis"),
                ("penerbit", "Penerbit"),
                ("stok", "Jumlah salinan"),
            ),
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
        tk.Label(
            form, text="Sinopsis", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=5, column=0, sticky="nw", pady=8)
        synopsis = tk.Text(
            form, height=4, wrap="word", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        synopsis.grid(row=5, column=1, columnspan=2, sticky="ew",
                      padx=(16, 0), pady=7)
        paths = {"book": "", "cover": ""}
        selected_labels = {}
        for row, (key, label, types) in enumerate(
            (
                ("book", "File buku (PDF)", [("PDF", "*.pdf")]),
                ("cover", "Sampul", [("Gambar", "*.png *.gif *.jpg *.jpeg")]),
            ),
            start=6,
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
            try:
                stock = int(fields["stok"].get())
                if stock < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Stok tidak valid", "Jumlah salinan harus bilangan bulat minimal 0."
                )
                return
            try:
                book_path = Path(paths["book"])
                if book_path.suffix.lower() != ".pdf":
                    raise ValueError("Select a PDF file.")
                file_data = book_path.read_bytes()
                cover_data = Path(paths["cover"]).read_bytes() if paths["cover"] else None
                connection = connect_database()
                try:
                    cursor = connection.cursor()
                    cursor.execute(
                        """
                        INSERT INTO buku_digital
                            (judul_buku, penulis, penerbit, sinopsis, file_data,
                             cover_data, tgl_diunggah, jumlah_stok)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
                        """,
                        (
                            title, fields["penulis"].get().strip(),
                            fields["penerbit"].get().strip(),
                            synopsis.get("1.0", "end-1c").strip(),
                            file_data,
                            cover_data,
                            stock,
                        ),
                    )
                    connection.commit()
                finally:
                    connection.close()
            except (OSError, ValueError, mysql.connector.Error) as error:
                messagebox.showerror("Gagal menyimpan buku", str(error))
                return
            for entry in fields.values():
                entry.delete(0, tk.END)
            synopsis.delete("1.0", tk.END)
            for key in paths:
                paths[key] = ""
                selected_labels[key].configure(text="Belum dipilih", fg=MUTED)
            self.load_admin_books()
            messagebox.showinfo(
                "Berhasil", "Buku dan isi PDF berhasil disimpan di database."
            )

        self.make_button(form, "Simpan buku", save_book, primary=True).grid(
            row=8, column=1, sticky="w", padx=(16, 0), pady=(20, 0)
        )
