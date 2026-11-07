import tkinter as tk
from tkinter import messagebox

import mysql.connector

from database import authenticate_user, register_user
from ui_theme import ACCENT, BACKGROUND, MUTED, PANEL, PANEL_LIGHT, TEXT


class LoginPageMixin:
    def show_login_screen(self):
        self.clear_container()
        center = tk.Frame(self.container, bg=BACKGROUND)
        center.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            center, text="RUANG BACA", bg=BACKGROUND, fg=ACCENT,
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(0, 10))
        tk.Label(
            center, text="Perpustakaan digital Anda",
            bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 25, "bold"),
        ).pack()
        tk.Label(
            center, text="Masuk dengan NIM atau buat akun siswa baru.",
            bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 10),
        ).pack(pady=(8, 20))

        forms = tk.Frame(center, bg=BACKGROUND)
        forms.pack(fill="x")
        forms.grid_columnconfigure(0, weight=1)
        login_form = tk.Frame(forms, bg=BACKGROUND)
        signup_form = tk.Frame(forms, bg=BACKGROUND)
        login_form.grid(row=0, column=0, sticky="ew")

        login_nim = self.add_auth_field(login_form, "NIM")
        login_password = self.add_auth_field(login_form, "Password", password=True)
        self.make_button(
            login_form, "Masuk", self.login_with_password, primary=True,
        ).pack(fill="x", pady=(16, 8))
        tk.Button(
            login_form, text="Belum punya akun? Daftar",
            command=lambda: self.show_auth_form(signup_form, login_form),
            bg=BACKGROUND, fg=ACCENT,
            activebackground=BACKGROUND, activeforeground=TEXT,
            relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9),
        ).pack()
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
            bg=BACKGROUND, fg=ACCENT,
            activebackground=BACKGROUND, activeforeground=TEXT,
            relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9),
        ).pack()
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

    @staticmethod
    def add_auth_field(parent, label, *, password=False):
        field = tk.Frame(parent, bg=BACKGROUND)
        field.pack(fill="x", pady=5)
        tk.Label(
            field, text=label, bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 5))
        entry = tk.Entry(
            field,
            bg=PANEL if password else PANEL_LIGHT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            width=38,
            show="*" if password else "",
        )
        entry.pack(fill="x", ipady=9, padx=1)
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
