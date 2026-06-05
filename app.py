from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect("absensi.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS mahasiswa (id INTEGER PRIMARY KEY, nim TEXT UNIQUE, nama TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS absensi (id INTEGER PRIMARY KEY, nim TEXT, nama TEXT, tanggal TEXT, waktu TEXT, status TEXT, device TEXT)")
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Server Aktif"})

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
