import tkinter as tk

from database import connect_database
from ui_theme import ACCENT, BACKGROUND, MUTED, TEXT


class LoginPageMixin:
    def show_login_screen(self):
        self.clear_container()
        center = tk.Frame(self.container, bg=BACKGROUND)
        center.place(relx=0.5, rely=0.48, anchor="center")
        tk.Label(
            center, text="RUANG BACA", bg=BACKGROUND, fg=ACCENT,
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(0, 10))
        tk.Label(
            center, text="Perpustakaan digital Anda",
            bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 25, "bold"),
        ).pack()
        tk.Label(
            center, text="Pilih akun untuk mulai menjelajah koleksi.",
            bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 10),
        ).pack(pady=(8, 24))
        connection = connect_database()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id_pengguna, nama_pengguna, peran FROM pengguna "
                "ORDER BY CASE peran WHEN 'Admin-CRUD' THEN 0 ELSE 1 END, "
                "nama_pengguna"
            )
            users = cursor.fetchall()
        finally:
            connection.close()
        for user in users:
            self.make_button(
                center,
                f"{user[1]}   ·   {user[2]}",
                lambda selected=user: self.login(selected),
                primary=user[2] != "Admin-CRUD",
            ).pack(fill="x", pady=5)

    def login(self, user):
        self.current_user_id, self.current_user_name, self.current_user_role = user
        self.search_var.set("")
        if self.current_user_role == "Admin-CRUD":
            self.show_admin_dashboard()
        else:
            self.show_student_dashboard()
