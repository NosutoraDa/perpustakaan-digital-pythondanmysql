# ERAUTAMA - Perpustakaan Digital

Aplikasi perpustakaan desktop sederhana dengan Python, Tkinter, dan MySQL/MariaDB.

## Menjalankan aplikasi

Gunakan Python 3.8 atau lebih baru. Pilih salah satu dump SQL berikut:

- `db_perpustakaan_digital (without_books).sql` (sekitar 4,5 KB): skema dan data
  contoh tanpa BLOB buku berukuran besar. Cocok untuk impor melalui phpMyAdmin.
- `db_perpustakaan_digital (with_books).sql` (sekitar 207 MB): termasuk file
  buku dalam database. phpMyAdmin mungkin menolak unggahan karena batas ukuran;
  gunakan impor command line di bawah jika itu terjadi.

Untuk mencoba impor dump besar lewat phpMyAdmin, batas upload PHP juga harus
mencukupi. Di XAMPP Control Panel, klik **Config** pada baris Apache, buka
`php.ini`, lalu atur `upload_max_filesize` dan `post_max_size` ke setidaknya
`256M`. Simpan dan mulai ulang Apache. Batas `max_allowed_packet` MariaDB di
bawah ini tetap harus cukup; jika phpMyAdmin masih menolak file atau waktu
impor habis, gunakan command line.

Kedua dump membuat database `db_perpustakaan_digital`, tabel, relasi, dan data
contoh. Jangan mengimpor dump berulang kali ke database yang sama tanpa
menghapus tabel lama terlebih dahulu.

### Impor dump besar di Windows dengan XAMPP

Perintah ini memakai lokasi XAMPP `D:\xampp` dan file dump di folder proyek.
Buka **Command Prompt** (bukan prompt `MariaDB>`), lalu jalankan:

```bat
"D:\xampp\mysql\bin\mysql.exe" -u root -p < "D:\MDaffa\Kuliah Praktek\tugas-akhir-semester-1-database\perpustakaan-digital-pythondanmysql\db_perpustakaan_digital (with_books).sql"
```

Jika file dump berada di lokasi lain, salin path lengkapnya dari File Explorer:
klik kanan file `.sql` sambil menekan **Shift**, pilih **Copy as path**, lalu
ganti path file SQL di ujung perintah dengan path yang disalin. Pertahankan tanda
kutip di sekitar path karena nama folder atau file bisa mengandung spasi.

Masukkan password MariaDB saat diminta. Jika akun `root` tidak memakai password,
tekan Enter. Sesuaikan lokasi executable atau file SQL jika foldernya berbeda.

Jika muncul `ERROR 1153 ... bigger than 'max_allowed_packet'`, tingkatkan batas
server MariaDB:

1. Di XAMPP Control Panel, hentikan **MySQL**, lalu klik **Config** di baris
   MySQL dan buka `my.ini`.
2. Di bagian `[mysqld]`, tambahkan atau ubah baris menjadi:

   ```ini
   max_allowed_packet=512M
   ```

3. Simpan file dan mulai ulang MySQL di XAMPP.
4. Di phpMyAdmin, buka tab **SQL** dan periksa nilainya:

   ```sql
   SHOW GLOBAL VARIABLES LIKE 'max_allowed_packet';
   ```

   Nilai yang diharapkan adalah `536870912` byte. Jika perlu, root dapat
   menaikkannya untuk sesi server saat ini dengan:

   ```sql
   SET GLOBAL max_allowed_packet = 536870912;
   ```

   Pengaturan `SET GLOBAL` berlaku sampai server dimulai ulang; `my.ini`
   menyimpan pengaturan untuk restart berikutnya. Opsi
   `--max-allowed-packet=512M` pada perintah impor hanya mengatur batas klien,
   jadi batas server tetap perlu disetel.

Jika impor sebelumnya gagal, sebagian tabel mungkin sudah dibuat. Sebelum
mengulang impor, pilih `db_perpustakaan_digital` di phpMyAdmin, buka tab **SQL**,
dan jalankan perintah berikut untuk menghapus tabel parsial. **Ini menghapus isi
keempat tabel tersebut.**

```sql
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS tag_buku, peminjaman, pengguna, buku_digital;
SET FOREIGN_KEY_CHECKS = 1;
```

Kemudian jalankan kembali perintah impor command line di atas. File `.ibd` yang
terlihat di folder `xampp\mysql\data` adalah berkas penyimpanan internal
MariaDB; jangan hapus atau pindahkan saat server berjalan. phpMyAdmin membaca
skema dan metadata yang dikelola server, bukan folder tersebut secara langsung.
Jika `DROP DATABASE` gagal dengan `ERROR 1010` atau `Directory not empty`, cek
di phpMyAdmin dengan `SHOW VARIABLES LIKE 'datadir';` untuk memastikan server
memakai folder data XAMPP yang sama. Jangan menghapus isi folder database secara
manual saat MySQL berjalan; buat salinan cadangan dan perbaiki tabel melalui
MariaDB atau minta bantuan sebelum mengubah berkas data internal.

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
