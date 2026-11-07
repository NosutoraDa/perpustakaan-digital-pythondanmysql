import base64
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import mysql.connector

from database import (
    connect_database,
    create_tag,
    delete_tag,
    get_admin_book,
    get_book_tags,
    get_users,
    rename_tag,
    replace_book_pdf,
    update_book_details,
    update_user_account,
    update_book_stock,
)
from ui_theme import (
    ACCENT,
    BACKGROUND,
    BORDER,
    MUTED,
    PANEL,
    PANEL_LIGHT,
    ROW_ALT,
    TEXT,
)

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class AdminPageMixin:
    def show_admin_dashboard(self):
        self.clear_container()
        self.build_header()
        self.admin_views = {
            "Data Buku": tk.Frame(
                self.workspace, bg=PANEL, highlightthickness=1,
                highlightbackground=BORDER,
            ),
            "Pengguna": tk.Frame(
                self.workspace, bg=PANEL, highlightthickness=1,
                highlightbackground=BORDER,
            ),
        }
        for label in self.admin_views:
            self.add_sidebar_item(
                label,
                lambda selected=label: self.show_admin_view(selected),
                selected=label == "Data Buku",
            )
        catalogue = self.admin_views["Data Buku"]
        users = self.admin_views["Pengguna"]
        self.build_admin_catalogue(catalogue)
        self.build_user_management(users)
        self.show_admin_view("Data Buku")

    def show_admin_view(self, label):
        for frame in self.admin_views.values():
            frame.pack_forget()
        self.admin_views[label].pack(fill="both", expand=True)
        self.select_sidebar_item(label)

    def build_admin_catalogue(self, parent):
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x", padx=20, pady=(18, 12))
        tk.Label(
            top, text="Data Buku", bg=PANEL, fg=TEXT,
            font=(self.font_display, 18, "bold"),
        ).pack(side="left")
        self.make_button(
            top, "Kelola buku terpilih", self.edit_selected_book,
        ).pack(side="right", padx=(8, 0))
        self.make_button(
            top, "Tambah buku", self.build_book_form,
            primary=True,
        ).pack(side="right")
        columns = ("id", "judul", "penulis", "penerbit", "stok", "tanggal")
        table = tk.Frame(parent, bg=PANEL)
        table.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        self.book_tree = ttk.Treeview(
            table, columns=columns, show="headings", style="Library.Treeview",
        )
        for key, label, width in (
            ("id", "ID", 55), ("judul", "Judul", 220),
            ("penulis", "Penulis", 145), ("penerbit", "Penerbit", 145),
            ("stok", "Salinan", 75), ("tanggal", "Tanggal unggah", 120),
        ):
            self.book_tree.heading(key, text=label)
            self.book_tree.column(
                key, width=width, minwidth=45, anchor="w", stretch=key == "judul",
            )
        vertical = ttk.Scrollbar(
            table, orient="vertical", command=self.book_tree.yview,
            style="Library.Vertical.TScrollbar",
        )
        horizontal = ttk.Scrollbar(
            table, orient="horizontal", command=self.book_tree.xview,
            style="Library.Horizontal.TScrollbar",
        )
        self.book_tree.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set,
        )
        self.book_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        self.load_admin_books()

    def load_admin_books(self):
        for item in self.book_tree.get_children():
            self.book_tree.delete(item)
        connection = connect_database()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id_buku, judul_buku, penulis, penerbit, jumlah_stok, "
                "tgl_diunggah "
                "FROM buku_digital ORDER BY id_buku DESC"
            )
            rows = cursor.fetchall()
        finally:
            connection.close()
        for index, row in enumerate(rows):
            self.book_tree.insert(
                "", "end", iid=str(row[0]), values=row,
                tags=("alternate" if index % 2 else "normal",),
            )
        self.book_tree.tag_configure("alternate", background=ROW_ALT)
        self.book_tree.tag_configure("normal", background=PANEL)
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
            assigned_tags = get_book_tags(int(selection[0]))
            available_tags = assigned_tags
        except (ValueError, mysql.connector.Error) as error:
            messagebox.showerror("Gagal membuka buku", str(error))
            return

        dialog = tk.Toplevel(self)
        dialog.title("Ubah detail buku")
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("760x600")
        self.center_popup(dialog)
        body = tk.Frame(dialog, bg=PANEL, padx=22, pady=18)
        body.pack(fill="both", expand=True)
        cover_frame = tk.Frame(body, bg=PANEL_LIGHT, width=205, height=270)
        cover_frame.grid(row=0, column=0, sticky="nw", padx=(0, 22))
        cover_frame.grid_propagate(False)
        cover_preview = tk.Label(
            cover_frame, text="Sampul belum dipilih",
            bg=PANEL_LIGHT, fg=MUTED, wraplength=175,
            font=(self.font_body, 10),
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
                    image.thumbnail((205, 270))
                    photo = ImageTk.PhotoImage(image)
                else:
                    photo = tk.PhotoImage(data=base64.b64encode(data).decode("ascii"))
                    factor = max(
                        1,
                        (photo.width() + 204) // 205,
                        (photo.height() + 269) // 270,
                    )
                    photo = photo.subsample(factor, factor)
                cover_state["image"] = photo
                cover_preview.configure(image=photo, text="")
            except (OSError, tk.TclError):
                cover_preview.configure(
                    image="", text="Format sampul tidak dapat ditampilkan"
                )

        details = tk.Frame(body, bg=PANEL)
        details.grid(row=0, column=1, rowspan=2, sticky="nsew")
        fields = {}
        for row, (label, value) in enumerate(
            (
                ("Judul", book[1] or ""),
                ("Penulis", book[2] or ""),
                ("Penerbit", book[3] or ""),
            )
        ):
            tk.Label(
                details, text=label, bg=PANEL, fg=MUTED,
                font=(self.font_body, 9),
            ).grid(row=row, column=0, sticky="w", pady=4)
            entry = tk.Entry(
                details, bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                relief="flat", font=(self.font_body, 10),
            )
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), ipady=7)
            fields[label] = entry

        tk.Label(
            details, text="Deskripsi materi pembelajaran",
            bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=3, column=0, sticky="nw", pady=6)
        synopsis_frame = tk.Frame(details, bg=PANEL_LIGHT)
        synopsis_frame.grid(
            row=3, column=1, sticky="nsew", padx=(12, 0), pady=4
        )
        synopsis = tk.Text(
            synopsis_frame, height=9, wrap="word", bg=PANEL_LIGHT,
            fg=TEXT, insertbackground=TEXT, relief="flat",
            font=(self.font_body, 10),
        )
        synopsis_scrollbar = ttk.Scrollbar(
            synopsis_frame, orient="vertical", command=synopsis.yview,
        )
        synopsis.configure(yscrollcommand=synopsis_scrollbar.set)
        synopsis.insert("1.0", book[4] or "")
        synopsis.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        synopsis_scrollbar.pack(side="right", fill="y")
        tk.Label(
            details, text="Tag materi", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=4, column=0, sticky="nw", pady=6)
        tag_frame = tk.Frame(details, bg=PANEL)
        tag_frame.grid(row=4, column=1, sticky="nsew", padx=(12, 0), pady=4)
        tag_listbox = tk.Listbox(
            tag_frame,
            selectmode="extended",
            height=3,
            bg=PANEL_LIGHT,
            fg=TEXT,
            relief="flat",
            exportselection=False,
            font=(self.font_body, 9),
        )
        tag_scrollbar = ttk.Scrollbar(
            tag_frame, orient="vertical", command=tag_listbox.yview,
        )
        tag_listbox.configure(yscrollcommand=tag_scrollbar.set)
        tag_list_frame = tk.Frame(tag_frame, bg=PANEL)
        tag_list_frame.pack(fill="both", expand=True)
        tag_listbox.pack(in_=tag_list_frame, side="left", fill="both", expand=True)
        tag_scrollbar.pack(in_=tag_list_frame, side="right", fill="y")

        def refresh_tag_choices(select_name=None):
            nonlocal available_tags
            selected_ids = {
                available_tags[index][0]
                for index in tag_listbox.curselection()
            }
            available_tags = get_book_tags(int(book[0]))
            tag_listbox.delete(0, tk.END)
            for tag_id, name in available_tags:
                tag_listbox.insert(tk.END, name)
                if name == select_name or tag_id in selected_ids:
                    tag_listbox.selection_set(tk.END)

        def selected_tag_names():
            return [
                tag_listbox.get(index)
                for index in tag_listbox.curselection()
            ]

        refresh_tag_choices()
        for tag in assigned_tags:
            name = tag[1]
            for index in range(tag_listbox.size()):
                if tag_listbox.get(index) == name:
                    tag_listbox.selection_set(index)
                    break

        self.make_button(
            tag_frame, "Kelola tag", lambda: self.manage_book_tags(
                dialog, int(book[0]), refresh_tag_choices
            ),
        ).pack(anchor="e", pady=(5, 0))
        cover_actions = tk.Frame(body, bg=PANEL)
        cover_actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))

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

        book_actions = tk.Frame(body, bg=PANEL)
        book_actions.grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0)
        )
        book_stock_label = tk.Label(
            book_actions,
            text=f"Stok: {book[6]} salinan",
            bg=PANEL, fg=MUTED, font=(self.font_body, 9),
        )
        book_stock_label.pack(side="left", padx=(0, 10))

        def change_book_stock():
            updated_stock = self.change_selected_book_stock(
                book_id=int(book[0]),
                current_stock=int(book[6]),
                parent=dialog,
            )
            if updated_stock is None:
                return
            book_stock_label.configure(
                text=f"Stok: {updated_stock} salinan"
            )

        self.make_button(
            book_actions, "Ubah stok", change_book_stock,
        ).pack(side="left", padx=3)
        self.make_button(
            book_actions, "Ganti PDF",
            lambda: self.replace_selected_book_pdf(
                book_id=int(book[0]), parent=dialog
            ),
        ).pack(side="left", padx=3)
        self.make_button(
            book_actions, "Hapus buku",
            lambda: self.delete_selected_book(
                book_id=int(book[0]), parent=dialog
            ),
        ).pack(side="left", padx=3)
        actions = tk.Frame(body, bg=PANEL)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        details.grid_columnconfigure(1, weight=1)
        details.grid_rowconfigure(3, weight=1)

        def save_details():
            try:
                message = update_book_details(
                    int(book[0]),
                    fields["Judul"].get(),
                    fields["Penulis"].get(),
                    fields["Penerbit"].get(),
                    synopsis.get("1.0", "end-1c"),
                    cover_state["data"],
                    selected_tag_names(),
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

    def manage_book_tags(self, parent, book_id, on_change):
        manager = tk.Toplevel(parent)
        manager.title("Kelola tag materi")
        manager.configure(bg=PANEL)
        manager.transient(parent)
        manager.grab_set()
        manager.geometry("420x460")
        self.center_popup(manager)

        content = tk.Frame(manager, bg=PANEL, padx=20, pady=18)
        content.pack(fill="both", expand=True)
        tk.Label(
            content, text="Tag materi pembelajaran", bg=PANEL, fg=TEXT,
            font=(self.font_body, 14, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        tk.Label(
            content,
            text="Tag disimpan khusus untuk buku ini.",
            bg=PANEL, fg=MUTED, font=(self.font_body, 9),
        ).pack(anchor="w", pady=(0, 12))

        list_frame = tk.Frame(content, bg=PANEL_LIGHT)
        list_frame.pack(fill="both", expand=True)
        tags_list = tk.Listbox(
            list_frame, exportselection=False, bg=PANEL_LIGHT, fg=TEXT,
            relief="flat", font=(self.font_body, 10),
        )
        tag_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=tags_list.yview,
        )
        tags_list.configure(yscrollcommand=tag_scrollbar.set)
        tags_list.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        tag_scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)
        manager_tags = []

        name_entry = tk.Entry(
            content, bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=(self.font_body, 10),
        )
        name_entry.pack(fill="x", pady=(12, 8), ipady=7)

        def refresh_manager(select_name=None):
            nonlocal manager_tags
            manager_tags = get_book_tags(book_id)
            tags_list.delete(0, tk.END)
            for tag in manager_tags:
                name = tag[1]
                tags_list.insert(tk.END, name)
                if name == select_name:
                    tags_list.selection_set(tk.END)
                    tags_list.see(tk.END)
            on_change(select_name)

        def selected_tag():
            selection = tags_list.curselection()
            if not selection:
                messagebox.showwarning(
                    "Pilih tag", "Pilih tag yang ingin diubah.", parent=manager
                )
                return None
            name = tags_list.get(selection[0])
            return next(
                ((tag_id, tag_name) for tag_id, tag_name in manager_tags
                 if tag_name == name),
                None,
            )

        def run_tag_change(operation, success_message, select_name=None):
            try:
                operation()
                refresh_manager(select_name)
                messagebox.showinfo(
                    "Berhasil", success_message, parent=manager
                )
            except (ValueError, mysql.connector.Error) as error:
                messagebox.showerror(
                    "Tag tidak dapat diperbarui", str(error), parent=manager
                )

        def copy_selected_tag_name(_event=None):
            selection = tags_list.curselection()
            if selection:
                name_entry.delete(0, tk.END)
                name_entry.insert(0, tags_list.get(selection[0]))

        tags_list.bind("<<ListboxSelect>>", copy_selected_tag_name)

        def add_tag():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning(
                    "Nama tag kosong", "Masukkan nama tag.", parent=manager
                )
                return
            run_tag_change(
                lambda: create_tag(book_id, name),
                "Tag berhasil ditambahkan.",
                select_name=name,
            )
            name_entry.delete(0, tk.END)

        def rename_selected_tag():
            selected = selected_tag()
            name = name_entry.get().strip()
            if selected is None:
                return
            if not name:
                messagebox.showwarning(
                    "Nama tag kosong", "Masukkan nama tag baru.", parent=manager
                )
                return
            run_tag_change(
                lambda: rename_tag(selected[0], name),
                "Tag berhasil diubah.",
                select_name=name,
            )
            name_entry.delete(0, tk.END)

        def delete_selected_tag():
            selected = selected_tag()
            if selected is None:
                return
            if not messagebox.askyesno(
                "Hapus tag",
                f'Hapus tag "{selected[1]}" dari buku ini?',
                parent=manager,
            ):
                return
            run_tag_change(
                lambda: delete_tag(selected[0]),
                "Tag berhasil dihapus.",
            )

        buttons = tk.Frame(content, bg=PANEL)
        buttons.pack(fill="x")
        self.make_button(buttons, "Tambah", add_tag, primary=True).pack(
            side="left"
        )
        self.make_button(
            buttons, "Ubah nama", rename_selected_tag,
        ).pack(side="left", padx=(7, 0))
        self.make_button(
            buttons, "Hapus", delete_selected_tag,
        ).pack(side="left", padx=(7, 0))
        self.make_button(
            buttons, "Tutup", manager.destroy,
        ).pack(side="right")
        refresh_manager()

    def change_selected_book_stock(
        self, book_id=None, current_stock=None, parent=None
    ):
        if book_id is None:
            selection = self.book_tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Pilih buku", "Pilih buku yang stoknya ingin diubah."
                )
                return None
            book_id = int(selection[0])
            values = self.book_tree.item(selection[0], "values")
            current_stock = int(values[4])
        if current_stock is None:
            messagebox.showwarning("Pilih buku", "Pilih buku yang stoknya ingin diubah.")
            return None
        parent = parent or self
        stock = simpledialog.askinteger(
            "Ubah stok buku",
            "Jumlah salinan yang dapat dipinjam bersamaan:",
            initialvalue=current_stock,
            minvalue=0,
            parent=parent,
        )
        if stock is None:
            return None

        try:
            success, message = update_book_stock(book_id, stock)
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error), parent=parent)
            return None
        if not success:
            messagebox.showwarning(
                "Stok tidak dapat diubah", message, parent=parent
            )
            return None
        self.load_admin_books()
        messagebox.showinfo("Berhasil", message, parent=parent)
        return stock

    def build_user_management(self, parent):
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x", padx=20, pady=(18, 14))
        tk.Label(
            top, text="Data Pengguna", bg=PANEL, fg=TEXT,
            font=(self.font_display, 18, "bold"),
        ).pack(side="left")
        self.make_button(
            top, "Kelola pengguna terpilih", self.edit_selected_user,
            primary=True,
        ).pack(side="right")
        columns = ("nim", "nama", "role", "status")
        table = tk.Frame(parent, bg=PANEL)
        table.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        self.user_tree = ttk.Treeview(
            table, columns=columns, show="headings", style="Library.Treeview",
        )
        for key, label, width in (
            ("nim", "NIM", 120),
            ("nama", "Nama", 180),
            ("role", "Peran", 125),
            ("status", "Akun", 150),
        ):
            self.user_tree.heading(key, text=label)
            self.user_tree.column(key, width=width, minwidth=80, anchor="w")
        vertical = ttk.Scrollbar(
            table, orient="vertical", command=self.user_tree.yview,
            style="Library.Vertical.TScrollbar",
        )
        horizontal = ttk.Scrollbar(
            table, orient="horizontal", command=self.user_tree.xview,
            style="Library.Horizontal.TScrollbar",
        )
        self.user_tree.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set,
        )
        self.user_tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        self.load_users()

    def load_users(self):
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        for index, user in enumerate(get_users()):
            status = "Siap masuk" if user[4] else "Belum mengatur password"
            self.user_tree.insert(
                "", "end", iid=str(user[0]),
                values=(user[1], user[2], user[3], status),
                tags=("alternate" if index % 2 else "normal",),
            )
        self.user_tree.tag_configure("alternate", background=ROW_ALT)
        self.user_tree.tag_configure("normal", background=PANEL)
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
        self.center_popup(dialog)
        body = tk.Frame(dialog, bg=PANEL, padx=26, pady=24)
        body.pack(fill="both", expand=True)
        tk.Label(
            body, text="Data pengguna", bg=PANEL, fg=TEXT,
            font=(self.font_body, 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        for row, (label, value) in enumerate(
            (("NIM", values[0]), ("Nama", values[1]), ("Status akun", values[3])),
            start=1,
        ):
            tk.Label(
                body, text=label, bg=PANEL, fg=MUTED,
                font=(self.font_body, 9),
            ).grid(row=row, column=0, sticky="w", pady=8)
            tk.Label(
                body, text=value, bg=PANEL, fg=TEXT,
                font=(self.font_body, 10),
            ).grid(row=row, column=1, sticky="w", padx=(18, 0), pady=8)

        tk.Label(
            body, text="Peran", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=4, column=0, sticky="w", pady=8)
        role = tk.StringVar(value=values[2])
        role_picker = ttk.Combobox(
            body, textvariable=role, state="readonly",
            values=("Admin-CRUD", "Siswa-Rent"),
        )
        role_picker.grid(row=4, column=1, sticky="ew", padx=(18, 0), pady=8)

        tk.Label(
            body, text="Password baru", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=5, column=0, sticky="w", pady=8)
        password = tk.Entry(
            body, show="*", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=(self.font_body, 10),
        )
        password.grid(row=5, column=1, sticky="ew", padx=(18, 0), ipady=7)
        tk.Label(
            body, text="Ulangi password", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=6, column=0, sticky="w", pady=8)
        confirmation = tk.Entry(
            body, show="*", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=(self.font_body, 10),
        )
        confirmation.grid(
            row=6, column=1, sticky="ew", padx=(18, 0), ipady=7
        )
        tk.Label(
            body, text="Kosongkan password jika tidak ingin mereset.",
            bg=PANEL, fg=MUTED, font=(self.font_body, 8),
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

    def delete_selected_book(self, book_id=None, parent=None):
        if book_id is None:
            selection = self.book_tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Pilih buku", "Pilih buku yang ingin dihapus."
                )
                return
            book_id = int(selection[0])
        parent = parent or self
        if not messagebox.askyesno(
            "Hapus buku", "Hapus buku ini dari katalog?", parent=parent
        ):
            return
        connection = connect_database()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM buku_digital WHERE id_buku = %s", (book_id,)
            )
            connection.commit()
        except mysql.connector.IntegrityError:
            messagebox.showerror(
                "Buku memiliki riwayat",
                "Buku yang pernah dipinjam tidak dapat dihapus agar riwayat tetap tersimpan.",
                parent=parent,
            )
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error), parent=parent)
        else:
            self.load_admin_books()
            if isinstance(parent, tk.Toplevel):
                parent.destroy()

        finally:
            connection.close()

    def replace_selected_book_pdf(self, book_id=None, parent=None):
        if book_id is None:
            selection = self.book_tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Pilih buku", "Pilih buku yang PDF-nya ingin diganti."
                )
                return
            book_id = int(selection[0])
        parent = parent or self
        source_path = filedialog.askopenfilename(
            parent=parent,
            title="Pilih PDF pengganti",
            filetypes=(("PDF", "*.pdf"),),
        )
        if not source_path:
            return

        try:
            replace_book_pdf(book_id, source_path)
        except (OSError, ValueError, mysql.connector.Error) as error:
            messagebox.showerror(
                "Gagal mengganti PDF", str(error), parent=parent
            )
            return

        self.load_admin_books()
        messagebox.showinfo(
            "Berhasil",
            "PDF buku berhasil diganti. Metadata dan riwayat peminjaman tetap tersimpan.",
            parent=parent,
        )

    def build_book_form(self):
        dialog = tk.Toplevel(self)
        dialog.title("Tambah buku")
        dialog.configure(bg=PANEL)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("740x520")
        self.center_popup(dialog)
        form = tk.Frame(dialog, bg=PANEL, padx=24, pady=22)
        form.pack(fill="both", expand=True)
        tk.Label(
            form, text="Tambah Buku", bg=PANEL, fg=TEXT,
            font=(self.font_body, 16, "bold"),
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
                     font=(self.font_body, 9)).grid(row=row, column=0, sticky="w", pady=7)
            entry = tk.Entry(
                form, bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                relief="flat", font=(self.font_body, 10), width=38,
                highlightthickness=1, highlightbackground=BORDER,
                highlightcolor=ACCENT, bd=0,
            )
            entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(16, 0), ipady=8)
            fields[key] = entry
        tk.Label(
            form, text="Deskripsi materi pembelajaran", bg=PANEL, fg=MUTED,
            font=(self.font_body, 9),
        ).grid(row=5, column=0, sticky="nw", pady=8)
        synopsis = tk.Text(
            form, height=4, wrap="word", bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=(self.font_body, 10),
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
                     font=(self.font_body, 9)).grid(row=row, column=0, sticky="w", pady=8)
            selected_labels[key] = tk.Label(
                form, text="Belum dipilih", bg=PANEL, fg=MUTED,
                font=(self.font_body, 9), anchor="w",
            )
            selected_labels[key].grid(row=row, column=1, sticky="ew", padx=(16, 10))

            def choose_file(file_key=key, file_types=types):
                path = filedialog.askopenfilename(
                    parent=dialog, filetypes=file_types
                )
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
                    "Data belum lengkap", "Judul dan PDF buku wajib diisi.",
                    parent=dialog,
                )
                return
            try:
                stock = int(fields["stok"].get())
                if stock < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Stok tidak valid",
                    "Jumlah salinan harus bilangan bulat minimal 0.",
                    parent=dialog,
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
                messagebox.showerror(
                    "Gagal menyimpan buku", str(error), parent=dialog
                )
                return
            for entry in fields.values():
                entry.delete(0, tk.END)
            synopsis.delete("1.0", tk.END)
            for key in paths:
                paths[key] = ""
                selected_labels[key].configure(text="Belum dipilih", fg=MUTED)
            self.load_admin_books()
            dialog.destroy()
            messagebox.showinfo(
                "Berhasil", "Buku dan isi PDF berhasil disimpan di database.",
                parent=self,
            )

        actions = tk.Frame(form, bg=PANEL)
        actions.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(20, 0))
        self.make_button(actions, "Simpan buku", save_book, primary=True).pack(
            side="left"
        )
        self.make_button(actions, "Batal", dialog.destroy).pack(side="right")
