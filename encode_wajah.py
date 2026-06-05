"""
====================================================
  ENCODER WAJAH MAHASISWA
  Jalankan SEKALI untuk daftarkan wajah ke sistem
====================================================

Cara pakai:
1. Buat folder: dataset/
2. Di dalam dataset/, buat folder per mahasiswa:
   dataset/Budi_Santoso/
   dataset/Ani_Rahayu/
3. Isi tiap folder dengan 5-10 foto wajah (.jpg/.png)
4. Jalankan: python encode_wajah.py
5. Upload file face_encodings.pkl ke server
"""

import face_recognition
import os
import pickle
from pathlib import Path

DATASET_DIR = "dataset"
OUTPUT_FILE = "face_encodings.pkl"

def encode_semua_wajah():
    semua_encodings = []
    semua_nama = []
    gagal = []

    if not os.path.exists(DATASET_DIR):
        print(f"❌ Folder '{DATASET_DIR}' tidak ditemukan!")
        print("   Buat folder dataset/ lalu isi dengan foto mahasiswa.")
        return

    mahasiswa_folders = [f for f in Path(DATASET_DIR).iterdir() if f.is_dir()]
    if not mahasiswa_folders:
        print("❌ Tidak ada folder mahasiswa di dalam dataset/")
        return

    print(f"📂 Ditemukan {len(mahasiswa_folders)} mahasiswa\n")

    for folder in sorted(mahasiswa_folders):
        nama = folder.name.replace("_", " ")
        foto_files = list(folder.glob("*.jpg")) + list(folder.glob("*.png")) + list(folder.glob("*.jpeg"))

        if not foto_files:
            print(f"  ⚠️  {nama}: tidak ada foto, dilewati")
            continue

        print(f"  👤 Memproses: {nama} ({len(foto_files)} foto)")
        berhasil = 0

        for foto_path in foto_files:
            try:
                image = face_recognition.load_image_file(str(foto_path))
                encodings = face_recognition.face_encodings(image)

                if len(encodings) == 0:
                    print(f"      ⚠️  {foto_path.name}: wajah tidak terdeteksi")
                    continue
                if len(encodings) > 1:
                    print(f"      ⚠️  {foto_path.name}: lebih dari 1 wajah, pakai yang pertama")

                semua_encodings.append(encodings[0])
                semua_nama.append(nama)
                berhasil += 1

            except Exception as e:
                print(f"      ❌ {foto_path.name}: error - {e}")
                gagal.append(foto_path.name)

        print(f"      ✅ {berhasil}/{len(foto_files)} foto berhasil di-encode\n")

    if not semua_encodings:
        print("❌ Tidak ada encoding yang berhasil dibuat.")
        return

    # Simpan ke file
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump({
            "encodings": semua_encodings,
            "names": semua_nama
        }, f)

    print("=" * 50)
    print(f"✅ Selesai! Total encoding: {len(semua_encodings)}")
    print(f"📁 Disimpan ke: {OUTPUT_FILE}")
    print(f"📋 Mahasiswa terdaftar: {sorted(set(semua_nama))}")
    if gagal:
        print(f"⚠️  File gagal diproses: {gagal}")
    print("\n🔜 Upload file face_encodings.pkl ke server kamu!")

if __name__ == "__main__":
    encode_semua_wajah()
