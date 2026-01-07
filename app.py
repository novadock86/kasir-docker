import os
import psycopg2
import time
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_super_aman'

# --- KONEKSI DATABASE ---
def get_db_connection():
    return psycopg2.connect(
        host="db",
        database=os.environ.get('DB_NAME', 'kasir_db'),
        user=os.environ.get('DB_USER', 'kasir'),
        password=os.environ.get('DB_PASS', 'rahasia123')
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # 1. Tabel Barang
    cur.execute('CREATE TABLE IF NOT EXISTS barang (id SERIAL PRIMARY KEY, nama VARCHAR(100) NOT NULL, harga INTEGER NOT NULL);')
    # 2. Tabel Transaksi
    cur.execute('CREATE TABLE IF NOT EXISTS transaksi (id SERIAL PRIMARY KEY, total INTEGER NOT NULL, waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    # 3. Tabel Users
    cur.execute('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password VARCHAR(200) NOT NULL);')
    
    # Cek admin default
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if cur.fetchone() is None:
        pass_hash = generate_password_hash('admin123')
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", ('admin', pass_hash))
    
    conn.commit()
    cur.close()
    conn.close()

# --- PENJAGA LOGIN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- TEMPLATE HTML ---
LOGIN_HTML = '''
<!doctype html>
<html>
<head><title>Login Admin</title></head>
<body style="font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;">
    <form method="post" style="border:1px solid #ccc; padding:20px; border-radius:10px;">
        <h2>🔐 Login Kasir</h2>
        {% with msgs = get_flashed_messages() %}{% if msgs %}<p style="color:red;">{{msgs[0]}}</p>{% endif %}{% endwith %}
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit" style="width:100%;">Masuk</button>
        <p><small>User: admin | Pass: admin123</small></p>
    </form>
</body>
'''

DASHBOARD_HTML = '''
<body style="font-family:sans-serif; padding:20px;">
    <h1>🏪 KASIR SAKTI v2.0</h1>
    <a href="/logout">Keluar</a><hr>
    <div style="display:flex; gap:50px;">
        <div>
            <h3>Daftar Barang</h3>
            {% for item in barang %}
            <p>{{ item[1] }} - Rp {{ item[2] }} 
               <form action="/beli" method="post" style="display:inline;"><input type="hidden" name="harga" value="{{item[2]}}"><button type="submit">Jual</button></form>
            </p>
            {% endfor %}
        </div>
        <div style="background:#eee; padding:20px;">
            <h3>Input Stok</h3>
            <form action="/tambah" method="post">
                <input type="text" name="nama" placeholder="Nama" required><br>
                <input type="number" name="harga" placeholder="Harga" required><br><br>
                <button type="submit">Tambah</button>
            </form>
            <h4>Total Omzet: Rp {{ total }}</h4>
        </div>
    </div>
</body>
'''

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (request.form['username'],))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user[2], request.form['password']):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        flash('Salah password!')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM barang;')
    brg = cur.fetchall()
    cur.execute('SELECT SUM(total) FROM transaksi;')
    tot = cur.fetchone()[0] or 0
    cur.close()
    conn.close()
    return render_template_string(DASHBOARD_HTML, barang=brg, total=tot)

@app.route('/tambah', methods=['POST'])
@login_required
def tambah():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO barang (nama, harga) VALUES (%s, %s)', (request.form['nama'], request.form['harga']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/beli', methods=['POST'])
@login_required
def beli():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO transaksi (total) VALUES (%s)', (request.form['harga'],))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Mengambil port dari environment variable yang disediakan Cloud
    port = int(os.environ.get("PORT", 5000))
    
    time.sleep(10)
    try:
        init_db()
    except:
        pass
        
    app.run(host='0.0.0.0', port=port) # Hilangkan debug=True untuk hosting