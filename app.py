 """
====================================================
  SISTEM ABSENSI WAJAH - SERVER PUSAT
  Deploy ke Railway / Render (GRATIS)
====================================================
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
import numpy as np
import sqlite3
import pickle
import base64
import os
import io
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Izinkan semua device konek

DB_PATH = "absensi.db"
ENCODINGS_PATH = "face_encodings.pkl"

# ─────────────────────────────────────────
#  SETUP DATABASE
# ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabel mahasiswa
    c.execute("""
        CREATE TABLE IF NOT EXISTS mahasiswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nim TEXT UNIQUE NOT NULL,
            nama TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabel absensi
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
    print("✅ Database siap")


# ─────────────────────────────────────────
#  LOAD ENCODINGS WAJAH
# ─────────────────────────────────────────
def load_encodings():
    if not os.path.exists(ENCODINGS_PATH):
        return [], []
    with open(ENCODINGS_PATH, "rb") as f:
        data = pickle.load(f)
    return data["encodings"], data["names"]


# ─────────────────────────────────────────
#  ENDPOINT: CEK SERVER HIDUP
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "message": "Server Absensi Aktif 🟢",
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


# ─────────────────────────────────────────
#  ENDPOINT: ABSEN (terima foto, kenali wajah)
# ─────────────────────────────────────────
@app.route("/absen", methods=["POST"])
def absen():
    try:
        data = request.get_json()
        if not data or "foto_base64" not in data:
            return jsonify({"sukses": False, "pesan": "Data foto tidak ditemukan"}), 400

        device_info = data.get("device", "unknown")

        # Decode foto dari base64
        foto_bytes = base64.b64decode(data["foto_base64"])
        image = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
        foto_array = np.array(image)

        # Deteksi wajah di foto
        face_locations = face_recognition.face_locations(foto_array)
        if len(face_locations) == 0:
            return jsonify({
                "sukses": False,
                "pesan": "Wajah tidak terdeteksi. Pastikan wajah terlihat jelas."
            })

        # Encode wajah yang terdeteksi
        face_encodings = face_recognition.face_encodings(foto_array, face_locations)

        # Load data wajah terdaftar
        known_encodings, known_names = load_encodings()
        if len(known_encodings) == 0:
            return jsonify({
                "sukses": False,
                "pesan": "Belum ada data wajah terdaftar di server."
            })

        # Cocokkan wajah
        nama_dikenali = None
        for face_enc in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_enc, tolerance=0.5)
            distances = face_recognition.face_distance(known_encodings, face_enc)

            if True in matches:
                best_idx = np.argmin(distances)
                if matches[best_idx]:
                    nama_dikenali = known_names[best_idx]
                    break

        if not nama_dikenali:
            return jsonify({
                "sukses": False,
                "pesan": "Wajah tidak dikenali. Belum terdaftar."
            })

        # Ambil NIM dari database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT nim FROM mahasiswa WHERE nama = ?", (nama_dikenali,))
        row = c.fetchone()
        nim = row[0] if row else "unknown"

        # Cek sudah absen hari ini belum
        tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
            SELECT id FROM absensi
            WHERE nim = ? AND tanggal = ?
        """, (nim, tanggal_hari_ini))
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
            "pesan": f"✅ {nama_dikenali} berhasil absen!"
        })

    except Exception as e:
        return jsonify({"sukses": False, "pesan": f"Error: {str(e)}"}), 500


# ─────────────────────────────────────────
#  ENDPOINT: REKAP ADMIN
# ─────────────────────────────────────────
@app.route("/rekap", methods=["GET"])
def rekap():
    tanggal = request.args.get("tanggal", datetime.now().strftime("%Y-%m-%d"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT nim, nama, tanggal, waktu, status, device
        FROM absensi
        WHERE tanggal = ?
        ORDER BY waktu ASC
    """, (tanggal,))
    rows = c.fetchall()
    conn.close()

    data = [{
        "nim": r[0],
        "nama": r[1],
        "tanggal": r[2],
        "waktu": r[3],
        "status": r[4],
        "device": r[5]
    } for r in rows]

    return jsonify({
        "tanggal": tanggal,
        "total_hadir": len(data),
        "data": data
    })


# ─────────────────────────────────────────
#  ENDPOINT: REKAP SEMUA TANGGAL
# ─────────────────────────────────────────
@app.route("/rekap/semua", methods=["GET"])
def rekap_semua():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT nim, nama, tanggal, waktu, status, device
        FROM absensi
        ORDER BY tanggal DESC, waktu ASC
    """)
    rows = c.fetchall()
    conn.close()

    data = [{
        "nim": r[0],
        "nama": r[1],
        "tanggal": r[2],
        "waktu": r[3],
        "status": r[4],
        "device": r[5]
    } for r in rows]

    return jsonify({"total": len(data), "data": data})


# ─────────────────────────────────────────
#  ENDPOINT: DAFTAR MAHASISWA
# ─────────────────────────────────────────
@app.route("/mahasiswa", methods=["GET"])
def daftar_mahasiswa():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nim, nama, created_at FROM mahasiswa ORDER BY nama")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"nim": r[0], "nama": r[1], "terdaftar": r[2]} for r in rows])


# ─────────────────────────────────────────
#  ENDPOINT: TAMBAH MAHASISWA
# ─────────────────────────────────────────
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
#  JALANKAN SERVER
# ─────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server berjalan di port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
