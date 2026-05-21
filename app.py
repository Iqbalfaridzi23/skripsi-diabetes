import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sqlite3
import re
import hashlib
from datetime import datetime, date
from fpdf import FPDF

# ==============================================================================
# 1. KONFIGURASI HALAMAN & DATABASE
# ==============================================================================
st.set_page_config(page_title="Skrining Diabetes", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
        [data-testid="stNumberInputStepUp"] {display: none;}
        [data-testid="stNumberInputStepDown"] {display: none;}
        input[type="number"]::-webkit-inner-spin-button, 
        input[type="number"]::-webkit-outer-spin-button {
            -webkit-appearance: none; margin: 0;
        }
        .judul-utama { text-align: center; color: #2C3E50; font-size: 40px; font-weight: bold; }
        .sub-judul { text-align: center; color: #7F8C8D; font-size: 20px; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('skripsi_diabetes.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT, email TEXT UNIQUE, password TEXT, 
            tgl_lahir TEXT, gender TEXT, role TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riwayat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT, nama_pasien TEXT, usia INTEGER, gender TEXT, 
            urea REAL, cr REAL, hba1c REAL, chol REAL, tg REAL, 
            hdl REAL, ldl REAL, vldl REAL, bmi REAL,
            hasil TEXT, probabilitas REAL, waktu TIMESTAMP
        )
    ''')
    
    admin_email = "admin@admin.com"
    admin_password_hashed = hash_password("admin1234")
    
    cursor.execute("SELECT * FROM users WHERE email=?", (admin_email,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (nama, email, password, tgl_lahir, gender, role) VALUES (?,?,?,?,?,?)",
                       ("Administrator", admin_email, admin_password_hashed, "1990-01-01", "Laki-laki", "admin"))
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

@st.cache_resource
def load_assets():
    try:
        model = joblib.load('model_gradient_boosting.pkl')
        scaler = joblib.load('scaler.pkl')
        return model, scaler
    except:
        return None, None

model, scaler = load_assets()

def hitung_umur(tgl_lahir_str):
    try:
        birth_date = datetime.strptime(tgl_lahir_str, '%Y-%m-%d').date()
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return 0

# ==============================================================================
# FUNGSI UNTUK GENERATE PDF
# ==============================================================================
def buat_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Hasil Skrining Risiko Diabetes Melitus", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Dicetak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Data Pasien:", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Nama      : {data['nama_pasien']}", ln=True)
    pdf.cell(200, 8, txt=f"Usia      : {data['usia']} Tahun", ln=True)
    pdf.cell(200, 8, txt=f"Gender    : {data['gender']}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Hasil Laboratorium Medis:", ln=True)
    pdf.set_font("Arial", size=12)
    
    parameter = ['BMI', 'HbA1c', 'Urea', 'Kreatinin', 'Kolesterol', 'Trigliserida', 'HDL', 'LDL', 'VLDL']
    nilai = [data['bmi'], data['hba1c'], data['urea'], data['cr'], data['chol'], data['tg'], data['hdl'], data['ldl'], data['vldl']]
    
    for p, n in zip(parameter, nilai):
        pdf.cell(100, 8, txt=f"{p}: {n}", ln=True)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"DIAGNOSIS SISTEM: {data['hasil']} (Keyakinan: {data['probabilitas']}%)", ln=True, align='C')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 11)
    pdf.multi_cell(0, 8, txt=f"Saran Medis: {data['saran']}")
    
    return pdf.output(dest='S').encode('latin-1')

# ==============================================================================
# MANAJEMEN STATE (SESI)
# ==============================================================================
if 'is_auth' not in st.session_state:
    st.session_state['is_auth'] = False
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Beranda'

# ==============================================================================
# A. TAMPILAN SEBELUM LOGIN 
# ==============================================================================
if not st.session_state['is_auth']:
    
    if st.session_state['current_page'] != 'Auth':
        col_logo, col_nav, col_btn = st.columns([2, 6, 2])
        with col_logo:
            st.markdown("### 🩺 DiabetesCare")
        with col_nav:
            nav_selection = st.radio("Navigasi", ["Beranda", "Manual Book", "Tentang Sistem"], horizontal=True, label_visibility="collapsed")
        with col_btn:
            if st.button("🔑 Masuk / Daftar", type="primary", use_container_width=True):
                st.session_state['current_page'] = 'Auth'
                st.rerun()
                
        st.session_state['current_page'] = nav_selection
        st.divider()

    # --------------------------------------------------------------------------
    # PAGE: BERANDA
    # --------------------------------------------------------------------------
    if st.session_state['current_page'] == 'Beranda':
        st.markdown("<div class='judul-utama'>Deteksi Dini Risiko Diabetes Melitus</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-judul'>Langkah kecil hari ini untuk kesehatan masa depan yang lebih baik.</div>", unsafe_allow_html=True)
        
        st.header("Apa itu Diabetes Melitus?")
        st.markdown("""
        **Diabetes Melitus (DM)** adalah penyakit gangguan metabolik menahun yang ditandai oleh peningkatan kadar gula darah (glukosa) melebihi batas normal. Kondisi ini terjadi ketika pankreas tidak lagi mampu memproduksi hormon insulin secara memadai (Tipe 1), atau ketika tubuh tidak dapat menggunakan insulin yang diproduksi secara efektif (Tipe 2).
        
        **Mengapa Penyakit Ini Berbahaya?**
        Penyakit ini sering dijuluki sebagai *"The Silent Killer"* (Pembunuh Diam-diam). Banyak orang tidak menyadari bahwa mereka mengidap diabetes hingga komplikasi serius mulai muncul. Jika dibiarkan tanpa penanganan, tingginya gula darah dapat merusak pembuluh darah besar dan kecil, yang berujung pada:
        * **Gagal Ginjal (Nefropati Diabetik)**
        * **Serangan Jantung dan Stroke**
        * **Kerusakan Saraf (Neuropati)** yang bisa berujung pada amputasi anggota tubuh.
        * **Kebutaan (Retinopati Diabetik)**
        
        ### 🚨 Jangan Tunggu Sampai Terlambat!
        Fase **Pra-Diabetes** adalah fase emas di mana lonjakan gula darah masih bisa dibalikkan menjadi normal dengan diet dan olahraga. Sayangnya, fase ini sering kali tidak memiliki gejala sama sekali. 
        
        Oleh karena itu, **skrining dini sangatlah krusial**. Dengan melakukan skrining secara berkala menggunakan hasil uji laboratorium Anda, sistem kami dapat mendeteksi risiko tersebut secara akurat. **Mari ambil kendali atas kesehatan Anda. Klik tombol 'Masuk / Daftar' di pojok kanan atas sekarang untuk mulai melakukan skrining mandiri secara gratis!**
        """)

    # --------------------------------------------------------------------------
    # PAGE: MANUAL BOOK
    # --------------------------------------------------------------------------
    elif st.session_state['current_page'] == 'Manual Book':
        st.header("📖 Buku Panduan Penggunaan Aplikasi")
        st.markdown("""
        Selamat datang di Sistem Skrining Diabetes. Aplikasi ini dirancang agar mudah digunakan oleh masyarakat umum maupun praktisi kesehatan. Ikuti panduan detail berikut untuk memulai:
        
        ### Tahap 1: Pendaftaran Akun (Registrasi)
        1. Klik tombol merah/biru bertuliskan **"Masuk / Daftar"** di pojok kanan atas layar Anda.
        2. Pilih menu **"Daftar Akun Baru"**.
        3. Isi seluruh formulir data diri Anda. Pastikan:
           * Email menggunakan format yang valid (contoh: `nama@gmail.com`).
           * Password minimal berjumlah 8 karakter.
           * Tanggal lahir diisi dengan benar, karena sistem akan otomatis menghitung umur Anda untuk keperluan medis.
        4. Klik tombol **Daftar Akun**. Jika berhasil, Anda akan diminta untuk masuk (login).
        
        ### Tahap 2: Masuk (Login)
        1. Di halaman autentikasi, pilih menu **"Login"**.
        2. Masukkan Email dan Password yang telah Anda daftarkan.
        3. Klik **Login**. Anda akan diarahkan ke halaman utama pengguna (Skrining).
        
        ### Tahap 3: Melakukan Skrining Mandiri
        1. Di panel menu sebelah kiri, pilih menu **"Skrining Diabetes"**.
        2. Siapkan lembar hasil uji laboratorium darah Anda (Bawaan dari klinik/rumah sakit).
        3. Masukkan 11 angka nilai laboratorium (seperti HbA1c, Glukosa, Kolesterol, dll) ke dalam kotak yang tersedia. 
        4. **Catatan:** Angka tidak boleh minus (negatif) dan tidak boleh dibiarkan kosong (0.0). Jika ada form yang belum diisi, sistem akan memunculkan tulisan peringatan merah.
        5. Klik tombol **"Cek Status Kesehatan"**. Hasil diagnosis beserta tingkat keyakinan (probabilitas) akan langsung muncul di layar.
        
        ### Tahap 4: Mencetak PDF dan Melihat Riwayat
        1. Pilih menu **"Riwayat Pemeriksaan"** di panel menu sebelah kiri.
        2. Di halaman ini, Anda akan melihat seluruh riwayat tes yang pernah Anda lakukan secara lengkap.
        3. Untuk memberikan hasil ke dokter Anda, pilih ID pemeriksaan pada menu cetak di bawah tabel, lalu klik **"Unduh PDF"**. File siap untuk di-*print*!
        """)

    # --------------------------------------------------------------------------
    # PAGE: TENTANG SISTEM
    # --------------------------------------------------------------------------
    elif st.session_state['current_page'] == 'Tentang Sistem':
        st.header("ℹ️ Tentang Sistem & Teknologi")
        st.markdown("""
        Sistem Pendukung Keputusan Klinis ini dikembangkan sebagai bagian dari penelitian Skripsi di bidang Teknik Informatika. Berikut adalah rincian teknis di balik kecerdasan aplikasi ini:
        
        ### 🧠 Algoritma Kecerdasan Buatan (Machine Learning)
        * **Model Utama: Gradient Boosting Classifier** Algoritma *ensemble learning* ini dipilih karena kemampuannya membangun ratusan pohon keputusan (*decision trees*) secara bertahap, di mana setiap pohon belajar dari kesalahan pohon sebelumnya. Hal ini sangat efektif untuk memetakan pola kompleks dari rekam medis manusia.
        * **Prapemrosesan (Handling Imbalanced Data): SMOTE & Bootstrapping** Karena data pasien "Pra-Diabetes" sangat minim, sistem menggunakan teknik *Synthetic Minority Over-sampling Technique* (SMOTE) dan *Bootstrapping* terisolasi pada data latih (rasio 70:30) untuk menciptakan data sintetis yang berkualitas tanpa mengalami *data leakage* (kebocoran data). Evaluasi akhir menunjukkan sistem memiliki **akurasi realistis sebesar 96.45%**.
            
        ### 📊 Data dan Parameter Klinis
        Dataset penelitian yang digunakan melatih model ini diekstraksi dari rekam medis pasien otentik. Model menganalisis **11 parameter uji laboratorium kritis**, yaitu: 
        Usia, Jenis Kelamin, BMI, Tekanan Darah/Urea, Kreatinin, HbA1c, Kolesterol Total, Trigliserida, HDL, LDL, dan VLDL.
        
        ### 💻 Teknologi Pengembangan (Tech Stack)
        * **Bahasa Pemrograman:** Python 3.10+
        * **Antarmuka Web:** Streamlit Framework (Untuk UI yang interaktif dan responsif).
        * **Basis Data:** SQLite (Relational Database tertanam untuk rekam medis terenkripsi lokal).
        * **Modul Ekspor:** Pustaka FPDF untuk meng- *generate* hasil cetak PDF otomatis.
        
        ---
        **Pengembang:** **Iqbal Alfaridzi Balman** (NIM: 535220248)  
        Program Studi Teknik Informatika, Universitas Tarumanagara.
        """)

    # --------------------------------------------------------------------------
    # PAGE: AUTH (PORTAL LOGIN & REGISTRASI TERISOLASI)
    # --------------------------------------------------------------------------
    elif st.session_state['current_page'] == 'Auth':
        if st.button("⬅️ Kembali ke Beranda"):
            st.session_state['current_page'] = 'Beranda'
            st.rerun()
            
        st.markdown("<h2 style='text-align: center;'>Portal Autentikasi Pengguna</h2>", unsafe_allow_html=True)
        
        # PERBAIKAN POIN 2: Menggunakan st.radio agar form ter-reset otomatis setiap pindah pilihan
        mode_auth = st.radio("Pilih Mode:", ["🔑 Masuk (Login)", "📝 Daftar Akun Baru"], horizontal=True)
        
        if mode_auth == "🔑 Masuk (Login)":
            st.subheader("Sudah punya akun? Silakan masuk.")
            # Tambahan clear_on_submit untuk mereset isi setelah tombol ditekan
            with st.form("form_login", clear_on_submit=True):
                l_email = st.text_input("Email")
                l_pass = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Login", use_container_width=True)
                
                if submit_login:
                    hashed_l_pass = hash_password(l_pass)
                    cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (l_email, hashed_l_pass))
                    user = cursor.fetchone()
                    if user:
                        st.session_state['is_auth'] = True
                        st.session_state['role'] = user[6] if len(user) > 6 and user[6] else "user"
                        st.session_state['user_info'] = {
                            'nama': user[1], 'email': user[2], 'tgl_lahir': user[4], 'gender': user[5]
                        }
                        st.session_state['current_page'] = 'Admin' if st.session_state['role'] == 'admin' else 'Skrining'
                        st.rerun()
                    else:
                        st.error("Email atau Password salah!")
                        
        elif mode_auth == "📝 Daftar Akun Baru":
            st.subheader("Belum punya akun? Daftar di sini.")
            with st.form("form_registrasi", clear_on_submit=True):
                r_nama = st.text_input("Nama Lengkap")
                r_email = st.text_input("Email")
                r_pass = st.text_input("Password (Minimal 8 Karakter)", type="password")
                r_tgl = st.date_input("Tanggal Lahir", min_value=date(1940, 1, 1), max_value=date.today())
                r_gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
                submit_reg = st.form_submit_button("Daftar Akun Sekarang", use_container_width=True)
                
                if submit_reg:
                    pola_email = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(com|co\.id|ac\.id|go\.id|net|org|id)$'
                    
                    if not r_nama.strip():
                        st.error("❌ Nama Lengkap wajib diisi!")
                    elif not r_email.strip():
                        st.error("❌ Email wajib diisi!")
                    elif not r_pass.strip():
                        st.error("❌ Password wajib diisi!")
                    elif len(r_pass) < 8:
                        st.warning("❌ Password harus minimal 8 karakter.")
                    elif not re.match(pola_email, r_email):
                        st.warning("❌ Format email tidak valid! (Contoh: pengguna@gmail.com)")
                    else:
                        cursor.execute("SELECT * FROM users WHERE email=?", (r_email,))
                        if cursor.fetchone():
                            st.error("Email sudah terdaftar!")
                        else:
                            hashed_r_pass = hash_password(r_pass)
                            cursor.execute("INSERT INTO users (nama, email, password, tgl_lahir, gender, role) VALUES (?,?,?,?,?,?)", 
                                        (r_nama, r_email, hashed_r_pass, str(r_tgl), r_gender, "user"))
                            cursor.connection.commit()
                            st.success("✅ Registrasi Berhasil! Silakan klik tab 'Masuk (Login)' untuk mengakses akun Anda.")
    st.stop()

# ==============================================================================
# B. TAMPILAN SETELAH LOGIN (SIDEBAR & FITUR UTAMA)
# ==============================================================================
if st.session_state['is_auth']:
    
    with st.sidebar:
        st.title("🧭 Navigasi Menu")
        st.write(f"Halo, **{st.session_state['user_info']['nama']}**")
        
        if st.session_state.get('role') == 'admin':
            opsi_menu = ["👑 Panel Admin"]
        else:
            opsi_menu = ["🔍 Skrining Diabetes", "📜 Riwayat Pemeriksaan"]
            
        menu = st.radio("Pilih Halaman:", opsi_menu)
        
        st.divider()
        if st.button("🚪 Keluar (Logout)", type="primary"):
            st.session_state['is_auth'] = False
            st.session_state['current_page'] = 'Beranda'
            st.rerun()

    # --------------------------------------------------------------------------
    # FITUR: SKRINING (USER ONLY)
    # --------------------------------------------------------------------------
    if st.session_state.get('role') != 'admin' and menu == "🔍 Skrining Diabetes":
        st.header("Form Uji Skrining Laboratorium")
        user_info = st.session_state['user_info']
        user_age = hitung_umur(user_info['tgl_lahir'])
        
        with st.form("skrining_form"):
            col_prof1, col_prof2, col_prof3 = st.columns(3)
            with col_prof1:
                st.text_input("Nama Pengguna", value=user_info['nama'], disabled=True)
            with col_prof2:
                st.number_input("Umur Pengguna", value=user_age, disabled=True)
            with col_prof3:
                st.text_input("Jenis Kelamin", value=user_info['gender'], disabled=True)
            
            st.divider()
            st.info("Ketikkan angka persis seperti yang tertera di lembar uji laboratorium Anda.")
            
            col1, col2 = st.columns(2)
            with col1:
                bmi = st.number_input("BMI (kg/m²)", min_value=0.0, value=0.0, format="%.1f")
                hba1c = st.number_input("Kadar HbA1c (%)", min_value=0.0, value=0.0, format="%.1f")
                urea = st.number_input("Urea", min_value=0.0, value=0.0, format="%.1f")
                cr = st.number_input("Cr (Kreatinin)", min_value=0.0, value=0.0, format="%.1f")
            with col2:
                chol = st.number_input("Chol (Kolesterol)", min_value=0.0, value=0.0, format="%.1f")
                tg = st.number_input("TG (Trigliserida)", min_value=0.0, value=0.0, format="%.1f")
                hdl = st.number_input("HDL", min_value=0.0, value=0.0, format="%.1f")
                ldl = st.number_input("LDL", min_value=0.0, value=0.0, format="%.1f")
                vldl = st.number_input("VLDL", min_value=0.0, value=0.0, format="%.1f")

            submit = st.form_submit_button("Cek Status Kesehatan", use_container_width=True)

        if submit:
            parameter_kosong = []
            if bmi == 0.0: parameter_kosong.append("BMI")
            if hba1c == 0.0: parameter_kosong.append("HbA1c")
            if urea == 0.0: parameter_kosong.append("Urea")
            if cr == 0.0: parameter_kosong.append("Kreatinin")
            if chol == 0.0: parameter_kosong.append("Kolesterol")
            if tg == 0.0: parameter_kosong.append("Trigliserida")
            if hdl == 0.0: parameter_kosong.append("HDL")
            if ldl == 0.0: parameter_kosong.append("LDL")
            if vldl == 0.0: parameter_kosong.append("VLDL")
            
            if len(parameter_kosong) > 0:
                st.error(f"⚠️ Form Tidak Lengkap! Anda belum mengisi parameter berikut: **{', '.join(parameter_kosong)}**")
            else:
                g_num = 1 if user_info['gender'] == "Laki-laki" else 0
                features = np.array([[g_num, user_age, urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi]])
                features_scaled = scaler.transform(features)
                pred = model.predict(features_scaled)[0]
                proba = max(model.predict_proba(features_scaled)[0]) * 100
                
                labels = {0: "Normal", 1: "Pra-Diabetes", 2: "Diabetes"}
                hasil_diag = labels[pred]
                
                # PERBAIKAN POIN 1: Menambahkan logika Saran Medis
                if hasil_diag == "Normal":
                    saran = "Pertahankan gaya hidup sehat, rutin berolahraga, dan jaga pola makan Anda."
                elif hasil_diag == "Pra-Diabetes":
                    saran = "Segera periksa ke dokter. Kurangi konsumsi gula harian, perbanyak serat, dan mulai rutin berolahraga untuk mencegah naiknya gula darah."
                else:
                    saran = "Segera konsultasikan dengan dokter atau fasilitas kesehatan terdekat untuk mendapatkan penanganan dan pengobatan medis yang tepat."
                
                st.divider()
                st.subheader(f"Hasil Diagnosis: {hasil_diag}")
                st.info(f"Tingkat Keyakinan Sistem: {proba:.2f}%")
                st.warning(f"💡 **Saran Medis:** {saran}")
                
                cursor.execute('''INSERT INTO riwayat 
                                (user_email, nama_pasien, usia, gender, urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi, hasil, probabilitas, waktu) 
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                               (user_info['email'], user_info['nama'], user_age, user_info['gender'], 
                                urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi, hasil_diag, proba, datetime.now()))
                conn.commit()
                st.success("✅ Data berhasil disimpan! Silakan buka menu 'Riwayat Pemeriksaan' untuk mengunduh PDF.")

    # --------------------------------------------------------------------------
    # FITUR: RIWAYAT PEMERIKSAAN & CETAK PDF (USER ONLY)
    # --------------------------------------------------------------------------
    elif st.session_state.get('role') != 'admin' and menu == "📜 Riwayat Pemeriksaan":
        st.header("Riwayat & Cetak Rekam Medis")
        user_email = st.session_state['user_info']['email']
        
        df_riwayat = pd.read_sql_query(f"SELECT * FROM riwayat WHERE user_email='{user_email}' ORDER BY waktu DESC", conn)
        
        if not df_riwayat.empty:
            df_display = df_riwayat.drop(columns=['user_email'])
            st.dataframe(df_display, use_container_width=True)
            
            st.divider()
            st.subheader("📄 Unduh Rekam Medis (PDF)")
            st.write("Masukkan ID riwayat dari tabel di atas yang ingin Anda cetak untuk diberikan kepada dokter.")
            
            col_pdf1, col_pdf2 = st.columns([1, 2])
            with col_pdf1:
                pilih_id = st.selectbox("Pilih ID Riwayat:", df_riwayat['id'].tolist())
            
            if pilih_id:
                data_baris = df_riwayat[df_riwayat['id'] == pilih_id].iloc[0]
                
                # Mendefinisikan ulang saran untuk dimasukkan ke dalam PDF
                if data_baris['hasil'] == "Normal":
                    saran_pdf = "Pertahankan gaya hidup sehat, rutin berolahraga, dan jaga pola makan Anda."
                elif data_baris['hasil'] == "Pra-Diabetes":
                    saran_pdf = "Segera periksa ke dokter. Kurangi konsumsi gula harian, perbanyak serat, dan mulai rutin berolahraga."
                else:
                    saran_pdf = "Segera konsultasikan dengan dokter untuk mendapatkan penanganan medis yang tepat."
                    
                data_pdf = {
                    'nama_pasien': data_baris['nama_pasien'], 'usia': data_baris['usia'], 'gender': data_baris['gender'],
                    'bmi': data_baris['bmi'], 'hba1c': data_baris['hba1c'], 'urea': data_baris['urea'], 
                    'cr': data_baris['cr'], 'chol': data_baris['chol'], 'tg': data_baris['tg'], 
                    'hdl': data_baris['hdl'], 'ldl': data_baris['ldl'], 'vldl': data_baris['vldl'], 
                    'hasil': data_baris['hasil'], 'probabilitas': round(data_baris['probabilitas'], 2),
                    'saran': saran_pdf
                }
                pdf_bytes = buat_pdf(data_pdf)
                with col_pdf1:
                    st.download_button(label="📥 Unduh File PDF", data=pdf_bytes, file_name=f"Rekam_Medis_{pilih_id}.pdf", mime="application/pdf", type="primary")
        else:
            st.warning("Belum ada riwayat prediksi yang tersimpan.")

    # --------------------------------------------------------------------------
    # FITUR: PANEL ADMIN 
    # --------------------------------------------------------------------------
    elif st.session_state.get('role') == 'admin' and menu == "👑 Panel Admin":
        st.header("Manajemen Data Pasien Terpadu (Akses Khusus Administrator)")
        df_admin = pd.read_sql_query("SELECT * FROM riwayat", conn)
        
        if not df_admin.empty:
            st.write("Silakan klik dua kali pada sel tabel di bawah ini untuk mengedit nilai. Perubahan akan langsung disimpan otomatis ke database SQLite.")
            edited_df = st.data_editor(df_admin, num_rows="dynamic", use_container_width=True)
            
            st.divider()
            col_del1, col_del2 = st.columns(2)
            with col_del1:
                st.write("#### Hapus Data Pasien")
                id_hapus = st.number_input("Masukkan ID Riwayat yang ingin dihapus:", min_value=0, value=0, step=1)
                if st.button("Hapus Data", type="primary"):
                    cursor.execute("DELETE FROM riwayat WHERE id=?", (id_hapus,))
                    conn.commit()
                    st.success(f"Data dengan ID {id_hapus} berhasil dihapus permanen!")
                    st.rerun()
        else:
            st.info("Database riwayat masih kosong.")