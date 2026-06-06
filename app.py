from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, os, base64, io, pickle
from datetime import datetime
from PIL import Image
import numpy as np

app = Flask(__name__)
CORS(app)
DB_PATH = "absensi.db"
DATASET_DIR = "dataset"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS mahasiswa (id INTEGER PRIMARY KEY, nim TEXT UNIQUE, nama TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS absensi (id INTEGER PRIMARY KEY, nim TEXT, nama TEXT, tanggal TEXT, waktu TEXT, status TEXT, device TEXT)")
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Server Aktif"})

@app.route("/absen", methods=["POST"])
def absen():
    try:
        data = request.get_json()
        foto_bytes = base64.b64decode(data["foto_base64"])
        device_info = data.get("device", "unknown")

        # Simpan foto sementara
        image = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
        foto_path = "/tmp/foto_absen.jpg"
        image.save(foto_path)

        # Load encodings
        if not os.path.exists("face_encodings.pkl"):
            return jsonify({"sukses": False, "pesan": "Data wajah belum ada di server"})

        import face_recognition
        with open("face_encodings.pkl", "rb") as f:
            data_enc = pickle.load(f)

        foto_array = np.array(image)
        face_locs = face_recognition.face_locations(foto_array)
        if not face_locs:
            return jsonify({"sukses": False, "pesan": "Wajah tidak terdeteksi"})

        face_encs = face_recognition.face_encodings(foto_array, face_locs)
        nama_dikenali = None

        for enc in face_encs:
            matches = face_recognition.compare_faces(data_enc["encodings"], enc, tolerance=0.5)
            distances = face_recognition.face_distance(data_enc["encodings"], enc)
            if True in matches:
                best = np.argmin(distances)
                if matches[best]:
                    nama_dikenali = data_enc["names"][best]
                    break

        if not nama_dikenali:
            return jsonify({"sukses": False, "pesan": "Wajah tidak dikenali"})

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT nim FROM mahasiswa WHERE nama=?", (nama_dikenali,))
        row = c.fetchone()
        nim = row[0] if row else "unknown"
        tanggal = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT id FROM absensi WHERE nim=? AND tanggal=?", (nim, tanggal))
        if c.fetchone():
            conn.close()
            return jsonify({"sukses": True, "sudah_absen": True, "nama": nama_dikenali, "nim": nim, "pesan": f"{nama_dikenali} sudah absen hari ini"})

        waktu = datetime.now().strftime("%H:%M:%S")
        c.execute("INSERT INTO absensi (nim,nama,tanggal,waktu,status,device) VALUES (?,?,?,?,?,?)",
                  (nim, nama_dikenali, tanggal, waktu, "HADIR", device_info))
        conn.commit()
        conn.close()
        return jsonify({"sukses": True, "sudah_absen": False, "nama": nama_dikenali, "nim": nim, "waktu": waktu, "tanggal": tanggal, "pesan": f"{nama_dikenali} berhasil absen!"})
    except Exception as e:
        return jsonify({"sukses": False, "pesan": str(e)}), 500

@app.route("/rekap")
def rekap():
    tanggal = request.args.get("tanggal", datetime.now().strftime("%Y-%m-%d"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nim,nama,tanggal,waktu,status,device FROM absensi WHERE tanggal=? ORDER BY waktu", (tanggal,))
    rows = c.fetchall()
    conn.close()
    data = [{"nim":r[0],"nama":r[1],"tanggal":r[2],"waktu":r[3],"status":r[4],"device":r[5]} for r in rows]
    return jsonify({"tanggal": tanggal, "total_hadir": len(data), "data": data})

@app.route("/rekap/semua")
def rekap_semua():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nim,nama,tanggal,waktu,status,device FROM absensi ORDER BY tanggal DESC,waktu")
    rows = c.fetchall()
    conn.close()
    data = [{"nim":r[0],"nama":r[1],"tanggal":r[2],"waktu":r[3],"status":r[4],"device":r[5]} for r in rows]
    return jsonify({"total": len(data), "data": data})

@app.route("/mahasiswa")
def daftar_mahasiswa():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nim,nama FROM mahasiswa ORDER BY nama")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"nim":r[0],"nama":r[1]} for r in rows])

@app.route("/mahasiswa/tambah", methods=["POST"])
def tambah_mahasiswa():
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO mahasiswa (nim,nama) VALUES (?,?)", (data["nim"], data["nama"]))
        conn.commit()
        return jsonify({"sukses": True, "pesan": f"{data['nama']} berhasil ditambahkan"})
    except:
        return jsonify({"sukses": False, "pesan": "NIM sudah terdaftar"})
    finally:
        conn.close()

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
