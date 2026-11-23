"""Skrip uji skenario 7-10 (Tabel 1.5, Bab I).

Letakkan di folder yang sama dengan database.py, pastikan MySQL/MariaDB (XAMPP)
berjalan dan data contoh sudah ada, lalu jalankan:  python uji_peminjaman.py

PERINGATAN: skrip ini mengubah data buku "Literasi Untuk Kehidupan":
semua peminjaman aktif buku itu dikembalikan di awal, dan jumlah_stok
dipulihkan di akhir. Jalankan hanya pada basis data latihan.
"""
import threading

import database as db

JUDUL = "Literasi Untuk Kehidupan"
NIM = {"user1": "2026002", "user2": "2026003", "user3": "2026004"}
PUTARAN = 20

hasil = []  # (nomor, deskripsi, lulus, keterangan)


def catat(no, deskripsi, lulus, ket):
    hasil.append((no, deskripsi, lulus, ket))
    print(f"[{'LULUS' if lulus else 'GAGAL'}] Skenario {no}: {deskripsi}\n         {ket}")


def query(sql, params=()):
    conn = db.connect_database()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else None
        conn.commit()
        return rows
    finally:
        conn.close()


def aktif(id_buku):
    return query("SELECT COUNT(*) FROM peminjaman WHERE id_buku=%s AND status='Aktif'",
                 (id_buku,))[0][0]


def reset(id_buku):
    query("UPDATE peminjaman SET status='Kembali' WHERE id_buku=%s AND status='Aktif'",
          (id_buku,))


def main():
    row = query("SELECT id_buku, jumlah_stok FROM buku_digital WHERE judul_buku=%s", (JUDUL,))
    if not row:
        raise SystemExit(f"Buku '{JUDUL}' tidak ditemukan.")
    id_buku, stok_awal = row[0]
    uid = {}
    for nama, nim in NIM.items():
        r = query("SELECT id_pengguna FROM pengguna WHERE no_identitas=%s", (nim,))
        if not r:
            raise SystemExit(f"Akun {nama} (NIM {nim}) tidak ditemukan.")
        uid[nama] = r[0][0]
    if stok_awal != 2:
        print(f"Catatan: jumlah_stok awal = {stok_awal}, bukan 2. Skenario dirancang untuk stok 2.")
    if input("Semua peminjaman aktif buku ini akan dikembalikan. Ketik YA untuk lanjut: ") != "YA":
        raise SystemExit("Dibatalkan.")

    try:
        db.update_book_stock(id_buku, 2)
        reset(id_buku)

        # ---- Skenario 7: dua sesi bersamaan pada sisa kuota 1 ----
        ok, msg = db.update_loan(uid["user1"], id_buku, "borrow", 7)
        assert ok, f"User 1 gagal meminjam: {msg}"
        pelanggaran, ringkas = [], []
        for putaran in range(1, PUTARAN + 1):
            barrier = threading.Barrier(2)
            out = {}

            def kerja(nama):
                barrier.wait()
                try:
                    out[nama] = db.update_loan(uid[nama], id_buku, "borrow", 7)
                except Exception as e:  # noqa: BLE001
                    out[nama] = (None, f"{type(e).__name__}: {e}")

            ts = [threading.Thread(target=kerja, args=(n,)) for n in ("user2", "user3")]
            [t.start() for t in ts]
            [t.join() for t in ts]
            berhasil = sum(1 for v in out.values() if v[0] is True)
            jumlah = aktif(id_buku)
            ringkas.append(berhasil)
            if berhasil != 1 or jumlah != 2:
                pelanggaran.append((putaran, out, jumlah))
            for nama, v in out.items():  # kembali ke kondisi sisa kuota 1
                if v[0] is True:
                    db.update_loan(uid[nama], id_buku, "return")
        catat(7, f"uji dua sesi, {PUTARAN} putaran", not pelanggaran,
              f"berhasil per putaran: {sorted(set(ringkas))}; putaran melanggar: {len(pelanggaran)}"
              + (f" -> {pelanggaran[0]}" if pelanggaran else ""))
        db.update_loan(uid["user1"], id_buku, "return")

        # ---- Skenario 8: batas durasi ----
        det = []
        lulus = True
        for hari in (1, 7):
            ok, msg = db.update_loan(uid["user2"], id_buku, "borrow", hari)
            det.append(f"{hari} hari -> {ok}: {msg}")
            lulus &= ok is True
            db.update_loan(uid["user2"], id_buku, "return")
        for hari in (0, 8):
            try:
                db.update_loan(uid["user2"], id_buku, "borrow", hari)
                det.append(f"{hari} hari -> TIDAK ditolak")
                lulus = False
                db.update_loan(uid["user2"], id_buku, "return")
            except ValueError as e:
                det.append(f"{hari} hari -> ValueError: {e}")
        catat(8, "batas durasi 1/7 diterima, 0/8 ditolak", lulus, " | ".join(det))

        # ---- Skenario 9: pinjaman ganda (BR-09) ----
        db.update_loan(uid["user2"], id_buku, "borrow", 7)
        ok, msg = db.update_loan(uid["user2"], id_buku, "borrow", 7)
        catat(9, "BR-09 pinjaman ganda ditolak", ok is False, f"{ok}: {msg}")

        # ---- Skenario 10: stok di bawah jumlah peminjam (BR-07) ----
        ok, msg = db.update_book_stock(id_buku, 0)
        catat(10, "BR-07 stok di bawah peminjam aktif ditolak", ok is False, f"{ok}: {msg}")
    finally:
        reset(id_buku)
        db.update_book_stock(id_buku, stok_awal)
        print(f"\njumlah_stok dipulihkan ke {stok_awal}; peminjaman aktif buku ini: {aktif(id_buku)}")

    print("\nRingkasan (salin ke kolom Hasil aktual Tabel 1.5):")
    for no, desk, lulus, ket in hasil:
        print(f"  {no}. {'sesuai harapan' if lulus else 'TIDAK sesuai'}: {ket}")


if __name__ == "__main__":
    main()