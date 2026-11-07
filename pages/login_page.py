import tkinter as tk
from tkinter import messagebox

import mysql.connector

from database import authenticate_user, register_user
from ui_theme import (
    ACCENT,
    ACCENT_LIGHT,
    BORDER,
    MUTED,
    PANEL,
    PANEL_LIGHT,
    TEXT,
)


class LoginPageMixin:
    def show_login_screen(self):
        self.clear_container()
        self.container.configure(bg=PANEL)
        left = tk.Frame(self.container, bg=PANEL)
        left.place(relx=0, rely=0, relwidth=0.56, relheight=1)
        right = tk.Frame(self.container, bg=ACCENT_LIGHT)
        right.place(relx=0.56, rely=0, relwidth=0.44, relheight=1)
        tk.Label(
            left, text="ERAUTAMA", bg=PANEL, fg=TEXT,
            font=(self.font_display, 16, "bold"),
        ).place(x=30, y=24)
        tk.Label(
            left, text="PERPUSTAKAAN DIGITAL", bg=PANEL, fg=ACCENT,
            font=(self.font_body, 8, "bold"),
        ).place(x=30, y=49)

        library_art = tk.Canvas(
            right, bg=ACCENT_LIGHT, highlightthickness=0, bd=0,
        )
        library_art.pack(fill="both", expand=True)

        def draw_library_art(event):
            canvas = event.widget
            canvas.delete("all")
            width, height = event.width, event.height
            canvas.create_text(
                width // 2, int(height * 0.19),
                text="Temukan cerita\nbaru di sini",
                fill=TEXT, font=(self.font_display, 24, "bold"),
                justify="center",
            )
            canvas.create_text(
                width // 2, int(height * 0.30),
                text="Koleksi bacaan, siap menemani hari Anda.",
                fill=MUTED, font=(self.font_body, 9),
                width=max(180, width - 48),
            )
            colors = ["#6677df", "#e79a76", "#45b889", "#d9b35f",
                      "#7d6bb5", "#5b9ab2", "#db7d91"]
            shelf_left, shelf_right = 28, width - 28
            book_rows = (
                (int(height * 0.52), 92),
                (int(height * 0.73), 102),
            )
            for shelf_y, book_height in book_rows:
                x = shelf_left
                while x < shelf_right - 24:
                    book_width = 23 + (len(colors) * (x // 23) % 17)
                    if x + book_width > shelf_right:
                        book_width = shelf_right - x
                    canvas.create_rectangle(
                        x, shelf_y - book_height, x + book_width, shelf_y,
                        fill=colors[(x // 23) % len(colors)],
                        outline="",
                    )
                    canvas.create_line(
                        x + book_width // 2, shelf_y - book_height + 12,
                        x + book_width // 2, shelf_y - 10,
                        fill="#ffffff",
                    )
                    x += book_width + 5
                canvas.create_rectangle(
                    shelf_left - 8, shelf_y, shelf_right + 8, shelf_y + 9,
                    fill="#4a4b60", outline="",
                )
            canvas.create_text(
                width // 2, int(height * 0.87),
                text="Baca. Jelajahi. Temukan.",
                fill=ACCENT, font=(self.font_body, 12, "bold"),
            )

        library_art.bind("<Configure>", draw_library_art)

        center = tk.Frame(left, bg=PANEL, width=330)
        center.place(relx=0.5, rely=0.53, anchor="center", width=330)
        tk.Label(
            center, text="Selamat datang", bg=PANEL, fg=TEXT,
            font=(self.font_display, 25, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            center, text="Masuk dengan NIM atau buat akun siswa.",
            bg=PANEL, fg=MUTED, font=(self.font_body, 9),
        ).pack(anchor="w", pady=(0, 18))

        forms = tk.Frame(center, bg=PANEL)
        forms.pack(fill="x")
        forms.grid_columnconfigure(0, weight=1)
        login_form = tk.Frame(forms, bg=PANEL)
        signup_form = tk.Frame(forms, bg=PANEL)
        login_form.grid(row=0, column=0, sticky="ew")

        login_nim = self.add_auth_field(login_form, "NIM")
        login_password = self.add_auth_field(login_form, "Password", password=True)
        self.make_button(
            login_form, "Masuk", self.login_with_password, primary=True,
        ).pack(fill="x", pady=(16, 8))
        tk.Button(
            login_form, text="Belum punya akun? Daftar",
            command=lambda: self.show_auth_form(signup_form, login_form),
            bg=PANEL, fg=ACCENT,
            activebackground=PANEL, activeforeground=TEXT,
            relief="flat", bd=0, cursor="hand2", font=(self.font_body, 9),
        ).pack(anchor="w")
        login_form.bind(
            "<Return>",
            lambda _event: self.login_with_password(login_nim, login_password),
        )
        login_nim.bind(
            "<Return>", lambda _event: login_password.focus_set()
        )
        login_password.bind(
            "<Return>",
            lambda _event: self.login_with_password(login_nim, login_password),
        )
        self.login_nim_entry = login_nim
        self.login_password_entry = login_password
        self.login_form = login_form

        signup_nim = self.add_auth_field(signup_form, "NIM")
        signup_name = self.add_auth_field(signup_form, "Nama lengkap")
        signup_password = self.add_auth_field(
            signup_form, "Password (minimal 8 karakter)", password=True,
        )
        signup_confirmation = self.add_auth_field(
            signup_form, "Ulangi password", password=True,
        )
        self.make_button(
            signup_form,
            "Buat akun siswa",
            lambda: self.create_account(
                signup_nim, signup_name, signup_password, signup_confirmation
            ),
            primary=True,
        ).pack(fill="x", pady=(16, 8))
        tk.Button(
            signup_form, text="Sudah punya akun? Masuk",
            command=lambda: self.show_auth_form(login_form, signup_form),
            bg=PANEL, fg=ACCENT,
            activebackground=PANEL, activeforeground=TEXT,
            relief="flat", bd=0, cursor="hand2", font=(self.font_body, 9),
        ).pack(anchor="w")
        signup_confirmation.bind(
            "<Return>",
            lambda _event: self.create_account(
                signup_nim, signup_name, signup_password, signup_confirmation
            ),
        )
        self.signup_form = signup_form
        login_nim.focus_set()

    @staticmethod
    def show_auth_form(active_form, inactive_form):
        inactive_form.grid_remove()
        active_form.grid(row=0, column=0, sticky="ew")

    def add_auth_field(self, parent, label, *, password=False):
        field = tk.Frame(parent, bg=PANEL)
        field.pack(fill="x", pady=6)
        tk.Label(
            field, text=label, bg=PANEL, fg=TEXT,
            font=(self.font_body, 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        entry = tk.Entry(
            field,
            bg=PANEL_LIGHT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=(self.font_body, 10),
            width=34,
            show="*" if password else "",
        )
        entry.pack(fill="x", ipady=10, padx=1)
        return entry

    def login_with_password(self, nim_entry=None, password_entry=None):
        nim_entry = nim_entry or self.login_nim_entry
        password_entry = password_entry or self.login_password_entry
        nim = nim_entry.get().strip()
        password = password_entry.get()
        if not nim or not password:
            messagebox.showwarning("Data belum lengkap", "Masukkan NIM dan password.")
            return
        try:
            user = authenticate_user(nim, password)
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error))
            return
        if user is None:
            messagebox.showerror(
                "Gagal masuk", "NIM atau password salah. Periksa kembali data Anda."
            )
            return
        self.login(user)

    def login(self, user):
        self.current_user_id, self.current_user_name, self.current_user_role = user
        self.search_var.set("")
        if self.current_user_role == "Admin-CRUD":
            self.show_admin_dashboard()
        else:
            self.show_student_dashboard()

    def create_account(self, nim_entry, name_entry, password_entry, confirmation_entry):
        nim = nim_entry.get().strip()
        name = name_entry.get().strip()
        password = password_entry.get()
        confirmation = confirmation_entry.get()
        if password != confirmation:
            messagebox.showerror("Password tidak cocok", "Ulangi password dengan benar.")
            return
        try:
            register_user(nim, name, password)
        except ValueError as error:
            messagebox.showerror("Tidak dapat membuat akun", str(error))
            return
        except mysql.connector.Error as error:
            messagebox.showerror("Kesalahan database", str(error))
            return

        self.login_nim_entry.delete(0, tk.END)
        self.login_nim_entry.insert(0, nim)
        self.login_password_entry.delete(0, tk.END)
        self.show_auth_form(self.login_form, self.signup_form)
        for entry in (nim_entry, name_entry, password_entry, confirmation_entry):
            entry.delete(0, tk.END)
        messagebox.showinfo(
            "Akun dibuat", "Akun siswa berhasil dibuat. Silakan masuk dengan NIM dan password."
        )
