from flask import Flask, request, jsonify
from flask_cors import CORS
from deepface import DeepFace
import sqlite3
import base64
import os
import io
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "absensi.db"
DATASET_DIR = "dataset"

# ─────────────────────────────────────────
#  SETUP DATABASE
# ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mahasiswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nim TEXT UNIQUE NOT NULL,
            nama TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nim TEXT NOT NULL,
            nama TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            waktu TEXT NOT NULL,
            status TEXT DEFAULT 'HADIR',
            device TEXT DEFAULT 'unknown',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
#  CEK SERVER
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    # Hitung jumlah mahasiswa terdaftar di dataset
    mahasiswa_list = []
    if os.path.exists(DATASET_DIR):
        mahasiswa_list = [f for f in os.listdir(DATASET_DIR)
                         if os.path.isdir(os.path.join(DATASET_DIR, f))]
    return jsonify({
        "status": "ok",
        "message": "Server Absensi Aktif",
        "mahasiswa_terdaftar": len(mahasiswa_list),
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# ─────────────────────────────────────────
#  ABSEN — cocokkan wajah dengan dataset
# ─────────────────────────────────────────
@app.route("/absen", methods=["POST"])
def absen():
    try:
        data = request.get_json()
        if not data or "foto_base64" not in data:
            return jsonify({"sukses": False, "pesan": "Data foto tidak ditemukan"}), 400

        device_info = data.get("device", "unknown")

        # Simpan foto yang dikirim ke file sementara
        foto_bytes = base64.b64decode(data["foto_base64"])
        image = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
        foto_sementara = "/tmp/foto_absen.jpg"
        image.save(foto_sementara)

        # Cek folder dataset ada
        if not os.path.exists(DATASET_DIR):
            return jsonify({
                "sukses": False,
                "pesan": "Folder dataset tidak ditemukan di server."
            })

        # Loop semua mahasiswa di dataset
        nama_dikenali = None
        jarak_terkecil = 999

        for nama_folder in os.listdir(DATASET_DIR):
            folder_path = os.path.join(DATASET_DIR, nama_folder)
            if not os.path.isdir(folder_path):
                continue

            # Loop semua foto di folder mahasiswa ini
            for foto_file in os.listdir(folder_path):
                if not foto_file.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                foto_referensi = os.path.join(folder_path, foto_file)

                try:
                    hasil = DeepFace.verify(
                        img1_path=foto_sementara,
                        img2_path=foto_referensi,
                        model_name="Facenet",
                        enforce_detection=False,
                        silent=True
                    )

                    if hasil["verified"] and hasil["distance"] < jarak_terkecil:
                        jarak_terkecil = hasil["distance"]
                        nama_dikenali = nama_folder.replace("_", " ")

                except Exception:
                    continue

        # Bersihkan file sementara
        if os.path.exists(foto_sementara):
            os.remove(foto_sementara)

        if not nama_dikenali:
            return jsonify({
                "sukses": False,
                "pesan": "Wajah tidak dikenali. Pastikan sudah terdaftar."
            })

        # Ambil NIM dari database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT nim FROM mahasiswa WHERE LOWER(nama) = LOWER(?)", (nama_dikenali,))
        row = c.fetchone()
        nim = row[0] if row else "unknown"

        # Cek sudah absen hari ini
        tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT id FROM absensi WHERE nim = ? AND tanggal = ?", (nim, tanggal_hari_ini))
        sudah_absen = c.fetchone()

        if sudah_absen:
            conn.close()
            return jsonify({
                "sukses": True,
                "sudah_absen": True,
                "nama": nama_dikenali,
                "nim": nim,
                "pesan": f"{nama_dikenali} sudah absen hari ini."
            })

        # Simpan absen baru
        waktu_sekarang = datetime.now().strftime("%H:%M:%S")
        c.execute("""
            INSERT INTO absensi (nim, nama, tanggal, waktu, status, device)
            VALUES (?, ?, ?, ?, 'HADIR', ?)
        """, (nim, nama_dikenali, tanggal_hari_ini, waktu_sekarang, device_info))
        conn.commit()
        conn.close()

        return jsonify({
            "sukses": True,
            "sudah_absen": False,
            "nama": nama_dikenali,
            "nim": nim,
            "waktu": waktu_sekarang,
            "tanggal": tanggal_hari_ini,
            "pesan": f"{nama_dikenali} berhasil absen!"
        })

    except Exception as e:
        return jsonify({"sukses": False, "pesan": f"Error: {str(e)}"}), 500

# ─────────────────────────────────────────
#  REKAP ADMIN
# ─────────────────────────────────────────
@app.route("/rekap", methods=["GET"])
def rekap():
    tanggal = request.args.get("tanggal", datetime.now().strftime("%Y-%m-%d"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT nim, nama, tanggal, waktu, status, device
        FROM absensi WHERE tanggal = ? ORDER BY waktu ASC
    """, (tanggal,))
    rows = c.fetchall()
    conn.close()
    data = [{"nim": r[0], "nama": r[1], "tanggal": r[2],
             "waktu": r[3], "status": r[4], "device": r[5]} for r in rows]
    return jsonify({"tanggal": tanggal, "total_hadir": len(data), "data": data})

@app.route("/rekap/semua", methods=["GET"])
def rekap_semua():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT nim, nama, tanggal, waktu, status, device
        FROM absensi ORDER BY tanggal DESC, waktu ASC
    """)
    rows = c.fetchall()
    conn.close()
    data = [{"nim": r[0], "nama": r[1], "tanggal": r[2],
             "waktu": r[3], "status": r[4], "device": r[5]} for r in rows]
    return jsonify({"total": len(data), "data": data})

# ─────────────────────────────────────────
#  MAHASISWA
# ─────────────────────────────────────────
@app.route("/mahasiswa", methods=["GET"])
def daftar_mahasiswa():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nim, nama, created_at FROM mahasiswa ORDER BY nama")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"nim": r[0], "nama": r[1], "terdaftar": r[2]} for r in rows])

@app.route("/mahasiswa/tambah", methods=["POST"])
def tambah_mahasiswa():
    data = request.get_json()
    nim = data.get("nim")
    nama = data.get("nama")
    if not nim or not nama:
        return jsonify({"sukses": False, "pesan": "NIM dan nama wajib diisi"}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO mahasiswa (nim, nama) VALUES (?, ?)", (nim, nama))
        conn.commit()
        return jsonify({"sukses": True, "pesan": f"{nama} berhasil ditambahkan"})
    except sqlite3.IntegrityError:
        return jsonify({"sukses": False, "pesan": "NIM sudah terdaftar"})
    finally:
        conn.close()

# ─────────────────────────────────────────
#  START
# ─────────────────────────────────────────
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)