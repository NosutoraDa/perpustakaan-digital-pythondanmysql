import base64
import hashlib
import hmac
import os
import secrets
from datetime import date, timedelta
from pathlib import Path

import mysql.connector


PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_MIN_LENGTH = 8


def _hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_HASH_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def _verify_password(password, encoded_hash):
    try:
        algorithm, iterations, encoded_salt, encoded_digest = encoded_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt)
        expected_digest = base64.urlsafe_b64decode(encoded_digest)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual_digest, expected_digest)


def _validate_password(password):
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Kata sandi harus memiliki minimal {PASSWORD_MIN_LENGTH} karakter."
        )


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
    connection = connect_database()
    try:
        cursor = connection.cursor(buffered=True)
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'buku_digital'
              AND COLUMN_NAME IN (
                  'tautan_file', 'cover_buku', 'file_data', 'cover_data',
                  'jumlah_stok', 'sinopsis'
              )
            """,
            (connection.database,),
        )
        columns = {row[0] for row in cursor.fetchall()}
        _setup_user_passwords(connection, cursor)
        if "file_data" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital ADD COLUMN file_data LONGBLOB NULL"
            )
        if "cover_data" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital ADD COLUMN cover_data LONGBLOB NULL"
            )
        if "sinopsis" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital ADD COLUMN sinopsis TEXT NULL"
            )
        for path_column, blob_column in (
            ("tautan_file", "file_data"),
            ("cover_buku", "cover_data"),
        ):
            if path_column not in columns:
                continue
            cursor.execute(
                f"SELECT id_buku, {path_column} FROM buku_digital "
                f"WHERE {path_column} IS NOT NULL AND {blob_column} IS NULL"
            )
            for book_id, file_path in cursor.fetchall():
                source = Path(file_path)
                if not source.is_file():
                    raise ValueError(
                        f"Cannot migrate legacy {path_column} for book {book_id}: "
                        f"file not found at {source}. Restore the file or clear "
                        "its old path before starting the app."
                    )
                cursor.execute(
                    f"UPDATE buku_digital SET {blob_column} = %s "
                    "WHERE id_buku = %s",
                    (source.read_bytes(), book_id),
                )
            cursor.execute(f"ALTER TABLE buku_digital DROP COLUMN {path_column}")
        if "jumlah_stok" not in columns:
            cursor.execute(
                "ALTER TABLE buku_digital "
                "ADD COLUMN jumlah_stok INT NOT NULL DEFAULT 1"
            )
            cursor.execute(
                """
                UPDATE buku_digital AS b
                SET jumlah_stok = GREATEST(
                    jumlah_stok,
                    (
                        SELECT COUNT(*)
                        FROM peminjaman AS p
                        WHERE p.id_buku = b.id_buku AND p.status = 'Aktif'
                    )
                )
                """
            )
        cursor.execute("SELECT id_pengguna, nama_pengguna, peran FROM pengguna LIMIT 0")
        cursor.execute("SELECT id_buku, judul_buku FROM buku_digital LIMIT 0")
        cursor.execute("SELECT id_pinjam, id_pengguna, id_buku FROM peminjaman LIMIT 0")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tag_buku (
                id_tag INT NOT NULL AUTO_INCREMENT,
                nama_tag VARCHAR(60) NOT NULL,
                PRIMARY KEY (id_tag),
                UNIQUE KEY unik_nama_tag (nama_tag)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS buku_tag (
                id_buku INT NOT NULL,
                id_tag INT NOT NULL,
                PRIMARY KEY (id_buku, id_tag),
                CONSTRAINT fk_buku_tag_buku FOREIGN KEY (id_buku)
                    REFERENCES buku_digital (id_buku) ON DELETE CASCADE,
                CONSTRAINT fk_buku_tag_tag FOREIGN KEY (id_tag)
                    REFERENCES tag_buku (id_tag) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        _expire_overdue_loans(cursor)
        connection.commit()
    finally:
        connection.close()


def _expire_overdue_loans(cursor, today=None):
    cursor.execute(
        """
        UPDATE peminjaman
        SET status = 'Kembali'
        WHERE status = 'Aktif' AND tenggat_waktu <= %s
        """,
        (today or date.today(),),
    )
    return cursor.rowcount


def expire_overdue_loans():
    connection = connect_database()
    try:
        cursor = connection.cursor()
        expired_count = _expire_overdue_loans(cursor)
        connection.commit()
        return expired_count
    finally:
        connection.close()


def _setup_user_passwords(connection, cursor):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'pengguna'
          AND COLUMN_NAME = 'password_hash'
        """,
        (connection.database,),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE pengguna ADD COLUMN password_hash VARCHAR(255) NULL"
        )

    bootstrap_nim = os.environ.get("MYSQL_BOOTSTRAP_ADMIN_NIM", "").strip()
    bootstrap_password = os.environ.get("MYSQL_BOOTSTRAP_ADMIN_PASSWORD", "")
    if bool(bootstrap_nim) != bool(bootstrap_password):
        raise ValueError(
            "Set both MYSQL_BOOTSTRAP_ADMIN_NIM and "
            "MYSQL_BOOTSTRAP_ADMIN_PASSWORD to configure the initial admin."
        )
    if not bootstrap_nim:
        return
    _validate_password(bootstrap_password)

    cursor.execute(
        """
        SELECT id_pengguna, peran, password_hash
        FROM pengguna
        WHERE no_identitas = %s
        FOR UPDATE
        """,
        (bootstrap_nim,),
    )
    account = cursor.fetchone()
    if account is None or account[1] != "Admin-CRUD":
        raise ValueError(
            "MYSQL_BOOTSTRAP_ADMIN_NIM must match an existing admin account."
        )
    if account[2] is None:
        cursor.execute(
            "UPDATE pengguna SET password_hash = %s WHERE id_pengguna = %s",
            (_hash_password(bootstrap_password), account[0]),
        )
    elif not _verify_password(bootstrap_password, account[2]):
        raise ValueError(
            "The configured bootstrap password does not match the existing "
            "admin password. Remove the bootstrap variables after setup."
        )


def authenticate_user(nim, password):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id_pengguna, nama_pengguna, peran, password_hash
            FROM pengguna
            WHERE no_identitas = %s
            """,
            (nim.strip(),),
        )
        user = cursor.fetchone()
        if user is None or user[3] is None or not _verify_password(password, user[3]):
            return None
        return user[:3]
    finally:
        connection.close()


def register_user(nim, name, password):
    nim = nim.strip()
    name = name.strip()
    if not nim:
        raise ValueError("NIM wajib diisi.")
    if not name:
        raise ValueError("Nama wajib diisi.")
    _validate_password(password)

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id_pengguna, nama_pengguna, peran, password_hash
            FROM pengguna
            WHERE no_identitas = %s
            FOR UPDATE
            """,
            (nim,),
        )
        existing_user = cursor.fetchone()
        if existing_user is not None:
            raise ValueError(
                "NIM tersebut sudah terdaftar. Minta admin mengatur password "
                "akun lama Anda."
            )

        cursor.execute(
            """
            INSERT INTO pengguna
                (no_identitas, nama_pengguna, tgl_bergabung, peran, password_hash)
            VALUES (%s, %s, CURRENT_DATE, 'Siswa-Rent', %s)
            """,
            (nim, name, _hash_password(password)),
        )
        connection.commit()
        return name
    finally:
        connection.close()


def set_user_password(actor_id, target_id, password):
    _validate_password(password)
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT peran FROM pengguna WHERE id_pengguna = %s FOR UPDATE",
            (actor_id,),
        )
        actor = cursor.fetchone()
        if actor is None or actor[0] != "Admin-CRUD":
            return False, "Hanya admin yang dapat mengatur password pengguna."

        cursor.execute(
            "SELECT id_pengguna FROM pengguna WHERE id_pengguna = %s FOR UPDATE",
            (target_id,),
        )
        if cursor.fetchone() is None:
            return False, "Pengguna tidak ditemukan."

        cursor.execute(
            "UPDATE pengguna SET password_hash = %s WHERE id_pengguna = %s",
            (_hash_password(password), target_id),
        )
        connection.commit()
        return True, "Password pengguna berhasil diatur."
    finally:
        connection.close()


def get_users():
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id_pengguna, no_identitas, nama_pengguna, peran,
                   password_hash IS NOT NULL
            FROM pengguna
            ORDER BY nama_pengguna, no_identitas
            """
        )
        return cursor.fetchall()
    finally:
        connection.close()


def update_user_account(actor_id, target_id, role, password=None):
    if role not in ("Admin-CRUD", "Siswa-Rent"):
        raise ValueError("Peran pengguna tidak valid.")
    if password is not None:
        _validate_password(password)

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT peran FROM pengguna WHERE id_pengguna = %s FOR UPDATE",
            (actor_id,),
        )
        actor = cursor.fetchone()
        if actor is None or actor[0] != "Admin-CRUD":
            return False, "Hanya admin yang dapat mengubah akun pengguna."

        cursor.execute(
            "SELECT peran, password_hash FROM pengguna "
            "WHERE id_pengguna = %s FOR UPDATE",
            (target_id,),
        )
        target = cursor.fetchone()
        if target is None:
            return False, "Pengguna tidak ditemukan."
        if (
            role == "Admin-CRUD"
            and target[0] != "Admin-CRUD"
            and target[1] is None
            and password is None
        ):
            return False, (
                "Pengguna harus membuat akun dan password sebelum menjadi admin."
            )
        if target_id == actor_id and role != "Admin-CRUD":
            return False, "Gunakan akun admin lain untuk mengubah peran Anda."
        if role == "Siswa-Rent" and target[0] == "Admin-CRUD":
            cursor.execute(
                "SELECT id_pengguna FROM pengguna "
                "WHERE peran = 'Admin-CRUD' FOR UPDATE"
            )
            if len(cursor.fetchall()) <= 1:
                return False, "Admin terakhir tidak dapat diubah menjadi siswa."

        if password is None:
            cursor.execute(
                "UPDATE pengguna SET peran = %s WHERE id_pengguna = %s",
                (role, target_id),
            )
        else:
            cursor.execute(
                "UPDATE pengguna SET peran = %s, password_hash = %s "
                "WHERE id_pengguna = %s",
                (role, _hash_password(password), target_id),
            )
        connection.commit()
        return True, "Data pengguna berhasil diperbarui."
    finally:
        connection.close()


def set_user_role(actor_id, target_id, role):
    if role not in ("Admin-CRUD", "Siswa-Rent"):
        raise ValueError("Peran pengguna tidak valid.")

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT peran FROM pengguna WHERE id_pengguna = %s FOR UPDATE",
            (actor_id,),
        )
        actor = cursor.fetchone()
        if actor is None or actor[0] != "Admin-CRUD":
            return False, "Hanya admin yang dapat mengubah peran pengguna."

        cursor.execute(
            "SELECT peran, password_hash FROM pengguna "
            "WHERE id_pengguna = %s FOR UPDATE",
            (target_id,),
        )
        target = cursor.fetchone()
        if target is None:
            return False, "Pengguna tidak ditemukan."
        if target[0] == role:
            return True, "Peran pengguna tidak berubah."
        if role == "Admin-CRUD" and target[1] is None:
            return False, "Pengguna harus membuat akun dan password sebelum menjadi admin."
        if target_id == actor_id and role != "Admin-CRUD":
            return False, "Gunakan akun admin lain untuk mengubah peran Anda."

        if role == "Siswa-Rent" and target[0] == "Admin-CRUD":
            cursor.execute(
                "SELECT id_pengguna FROM pengguna "
                "WHERE peran = 'Admin-CRUD' FOR UPDATE"
            )
            if len(cursor.fetchall()) <= 1:
                return False, "Admin terakhir tidak dapat diubah menjadi siswa."

        cursor.execute(
            "UPDATE pengguna SET peran = %s WHERE id_pengguna = %s",
            (role, target_id),
        )
        connection.commit()
        return True, "Peran pengguna berhasil diperbarui."
    finally:
        connection.close()


def get_books(user_id=None):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        if _expire_overdue_loans(cursor):
            connection.commit()
        cursor.execute(
            """
            SELECT b.id_buku, b.judul_buku, b.penulis, b.penerbit,
                   b.cover_data,
                   b.tgl_diunggah,
                   CASE p.status
                       WHEN 'Aktif' THEN 'Dipinjam'
                       WHEN 'Kembali' THEN 'Dikembalikan'
                   END AS status,
                   p.tenggat_waktu,
                   b.jumlah_stok,
                   GREATEST(
                       b.jumlah_stok - COALESCE(inventory.borrowed_count, 0), 0
                   ) AS available_count,
                   b.sinopsis,
                   COALESCE(book_tags.tags, '')
            FROM buku_digital AS b
            LEFT JOIN peminjaman AS p
              ON p.id_buku = b.id_buku
             AND p.id_pengguna = %s
             AND p.status = 'Aktif'
            LEFT JOIN (
                SELECT id_buku, COUNT(*) AS borrowed_count
                FROM peminjaman
                WHERE status = 'Aktif'
                GROUP BY id_buku
            ) AS inventory ON inventory.id_buku = b.id_buku
            LEFT JOIN (
                SELECT bt.id_buku,
                       GROUP_CONCAT(t.nama_tag ORDER BY t.nama_tag SEPARATOR ', ')
                           AS tags
                FROM buku_tag AS bt
                JOIN tag_buku AS t ON t.id_tag = bt.id_tag
                GROUP BY bt.id_buku
            ) AS book_tags ON book_tags.id_buku = b.id_buku
            ORDER BY b.tgl_diunggah DESC, b.id_buku DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def get_admin_book(book_id):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id_buku, judul_buku, penulis, penerbit, sinopsis, cover_data,
                   jumlah_stok
            FROM buku_digital
            WHERE id_buku = %s
            """,
            (book_id,),
        )
        book = cursor.fetchone()
        if book is None:
            raise ValueError("Buku tidak ditemukan.")
        return book
    finally:
        connection.close()


def get_book_tags(book_id):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT t.id_tag, t.nama_tag
            FROM tag_buku AS t
            JOIN buku_tag AS bt ON bt.id_tag = t.id_tag
            WHERE bt.id_buku = %s
            ORDER BY t.nama_tag
            """,
            (book_id,),
        )
        return cursor.fetchall()
    finally:
        connection.close()


def get_all_tags():
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id_tag, nama_tag FROM tag_buku ORDER BY nama_tag")
        return cursor.fetchall()
    finally:
        connection.close()


def create_tag(name):
    name = name.strip()
    if not name or len(name) > 60:
        raise ValueError("Nama tag harus berisi 1–60 karakter.")

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO tag_buku (nama_tag) VALUES (%s)", (name,))
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def rename_tag(tag_id, name):
    name = name.strip()
    if not name or len(name) > 60:
        raise ValueError("Nama tag harus berisi 1–60 karakter.")

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE tag_buku SET nama_tag = %s WHERE id_tag = %s",
            (name, tag_id),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id_tag FROM tag_buku WHERE id_tag = %s", (tag_id,)
            )
            if cursor.fetchone() is None:
                raise ValueError("Tag tidak ditemukan.")
        connection.commit()
    finally:
        connection.close()


def delete_tag(tag_id):
    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM tag_buku WHERE id_tag = %s", (tag_id,))
        if cursor.rowcount == 0:
            raise ValueError("Tag tidak ditemukan.")
        connection.commit()
    finally:
        connection.close()


def update_book_details(
    book_id, title, author, publisher, synopsis, cover_data, tags=()
):
    title = title.strip()
    if not title:
        raise ValueError("Judul buku wajib diisi.")
    normalized_tags = []
    seen_tags = set()
    for tag in tags:
        name = tag.strip()
        if not name:
            continue
        if len(name) > 60:
            raise ValueError("Nama tag maksimal 60 karakter.")
        normalized_name = name.casefold()
        if normalized_name not in seen_tags:
            normalized_tags.append(name)
            seen_tags.add(normalized_name)

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE buku_digital
            SET judul_buku = %s, penulis = %s, penerbit = %s,
                sinopsis = %s, cover_data = %s
            WHERE id_buku = %s
            """,
            (
                title, author.strip(), publisher.strip(),
                synopsis.strip() or None, cover_data, book_id,
            ),
        )
        cursor.execute("SELECT id_buku FROM buku_digital WHERE id_buku = %s", (book_id,))
        if cursor.fetchone() is None:
            raise ValueError("Buku tidak ditemukan.")
        tag_ids = []
        for name in normalized_tags:
            cursor.execute(
                "SELECT id_tag FROM tag_buku WHERE nama_tag = %s", (name,)
            )
            tag = cursor.fetchone()
            if tag is None:
                cursor.execute(
                    "INSERT INTO tag_buku (nama_tag) VALUES (%s)", (name,)
                )
                tag_ids.append(cursor.lastrowid)
            else:
                tag_ids.append(tag[0])
        cursor.execute("DELETE FROM buku_tag WHERE id_buku = %s", (book_id,))
        if tag_ids:
            cursor.executemany(
                "INSERT INTO buku_tag (id_buku, id_tag) VALUES (%s, %s)",
                [(book_id, tag_id) for tag_id in tag_ids],
            )
        connection.commit()
        return "Data buku berhasil diperbarui."
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
            SET file_data = %s
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
            "SELECT file_data FROM buku_digital WHERE id_buku = %s",
            (book_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Book {book_id} was not found.")
        return row[0]
    finally:
        connection.close()


def update_book_stock(book_id, stock):
    if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
        raise ValueError("Stock must be a non-negative whole number.")

    connection = connect_database()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id_buku FROM buku_digital WHERE id_buku = %s FOR UPDATE",
            (book_id,),
        )
        if cursor.fetchone() is None:
            return False, "Buku tidak ditemukan."

        cursor.execute(
            "SELECT COUNT(*) FROM peminjaman "
            "WHERE id_buku = %s AND status = 'Aktif'",
            (book_id,),
        )
        borrowed_count = cursor.fetchone()[0]
        if stock < borrowed_count:
            return (
                False,
                f"Stok tidak dapat diatur di bawah {borrowed_count} "
                "salinan yang sedang dipinjam.",
            )

        cursor.execute(
            "UPDATE buku_digital SET jumlah_stok = %s WHERE id_buku = %s",
            (stock, book_id),
        )
        connection.commit()
        return True, f"Stok buku berhasil diubah menjadi {stock}."
    finally:
        connection.close()


def update_loan(user_id, book_id, action, rental_days=7):
    if action not in ("borrow", "return"):
        raise ValueError("Jenis tindakan peminjaman tidak valid.")
    if action == "borrow" and (
        isinstance(rental_days, bool)
        or not isinstance(rental_days, int)
        or not 1 <= rental_days <= 7
    ):
        raise ValueError("Durasi peminjaman harus antara 1 dan 7 hari.")

    connection = connect_database()
    try:
        cursor = connection.cursor()
        if _expire_overdue_loans(cursor):
            connection.commit()
        if action == "borrow":
            cursor.execute(
                "SELECT jumlah_stok FROM buku_digital "
                "WHERE id_buku = %s FOR UPDATE",
                (book_id,),
            )
            book = cursor.fetchone()
            if book is None:
                return False, "Buku tidak ditemukan."

            cursor.execute(
                "SELECT 1 FROM peminjaman WHERE id_pengguna = %s "
                "AND id_buku = %s AND status = 'Aktif'",
                (user_id, book_id),
            )
            active_loans = cursor.fetchall()
            if active_loans:
                return False, "Buku ini sudah ada di daftar pinjaman Anda."

            cursor.execute(
                "SELECT COUNT(*) FROM peminjaman "
                "WHERE id_buku = %s AND status = 'Aktif'",
                (book_id,),
            )
            borrowed_count = cursor.fetchone()[0]
            if borrowed_count >= book[0]:
                return False, "Semua salinan buku ini sedang dipinjam."

            due_date = (date.today() + timedelta(days=rental_days)).isoformat()
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
