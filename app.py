import os
import psycopg2
import time
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kunci_rahasia_super_aman')

# --- KONEKSI DATABASE (VERSI CLOUD-READY) ---
def get_db_connection():
    # Render biasanya memberikan DATABASE_URL secara otomatis
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Jika di Cloud (Render/Railway)
        return psycopg2.connect(db_url)
    else:
        # Jika di Laptop (Docker Lokal)
        return psycopg2.connect(
            host="db",
            database=os.environ.get('DB_NAME', 'kasir_db'),
            user=os.environ.get('DB_USER', 'kasir'),
            password=os.environ.get('DB_PASS', 'rahasia123')
        )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabel-tabel utama
    cur.execute('CREATE TABLE IF NOT EXISTS barang (id SERIAL PRIMARY KEY, nama VARCHAR(100) NOT NULL, harga INTEGER NOT NULL);')
    cur.execute('CREATE TABLE IF NOT EXISTS transaksi (id SERIAL PRIMARY KEY, total INTEGER NOT NULL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    cur.execute('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(200) NOT NULL);')
    
    # Buat admin default jika belum ada
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if cur.fetchone() is None:
        pass_hash = generate_password_hash('admin123')
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('admin', pass_hash))
    
    conn.commit()
    cur.close()
    conn.close()

# --- SECURITY CHECK ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- TAMPILAN (UI) ---
HTML_LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Kasir Cloud</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; margin: 0; padding: 20px; background: #f4f7f6; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4
