# ERAUTAMA - Perpustakaan Digital

Aplikasi perpustakaan desktop yang dibuat dengan Python, Tkinter, dan MySQL/MariaDB.

## 1. Siapkan aplikasi

Pastikan sudah terpasang:

- Python 3.8 atau lebih baru.
- XAMPP dengan MySQL aktif. Jalankan XAMPP Control Panel, lalu klik **Start**
  pada baris **MySQL**.

## 2. Database otomatis disiapkan

Pastikan MySQL/MariaDB dari XAMPP sedang berjalan. Saat `main.py` dijalankan,
aplikasi membuat database `db_perpustakaan_digital` dan tabel jika belum tersedia,
lalu menambahkan akun dan data contoh yang belum ada. Skema dan dua buku awal
berada di `database.py`; empat buku contoh beserta PDF dan sampulnya berada di
`book_seed_data.py`. Simpan kedua file tersebut di folder yang sama. Tidak perlu
mengimpor file SQL untuk menjalankan aplikasi.

Secara bawaan aplikasi memakai `localhost:3306`, user `root`, dan password
kosong. Jika MySQL memakai pengaturan berbeda, isi variabel `MYSQL_HOST`,
`MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, dan `MYSQL_DATABASE` sebelum
menjalankan aplikasi. Akun MySQL harus memiliki izin membuat database dan tabel.

## 3. Pasang kebutuhan Python

Paling praktis di Windows: buka folder proyek dan double-click
`run.bat`. Launcher ini akan memasang paket Python yang dibutuhkan dan
menjalankan aplikasi secara otomatis.

Atau lakukan langkah manual berikut:

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

Dump SQL opsional tersedia di folder proyek. `db_perpustakaan_digital (with_books).sql`
berisi empat buku pilihan dan PDF-nya tanpa sampul; ukurannya sekitar 38,7 MB.
`db_perpustakaan_digital (without_book_files).sql` mempertahankan metadata buku
dan tag tanpa PDF atau sampul. Dump `with_books` yang asli berisi 21 buku dengan
PDF dan sampul, sehingga ukurannya sekitar 207 MB. Untuk penggunaan aplikasi
biasa, jalankan `main.py`; data contoh akan disiapkan otomatis. PDF dan sampul
yang ditambahkan admin disimpan di database, sehingga ukuran database dan file
hasil **Export** dapat menjadi besar.
