import os
from datetime import date, timedelta
from pathlib import Path

import mysql.connector


def connect_database():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        connection_timeout=int(os.environ.get("MYSQL_CONNECT_TIMEOUT", "5")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "db_perpustakaan_digital"),
    )


def setup_database():
    os.makedirs("uploads/books", exist_ok=True)
    os.makedirs("uploads/covers", exist_ok=True)
    connection = connect_database()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'buku_digital'
              AND COLUMN_NAME IN ('cover_buku', 'file_data')
            """,
            (connection.database,),
        )
        columns = {row[0] for row in cursor.fetchall()}
        if "cover_buku" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital ADD COLUMN cover_buku VARCHAR(500) NULL"
            )
        if "file_data" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital ADD COLUMN file_data LONGBLOB NULL"
            )
        cursor.execute("SELECT id_pengguna, nama_pengguna, peran FROM pengguna LIMIT 0")
        cursor.execute("SELECT id_buku, judul_buku FROM buku_digital LIMIT 0")
        cursor.execute("SELECT id_pinjam, id_pengguna, id_buku FROM peminjaman LIMIT 0")
        connection.commit()
    finally:
        connection.close()


def get_books(user_id=None):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT b.id_buku, b.judul_buku, b.penulis, b.penerbit,
                   b.tautan_file, b.cover_buku, b.tgl_diunggah,
                   CASE p.status
                       WHEN 'Aktif' THEN 'Dipinjam'
                       WHEN 'Kembali' THEN 'Dikembalikan'
                   END AS status,
                   p.tenggat_waktu
            FROM buku_digital AS b
            LEFT JOIN peminjaman AS p
              ON p.id_buku = b.id_buku
             AND p.id_pengguna = %s
             AND p.status = 'Aktif'
            ORDER BY b.tgl_diunggah DESC, b.id_buku DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def replace_book_pdf(book_id, source_path):
    source = Path(source_path)
    if source.suffix.lower() != ".pdf":
        raise ValueError("Select a PDF file.")
    if not source.is_file():
        raise FileNotFoundError(f"PDF file not found: {source}")
    save_book_file(book_id, source.read_bytes())


def save_book_file(book_id, file_data):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE buku_digital
            SET file_data = %s, tautan_file = NULL
            WHERE id_buku = %s
            """,
            (file_data, book_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Book {book_id} was not found.")
        connection.commit()
    finally:
        connection.close()


def get_book_file(book_id):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT file_data, tautan_file FROM buku_digital WHERE id_buku = %s",
            (book_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Book {book_id} was not found.")
        return row[0], row[1]
    finally:
        connection.close()


def update_loan(user_id, book_id, action):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        if action == "borrow":
            cursor.execute(
                "SELECT 1 FROM peminjaman WHERE id_pengguna = %s "
                "AND id_buku = %s AND status = 'Aktif'",
                (user_id, book_id),
            )
            active_loans = cursor.fetchall()
            if active_loans:
                return False, "Buku ini sudah ada di daftar pinjaman Anda."
            due_date = (date.today() + timedelta(days=7)).isoformat()
            cursor.execute(
                """
                INSERT INTO peminjaman
                    (id_pengguna, id_buku, status, tenggat_waktu)
                VALUES (%s, %s, 'Aktif', %s)
                """,
                (user_id, book_id, due_date),
            )
            message = f"Buku berhasil dipinjam hingga {due_date}."
        else:
            cursor.execute(
                """
                UPDATE peminjaman SET status = 'Kembali'
                WHERE id_pengguna = %s AND id_buku = %s AND status = 'Aktif'
                """,
                (user_id, book_id),
            )
            if cursor.rowcount == 0:
                return False, "Pinjaman aktif tidak ditemukan."
            message = "Buku berhasil dikembalikan."
        connection.commit()
        return True, message
    finally:
        connection.close()
