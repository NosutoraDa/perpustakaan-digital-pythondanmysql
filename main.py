import sys
import tkinter as tk
from tkinter import messagebox

import mysql.connector

from app import ELibraryApp
from database import setup_database


def main():
    try:
        setup_database()
        app = ELibraryApp()
    except (mysql.connector.Error, ValueError) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database setup failed",
            "Could not prepare the library database. Make sure MySQL/MariaDB "
            "is running, the SQL dump has been imported, and the MYSQL_HOST, "
            "MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE "
            "settings are correct.\n\n"
            f"Details: {error}",
            parent=root,
        )
        root.destroy()
        return 1

    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
