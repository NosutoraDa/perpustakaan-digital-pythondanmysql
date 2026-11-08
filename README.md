# ERAUTAMA - Perpustakaan Digital

Aplikasi perpustakaan desktop sederhana dengan Python, Tkinter, dan MySQL/MariaDB.

## Menjalankan aplikasi

Gunakan Python 3.8 atau lebih baru. Untuk menyiapkan database, impor
`db_perpustakaan_digital.sql` melalui phpMyAdmin:

1. Jalankan MySQL/MariaDB dan buka phpMyAdmin.
2. Buka tab **Import**.
3. Pilih `db_perpustakaan_digital.sql`, lalu klik **Import** atau **Go**.

Dump ini membuat database `db_perpustakaan_digital`, tabel, relasi, dan data
contoh.

Setelah mengimpor SQL, pasang dependency:

```powershell
python -m pip install -r requirements.txt
```

UI dibagi ke `pages/login_page.py`, `pages/student_page.py`, dan `pages/admin_page.py`;
operasi database bersama berada di `database.py`.

Atur variabel koneksi sebelum menjalankan aplikasi jika konfigurasi berbeda
dari nilai bawaan (`localhost`, port `3306`, user `root`, password kosong):

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "your-password"
$env:MYSQL_DATABASE = "db_perpustakaan_digital"
python main.py
```

### Akun contoh

SQL dump membuat akun demo berikut. Masuk dengan NIM dan password yang sesuai:

| Nama | Peran | NIM | Password |
|---|---|---|---|
| Admin 1 | Admin | `2026001` | `Admin123!` |
| User 1 | Siswa | `2026002` | `User123!` |
| User 2 | Siswa | `2026003` | `User123!` |
| User 3 | Siswa | `2026004` | `User123!` |

Password di database disimpan sebagai hash. Ini adalah kredensial demo untuk
praktikum; admin dapat mengatur password lain melalui tab **Pengguna**.
Menjalankan ulang SQL dump akan mengatur ulang nama, peran, dan password akun
demo tersebut.

Jalankan aplikasi dengan:

```powershell
python main.py
```

Aplikasi memakai data pengguna, buku, dan peminjaman dari SQL dump yang diimpor.
Saat terhubung ke database lama, aplikasi menambahkan kolom yang diperlukan,
termasuk `cover_data`, `file_data`, `sinopsis`, `jumlah_stok`, dan `password_hash`,
serta tabel `tag_buku`. Jika database masih memakai tabel relasi `buku_tag`,
aplikasi memindahkan tag ke `tag_buku` lalu menghapus tabel relasi lama.
Kolom path file dari database lama akan dipindahkan ke BLOB jika file asalnya
masih tersedia, lalu kolom path lama dihapus. Jika file lama tidak ditemukan,
aplikasi menampilkan error agar path tersebut dapat dipulihkan atau dibersihkan
terlebih dahulu. PDF dan sampul pada data contoh dibiarkan kosong agar SQL mudah
dibaca; admin dapat menambah file melalui panel aplikasi.
Jika koneksi gagal, aplikasi menampilkan detail error MySQL; pastikan layanan
MySQL/MariaDB berjalan dan database serta tabel hasil impor tersedia.

## Fitur

- Antarmuka terang dengan aksen indigo-navy, header dan panel yang rapi,
  tabel admin bergaris selang-seling, serta tipografi Calibri dan Bahnschrift
  (otomatis memakai Segoe UI bila font tersebut tidak tersedia).
- Katalog buku berbentuk grid dengan pencarian dan filter buku tersedia atau
  sedang dipinjam.
- Peminjaman dengan pilihan durasi 1–7 hari, pengembalian otomatis saat
  tenggat tercapai, serta membuka file buku yang sudah dipinjam. Admin dapat
  mengatur stok tiap buku; jumlah peminjaman aktif tidak dapat melebihi stok
  yang tersedia.
- Detail buku menggunakan bagian **Deskripsi Materi Pembelajaran** agar sesuai
  untuk buku akademik dan bahan ajar. Admin dapat membuat, mengganti nama, dan
  menghapus tag materi khusus per buku melalui popup detail; tag juga dapat
  digunakan dalam pencarian katalog.
- Panel admin untuk menambah buku dan mengubah judul, penulis, penerbit,
  sinopsis, sampul, stok, dan PDF, serta menghapus buku melalui satu jendela
  detail. Form tambah buku dan pengelolaan pengguna juga dibuka sebagai popup.
  Buku yang belum memiliki riwayat pinjaman dapat dihapus. PDF
  dan sampul disimpan sebagai `LONGBLOB` di MySQL, sehingga ikut tersimpan saat
  database diekspor; saat dibaca, aplikasi mengekstrak salinan sementara PDF
  untuk pembaca di komputer.
- Masuk dan daftar menggunakan NIM dan password. Akun baru otomatis menjadi
  siswa. Admin dapat mengatur atau mereset password serta mengubah peran akun
  melalui jendela pengelolaan di tab **Pengguna**, tempat admin juga dapat
  mereset password; admin terakhir tidak dapat diturunkan perannya. Minta admin
  mengatur password untuk akun yang sudah ada di database.
- Sampul PNG/GIF ditampilkan langsung; dukungan sampul JPEG tersedia jika Pillow
  terpasang. Tanpa sampul yang dapat dibaca, katalog menampilkan ilustrasi
  pengganti.
- Detail buku menampilkan sampul di kiri dan informasi serta sinopsis di kanan.

### Menyimpan PDF dan sampul di dalam database

Dump SQL menyediakan tiga data buku contoh tanpa file PDF atau sampul. Tambahkan
buku atau gunakan **Ganti PDF buku terpilih** untuk menyimpan PDF ke kolom
`file_data`, bukan hanya menyimpan path file. Sampul yang dipilih saat
menambahkan buku disimpan sebagai bytes di `cover_data`. Setelah itu, gunakan
**Export** di phpMyAdmin untuk membuat dump yang menyertakan PDF dan sampul.

Menyimpan BLOB praktis untuk koleksi kecil atau file berukuran wajar, tetapi
membuat database dan file export membesar. Untuk file besar, batas
`max_allowed_packet` MySQL/MariaDB dan batas upload phpMyAdmin mungkin perlu
ditingkatkan.
