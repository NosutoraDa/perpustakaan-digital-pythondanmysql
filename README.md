# Ruang Baca - Perpustakaan Digital

Aplikasi perpustakaan desktop sederhana dengan Python, Tkinter, dan MySQL/MariaDB.

## Menjalankan aplikasi

Gunakan Python 3.8 atau lebih baru. Buat database bernama
`db_perpustakaan_digital`, lalu impor `db_perpustakaan_digital.sql` ke database
tersebut melalui tab **Import** di phpMyAdmin. Untuk membuat databasenya dari
PowerShell:

```powershell
mysql -u root -p -e "CREATE DATABASE db_perpustakaan_digital"
```

Setelah mengimpor SQL, pasang dependency dan jalankan aplikasi:

```powershell
python -m pip install -r requirements.txt
python main.py
```

File `test.py` tetap dapat digunakan sebagai launcher lama. UI dibagi ke
`pages/login_page.py`, `pages/student_page.py`, dan `pages/admin_page.py`;
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

Aplikasi memakai data pengguna, buku, dan peminjaman dari SQL dump yang diimpor.
Jika diperlukan, aplikasi menambahkan kolom opsional `cover_buku` ke database
lama dan kolom `file_data` untuk menyimpan isi PDF pada database lama. Dump
terbaru menyertakan PDF contoh singkat untuk ketiga buku awal; ganti file contoh
tersebut dengan PDF yang ingin digunakan melalui panel admin.
Jika koneksi gagal, aplikasi menampilkan detail error MySQL; pastikan layanan
MySQL/MariaDB berjalan dan database serta tabel hasil impor tersedia.

## Fitur

- Katalog buku berbentuk grid dengan pencarian dan filter buku tersedia atau
  sedang dipinjam.
- Peminjaman selama tujuh hari, pengembalian, serta membuka file buku yang
  sudah dipinjam.
- Panel admin untuk menambah buku beserta file dan sampulnya, serta menghapus
  buku yang belum memiliki riwayat pinjaman. Admin juga dapat mengganti PDF
  pada buku terpilih tanpa mengubah metadata atau riwayat peminjaman. PDF
  disimpan sebagai `LONGBLOB` di MySQL, sehingga ikut tersimpan saat database
  diekspor; saat dibaca, aplikasi mengekstrak salinan sementara untuk pembaca
  PDF di komputer.
- Pilih akun dari tabel `pengguna` pada layar awal. Peran `Admin-CRUD` membuka
  panel admin; peran `Siswa-Rent` membuka katalog siswa.
- Sampul PNG/GIF ditampilkan langsung; dukungan sampul JPEG tersedia jika Pillow
  terpasang. Tanpa sampul yang dapat dibaca, katalog menampilkan ilustrasi
  pengganti.

### Menyimpan PDF di dalam database

Impor SQL dump untuk mendapatkan tiga PDF contoh bawaan. Tambahkan buku atau
gunakan **Ganti PDF buku terpilih** untuk menyimpan PDF lain ke kolom
`file_data`, bukan hanya menyimpan path file. Setelah itu, gunakan **Export**
di phpMyAdmin untuk membuat dump yang menyertakan PDF.

Menyimpan BLOB praktis untuk koleksi kecil atau PDF berukuran wajar, tetapi
membuat database dan file export membesar. Untuk PDF besar, batas
`max_allowed_packet` MySQL/MariaDB dan batas upload phpMyAdmin mungkin perlu
ditingkatkan.
