"""Backward-compatible launcher for the Ruang Baca application."""

from app import ELibraryApp
from database import connect_database, get_books, setup_database, update_loan
from main import main

__all__ = [
    "ELibraryApp",
    "connect_database",
    "get_books",
    "main",
    "setup_database",
    "update_loan",
]


if __name__ == "__main__":
    raise SystemExit(main())
