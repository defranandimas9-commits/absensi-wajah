from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
CORS(app)
DB_PATH = "absensi.db"

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
        nama = data.get("nama")
        nim = data.get("nim")
        device = data.get("device", "desktop")
        if not nama or not nim:
            return jsonify({"sukses": False, "pesan": "Nama dan NIM wajib diisi"})
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        tanggal = datetime.now().strftime("%Y-%m-%d")
        waktu = datetime.now().strftime("%H:%M:%S")
        c.execute("SELECT id FROM absensi WHERE nim=? AND tanggal=?", (nim, tanggal))
        if c.fetchone():
            conn.close()
            return jsonify({"sukses": True, "sudah_absen": True, "nama": nama, "nim": nim, "pesan": f"{nama} sudah absen hari ini"})
        c.execute("INSERT INTO absensi (nim,nama,tanggal,waktu,status,device) VALUES (?,?,?,?,?,?)", (nim, nama, tanggal, waktu, "HADIR", device))
        conn.commit()
        conn.close()
        return jsonify({"sukses": True, "sudah_absen": False, "nama": nama, "nim": nim, "waktu": waktu, "tanggal": tanggal, "pesan": f"{nama} berhasil absen!"})
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
