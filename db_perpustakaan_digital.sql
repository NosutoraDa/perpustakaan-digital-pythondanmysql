-- Database perpustakaan digital.
-- Impor file ini melalui phpMyAdmin atau jalankan dengan MySQL/MariaDB.

CREATE DATABASE IF NOT EXISTS db_perpustakaan_digital
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

USE db_perpustakaan_digital;

-- Koleksi buku. Isi PDF dan gambar sampul disimpan sebagai BLOB.
CREATE TABLE IF NOT EXISTS buku_digital (
    id_buku INT NOT NULL AUTO_INCREMENT,
    judul_buku VARCHAR(150) NOT NULL,
    penulis VARCHAR(100),
    penerbit VARCHAR(100),
    sinopsis TEXT,
    file_data LONGBLOB,
    cover_data LONGBLOB,
    tgl_diunggah DATE,
    jumlah_stok INT NOT NULL DEFAULT 1,
    PRIMARY KEY (id_buku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Akun admin dan siswa. Password disimpan sebagai hash, bukan teks biasa.
CREATE TABLE IF NOT EXISTS pengguna (
    id_pengguna INT NOT NULL AUTO_INCREMENT,
    no_identitas VARCHAR(30) NOT NULL,
    nama_pengguna VARCHAR(100) NOT NULL,
    tgl_bergabung DATE,
    peran ENUM('Admin-CRUD', 'Siswa-Rent') NOT NULL,
    password_hash VARCHAR(255),
    PRIMARY KEY (id_pengguna),
    UNIQUE KEY unik_nim (no_identitas)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Setiap peminjaman menghubungkan satu pengguna dengan satu buku.
CREATE TABLE IF NOT EXISTS peminjaman (
    id_pinjam INT NOT NULL AUTO_INCREMENT,
    id_pengguna INT NOT NULL,
    id_buku INT NOT NULL,
    tenggat_waktu DATE,
    status ENUM('Aktif', 'Kembali') DEFAULT 'Aktif',
    PRIMARY KEY (id_pinjam),
    KEY indeks_peminjaman_pengguna (id_pengguna),
    KEY indeks_peminjaman_buku (id_buku),
    CONSTRAINT fk_peminjaman_pengguna
        FOREIGN KEY (id_pengguna) REFERENCES pengguna (id_pengguna),
    CONSTRAINT fk_peminjaman_buku
        FOREIGN KEY (id_buku) REFERENCES buku_digital (id_buku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Akun demo. Password disimpan sebagai hash; password untuk laporan ada di README.
INSERT INTO pengguna
    (no_identitas, nama_pengguna, tgl_bergabung, peran, password_hash)
VALUES
    ('2026001', 'Admin 1', '2026-01-10', 'Admin-CRUD',
     'pbkdf2_sha256$600000$P6AHdNrPQm56hlbcSjiUFA==$mNpPstKlFaQA1iLVGaAyV-E-AlUK55On9zuVjxic1ao='),
    ('2026002', 'User 1', '2026-01-12', 'Siswa-Rent',
     'pbkdf2_sha256$600000$JYWKQKSQ5TA7ZK2KYX4AAQ==$6NBmo4fTM5_lAOQftUp3EuvyMB-tlZvH8r3g80QGPyA='),
    ('2026003', 'User 2', '2026-01-15', 'Siswa-Rent',
     'pbkdf2_sha256$600000$Fo761fnh58-zCbd4iyxrHg==$vhCuEZfakrHwzMadV0jPKfmTjdLLiNrr2ZcNMirKSJo='),
    ('2026004', 'User 3', '2026-01-16', 'Siswa-Rent',
     'pbkdf2_sha256$600000$be8gew5DAmpfd5knusokhw==$Euz2EC70SQ1zIIUl356vUOCRBmzR2_EHcB1OOYgJj_k=')
ON DUPLICATE KEY UPDATE
    nama_pengguna = VALUES(nama_pengguna),
    tgl_bergabung = VALUES(tgl_bergabung),
    peran = VALUES(peran),
    password_hash = VALUES(password_hash);

-- File PDF dan sampul sengaja kosong; admin dapat mengunggahnya dari aplikasi.
INSERT IGNORE INTO buku_digital
    (id_buku, judul_buku, penulis, penerbit, sinopsis, tgl_diunggah, jumlah_stok)
VALUES
    (
        1, 'Belajar MySQL', 'Abdul Kadir', 'Andi Publisher',
        'Pengenalan dasar SQL dan pengelolaan basis data MySQL, mulai dari tabel hingga query.',
        '2026-01-10', 2
    ),
    (
        2, 'Pemrograman Python', 'Budi Raharjo', 'Informatika',
        'Pengantar bahasa Python, struktur program, fungsi, dan konsep pemrograman.',
        '2026-01-12', 2
    ),
    (
        3, 'Dasar Basis Data', 'Fathansyah', 'Informatika',
        'Pembahasan konsep basis data, tabel, relasi, kunci, dan perancangan data.',
        '2026-01-15', 2
    );

-- Contoh dua peminjaman aktif dan satu buku yang sudah dikembalikan.
INSERT IGNORE INTO peminjaman
    (id_pinjam, id_pengguna, id_buku, tenggat_waktu, status)
VALUES
    (7, 2, 1, '2026-11-10', 'Aktif'),
    (8, 3, 2, '2026-11-12', 'Aktif'),
    (9, 2, 3, '2026-11-15', 'Kembali');
