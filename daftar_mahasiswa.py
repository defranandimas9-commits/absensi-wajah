"""
====================================================
  DAFTARKAN MAHASISWA KE DATABASE
  Jalankan SEKALI setelah server Railway aktif
====================================================

Cara pakai:
1. Isi daftar mahasiswa di bawah
2. Ganti SERVER dengan URL Railway kamu
3. Jalankan: python daftar_mahasiswa.py
"""

import requests

# ← Ganti dengan URL server Railway kamu
SERVER = "https://URL_SERVER_KAMU.railway.app"

# ← Isi semua mahasiswa di sini
# PENTING: nama harus sama persis dengan nama folder di dataset/
# Contoh folder: Budi_Santoso → nama di sini: "Budi Santoso"

mahasiswa = [
    {"nim": "2021001", "nama": "Budi Santoso"},
    {"nim": "2021002", "nama": "Ani Rahayu"},
    {"nim": "2021003", "nama": "Rizky Pratama"},
    # tambahkan mahasiswa lain di sini...
    # {"nim": "2021004", "nama": "Nama Mahasiswa"},
]

print("=" * 50)
print("  MENDAFTARKAN MAHASISWA KE DATABASE")
print("=" * 50)

berhasil = 0
gagal = 0

for m in mahasiswa:
    try:
        r = requests.post(
            f"{SERVER}/mahasiswa/tambah",
            json={"nim": m["nim"], "nama": m["nama"]},
            timeout=10
        )
        hasil = r.json()
        if hasil.get("sukses"):
            print(f"  ✅  {m['nim']} — {m['nama']}")
            berhasil += 1
        else:
            print(f"  ⚠️  {m['nim']} — {m['nama']} : {hasil.get('pesan')}")
            gagal += 1
    except Exception as e:
        print(f"  ❌  {m['nim']} — {m['nama']} : Error - {e}")
        gagal += 1

print("=" * 50)
print(f"  Selesai! Berhasil: {berhasil}, Gagal/Sudah ada: {gagal}")
print("=" * 50)
