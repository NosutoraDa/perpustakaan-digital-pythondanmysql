# ERAUTAMA - Perpustakaan Digital

Aplikasi perpustakaan desktop yang dibuat dengan Python, Tkinter, dan MySQL/MariaDB.

## 1. Siapkan aplikasi

Pastikan sudah terpasang:

- Python 3.8 atau lebih baru.
- XAMPP dengan MySQL aktif. Jalankan XAMPP Control Panel, lalu klik **Start**
  pada baris **MySQL**.

## 2. Siapkan database

Ada dua file SQL. Pilih salah satu:

- `db_perpustakaan_digital (without_books).sql` (sekitar 4,5 KB): pilihan yang
  disarankan untuk pemula. File ini membuat tabel dan akun contoh, tetapi tidak
  berisi data buku.
- `db_perpustakaan_digital (with_books).sql` (sekitar 207 MB): menyertakan file
  buku beserta file PDF-nya. Proses impornya lebih rumit dan mungkin terlalu
  besar untuk phpMyAdmin.

### Cara mudah: impor file kecil lewat phpMyAdmin

1. Buka `http://localhost/phpmyadmin` di browser.
2. Klik tab **Import**.
3. Klik **Choose File**, pilih `db_perpustakaan_digital (without_books).sql`.
4. Klik **Import** atau **Go** di bagian bawah halaman.

Dump SQL akan membuat database bernama `db_perpustakaan_digital` beserta tabel
dan data contoh.

### Impor file besar lewat Command Prompt

Gunakan cara ini untuk file `with_books` jika phpMyAdmin menolak file karena
ukurannya. Perintah berikut sesuai dengan XAMPP di `D:\xampp` dan lokasi file
SQL pada komputer ini. Buka **Command Prompt** dari menu Start. Jangan ketik
perintah ini di jendela yang menampilkan prompt `MariaDB>`.

```bat
"D:\xampp\mysql\bin\mysql.exe" -u root -p < "D:\MDaffa\Kuliah Praktek\tugas-akhir-semester-1-database\perpustakaan-digital-pythondanmysql\db_perpustakaan_digital (with_books).sql"
```

Saat muncul `Enter password`, ketik password MariaDB lalu tekan Enter. Jika akun
`root` tidak memiliki password, langsung tekan Enter. Saat mengetik password,
karakter yang diketik memang tidak terlihat.

Jika file SQL ada di folder lain, salin path-nya dari File Explorer: tekan dan
tahan **Shift**, klik kanan file `.sql`, lalu pilih **Copy as path**. Ganti path
file SQL yang ada di ujung perintah dengan path tersebut. Biarkan tanda kutip
mengapit path. Jika XAMPP tidak berada di `D:\xampp`, sesuaikan bagian pertama
perintah agar menunjuk ke `mysql.exe` di folder XAMPP Anda.

### Jika muncul pesan `ERROR 1153` / `max_allowed_packet`

Pesan ini berarti MariaDB menolak data buku yang besar. Naikkan batasnya:

1. Di XAMPP Control Panel, klik **Stop** pada MySQL.
2. Klik **Config** pada baris MySQL, lalu buka `my.ini`.
3. Cari bagian `[mysqld]`. Di bawahnya, tambahkan baris ini. Jika sudah ada,
   ubah nilainya:

   ```ini
   max_allowed_packet=512M
   ```

4. Simpan `my.ini`, lalu klik **Start** pada MySQL.
5. Di phpMyAdmin, klik tab **SQL** dan jalankan:

   ```sql
   SHOW GLOBAL VARIABLES LIKE 'max_allowed_packet';
   ```

   Nilainya seharusnya `536870912`. Jika masih lebih kecil, jalankan perintah
   berikut di tab **SQL**:

   ```sql
   SET GLOBAL max_allowed_packet = 536870912;
   ```

   Setelah itu, ulangi impor dari Command Prompt. Perintah `SET GLOBAL` hanya
   berlaku sampai MySQL dimulai ulang; pengaturan di `my.ini` akan tetap berlaku
   setelah restart. Opsi `--max-allowed-packet` di Command Prompt saja tidak
   cukup karena batas di MariaDB juga harus dinaikkan.

### Jika impor sebelumnya gagal atau muncul `table already exists`

Impor yang gagal bisa saja sudah membuat sebagian tabel. Untuk menghapus tabel
tersebut sebelum mencoba lagi:

1. Buka phpMyAdmin dan klik database `db_perpustakaan_digital` di sisi kiri.
2. Klik tab **SQL**.
3. Jalankan perintah berikut.

   **Perhatian:** perintah ini menghapus data dari empat tabel di bawah.

   ```sql
   SET FOREIGN_KEY_CHECKS = 0;
   DROP TABLE IF EXISTS tag_buku, peminjaman, pengguna, buku_digital;
   SET FOREIGN_KEY_CHECKS = 1;
   ```

4. Ulangi impor file SQL.

Jika `DROP DATABASE` gagal dengan pesan `ERROR 1010` atau `Directory not empty`,
jangan hapus atau pindahkan file `.ibd` dari Explorer saat MySQL berjalan. File
`.ibd` adalah file internal MariaDB. Di phpMyAdmin, buka tab **SQL** dan cek
lokasi data yang dipakai server:

```sql
SHOW VARIABLES LIKE 'datadir';
```

Jika langkah di atas belum menyelesaikan masalah, minta bantuan sebelum mengubah
file di folder data XAMPP.

## 3. Pasang kebutuhan Python

Buka folder proyek di File Explorer. Klik bagian alamat folder di atas, ketik
`cmd`, lalu tekan Enter. Di jendela Command Prompt yang terbuka, jalankan:

```powershell
python -m pip install -r requirements.txt
```

## 4. Jalankan aplikasi

Di jendela Command Prompt atau PowerShell yang sama, jalankan:

```powershell
python main.py
```

Secara bawaan, aplikasi mencoba terhubung ke MySQL di `localhost`, port `3306`,
dengan nama database `db_perpustakaan_digital`, user `root`, dan password kosong.
Jika pengaturan MySQL Anda berbeda, isi variabel berikut sebelum menjalankan
aplikasi. Ganti password contoh dengan password MySQL Anda:

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "password-anda"
$env:MYSQL_DATABASE = "db_perpustakaan_digital"
python main.py
```

## Akun untuk mencoba aplikasi

Gunakan NIM dan password berikut untuk masuk:

| Nama | Peran | NIM | Password |
|---|---|---|---|
| Admin 1 | Admin | `2026001` | `Admin123!` |
| User 1 | Siswa | `2026002` | `User123!` |
| User 2 | Siswa | `2026003` | `User123!` |
| User 3 | Siswa | `2026004` | `User123!` |

Password contoh disimpan dalam bentuk hash di database. Mengimpor dump lagi akan
mengatur ulang data akun contoh. Admin bisa mengatur password akun melalui tab
**Pengguna**.

## Fitur utama

- Melihat dan mencari katalog buku.
- Meminjam buku dan mengembalikannya. Admin dapat mengatur stok buku.
- Admin dapat menambah, mengubah, dan menghapus buku, serta mengelola akun.
- PDF dan sampul yang ditambahkan admin disimpan di database.
- Pengguna dapat mendaftar dengan NIM dan password; akun baru menjadi siswa.

Dump `with_books` menyediakan tiga buku contoh beserta file-nya. Dump
`without_books` tidak memiliki data buku; admin dapat menambahkan buku melalui
aplikasi. PDF dan sampul yang ditambahkan disimpan di database, sehingga ukuran
database dan file hasil **Export** dapat menjadi besar.
