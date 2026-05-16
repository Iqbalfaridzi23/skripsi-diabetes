import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sqlite3
import re
from datetime import datetime, date

# ==============================================================================
# 1. KONFIGURASI HALAMAN, DATABASE & CSS
# ==============================================================================
st.set_page_config(page_title="Sistem Skrining Diabetes", page_icon="🩺", layout="wide")

st.markdown("""
    <style>
        [data-testid="stNumberInputStepUp"] {display: none;}
        [data-testid="stNumberInputStepDown"] {display: none;}
        input[type="number"]::-webkit-inner-spin-button, 
        input[type="number"]::-webkit-outer-spin-button {
            -webkit-appearance: none; margin: 0;
        }
    </style>
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect('skripsi_diabetes.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tabel User
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT, email TEXT UNIQUE, password TEXT, 
            tgl_lahir TEXT, gender TEXT
        )
    ''')
    # Tabel Riwayat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riwayat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT, nama_pasien TEXT, usia INTEGER, gender TEXT, 
            urea REAL, cr REAL, hba1c REAL, chol REAL, tg REAL, 
            hdl REAL, ldl REAL, vldl REAL, bmi REAL,
            hasil TEXT, probabilitas REAL, waktu TIMESTAMP
        )
    ''')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ==============================================================================
# 2. LOAD MODEL & SCALER
# ==============================================================================
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
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return 0

# ==============================================================================
# 3. HALAMAN LOGIN & REGISTRASI
# ==============================================================================
if 'is_auth' not in st.session_state:
    st.session_state['is_auth'] = False

if not st.session_state['is_auth']:
    st.title("🏥 Sistem Informasi Skrining Diabetes")
    tab1, tab2 = st.tabs(["Masuk (Login)", "Daftar (Registrasi)"])
    
    with tab1:
        st.subheader("Silakan Login")
        l_email = st.text_input("Email", key="l_email")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (l_email, l_pass))
            user = cursor.fetchone()
            if user:
                st.session_state['is_auth'] = True
                st.session_state['user_info'] = {
                    'nama': user[1], 'email': user[2], 'tgl_lahir': user[4], 'gender': user[5]
                }
                st.success("Berhasil masuk!")
                st.rerun()
            else:
                st.error("Cek kembali email/password Anda")

    with tab2:
        st.subheader("Buat Akun Baru")
        r_nama = st.text_input("Nama Lengkap")
        r_email = st.text_input("Email")
        r_pass = st.text_input("Password (Minimal 8 Karakter)", type="password")
        r_tgl = st.date_input("Tanggal Lahir", min_value=date(1940, 1, 1), max_value=date.today())
        r_gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        
        if st.button("Daftar Akun"):
            pola_email = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            
            if len(r_pass) < 8:
                st.warning("Password harus mengisi minimal 8 karakter")
            elif not re.match(pola_email, r_email):
                st.warning("Format email tidak valid! (Contoh: pengguna@gmail.com)")
            else:
                cursor.execute("SELECT * FROM users WHERE email=?", (r_email,))
                if cursor.fetchone():
                    st.error("Email sudah digunakan")
                else:
                    cursor.execute("INSERT INTO users (nama, email, password, tgl_lahir, gender) VALUES (?,?,?,?,?)", 
                                (r_nama, r_email, r_pass, str(r_tgl), r_gender))
                    conn.commit()
                    st.success("Registrasi Berhasil! Silakan Login.")
    st.stop()

# ==============================================================================
# 4. NAVIGASI SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("🧭 Navigasi")
    st.write(f"Login sebagai: **{st.session_state['user_info']['nama']}**")
    
    # Menambahkan menu "Panduan Penggunaan"
    menu = st.radio("Pilih Halaman:", [
        "🔍 Skrining Diabetes", 
        "📜 Riwayat Pemeriksaan", 
        "📖 Panduan Penggunaan", 
        "ℹ️ Tentang Sistem", 
        "🚪 Keluar"
    ])

if menu == "🚪 Keluar":
    st.session_state['is_auth'] = False
    st.rerun()

# ==============================================================================
# 5. HALAMAN SKRINING 
# ==============================================================================
elif menu == "🔍 Skrining Diabetes":
    st.header("Form Skrining")
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
        st.info("Silakan ketikkan langsung hasil uji laboratorium Anda pada kotak di bawah ini.")
        
        col1, col2 = st.columns(2)
        with col1:
            bmi = st.number_input("BMI (Indeks Massa Tubuh)", value=0.0, format="%.1f")
            hba1c = st.number_input("Kadar HbA1c (%)", value=0.0, format="%.1f")
            urea = st.number_input("Urea", value=0.0, format="%.1f")
            cr = st.number_input("Cr (Kreatinin)", value=0.0, format="%.1f")
        with col2:
            chol = st.number_input("Chol (Kolesterol)", value=0.0, format="%.1f")
            tg = st.number_input("TG (Trigliserida)", value=0.0, format="%.1f")
            hdl = st.number_input("HDL", value=0.0, format="%.1f")
            ldl = st.number_input("LDL", value=0.0, format="%.1f")
            vldl = st.number_input("VLDL", value=0.0, format="%.1f")

        submit = st.form_submit_button("Cek Status Kesehatan", use_container_width=True)

    if submit:
        input_list = [bmi, hba1c, urea, cr, chol, tg, hdl, ldl, vldl]
        if any(v == 0.0 for v in input_list):
            st.error("⚠️ Gagal memproses! Mohon lengkapi seluruh form data laboratorium terlebih dahulu.")
        else:
            g_num = 1 if user_info['gender'] == "Laki-laki" else 0
            features = np.array([[g_num, user_age, urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi]])
            features_scaled = scaler.transform(features)
            pred = model.predict(features_scaled)[0]
            proba = max(model.predict_proba(features_scaled)[0]) * 100
            
            labels = {0: "Normal", 1: "Pra-Diabetes", 2: "Diabetes"}
            hasil_diag = labels[pred]
            
            st.divider()
            st.subheader(f"Hasil Diagnosis: {hasil_diag}")
            st.info(f"Tingkat Keyakinan Sistem: {proba:.2f}%")
            
            cursor.execute('''INSERT INTO riwayat 
                            (user_email, nama_pasien, usia, gender, urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi, hasil, probabilitas, waktu) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                           (user_info['email'], user_info['nama'], user_age, user_info['gender'], 
                            urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi, hasil_diag, proba, datetime.now()))
            conn.commit()

# ==============================================================================
# 6. HALAMAN RIWAYAT
# ==============================================================================
elif menu == "📜 Riwayat Pemeriksaan":
    st.header("Riwayat Prediksi Pengguna")
    user_email = st.session_state['user_info']['email']
    
    df_riwayat = pd.read_sql_query(f"SELECT nama_pasien, usia, gender, urea, cr, hba1c, chol, tg, hdl, ldl, vldl, bmi, hasil, probabilitas, waktu FROM riwayat WHERE user_email='{user_email}' ORDER BY waktu DESC", conn)
    
    if not df_riwayat.empty:
        st.dataframe(df_riwayat, use_container_width=True)
    else:
        st.warning("Belum ada riwayat prediksi.")

# ==============================================================================
# 7. HALAMAN PANDUAN PENGGUNAAN (MANUAL BOOK)
# ==============================================================================
elif menu == "📖 Panduan Penggunaan":
    st.header("Buku Panduan Penggunaan Sistem (Manual Book)")
    st.markdown("Selamat datang di aplikasi Sistem Informasi Skrining Diabetes. Berikut adalah panduan langkah demi langkah untuk menggunakan fitur-fitur di dalam aplikasi ini:")
    
    with st.expander("1. Cara Mendaftar dan Masuk (Login)", expanded=True):
        st.markdown("""
        **Cara Mendaftar (Registrasi):**
        1. Pada halaman awal, pilih *tab* **Daftar (Registrasi)**.
        2. Isi seluruh kolom yang tersedia: Nama Lengkap, Email (menggunakan @ dan domain), Password (minimal 8 karakter), Tanggal Lahir, dan Jenis Kelamin.
        3. Klik tombol **Daftar Akun**. Jika berhasil, akan muncul notifikasi berwarna hijau.
        
        **Cara Masuk (Login):**
        1. Pilih *tab* **Masuk (Login)**.
        2. Masukkan Email dan Password yang telah Anda daftarkan.
        3. Klik tombol **Login**. Anda akan diarahkan ke dalam sistem.
        """)

    with st.expander("2. Cara Melakukan Skrining Kesehatan"):
        st.markdown("""
        1. Setelah Login, pilih menu **🔍 Skrining Diabetes** di panel navigasi sebelah kiri.
        2. Anda akan melihat Nama, Umur, dan Jenis Kelamin Anda sudah terisi secara otomatis berdasarkan data akun Anda.
        3. Isi ke-9 parameter laboratorium medis (BMI, HbA1c, Urea, dll) pada kolom yang disediakan. **Pastikan tidak ada nilai yang dibiarkan 0.0**.
        4. Klik tombol **Cek Status Kesehatan**.
        """)
        
    with st.expander("3. Membaca Hasil Prediksi"):
        st.markdown("""
        Setelah Anda menekan tombol cek status, sistem akan memproses data menggunakan algoritma cerdas di latar belakang. Anda akan menerima dua keluaran:
        * **Hasil Diagnosis:** Menunjukkan status pasien yang terbagi menjadi 3 kelas: *Normal*, *Pra-Diabetes*, atau *Diabetes*.
        * **Tingkat Keyakinan Sistem:** Persentase seberapa yakin mesin (algoritma Gradient Boosting) terhadap hasil tebakannya.
        """)
        
    with st.expander("4. Melacak Riwayat Pemeriksaan"):
        st.markdown("""
        Setiap kali Anda melakukan skrining, sistem akan menyimpan rekam medis digital Anda secara otomatis.
        1. Pilih menu **📜 Riwayat Pemeriksaan** di panel navigasi sebelah kiri.
        2. Anda akan melihat sebuah tabel yang berisi seluruh parameter uji laboratorium, lengkap dengan waktu pemeriksaan dan hasil diagnosisnya.
        3. Data akan diurutkan dari yang paling baru hingga yang paling lama.
        """)

# ==============================================================================
# 8. TENTANG SISTEM
# ==============================================================================
elif menu == "ℹ️ Tentang Sistem":
    st.header("Informasi Proyek Skripsi")
    
    st.subheader("1. Latar Belakang")
    st.markdown("""
    Diabetes mellitus merupakan salah satu penyakit tidak menular kronis yang paling mendesak di era modern, ditandai dengan kadar glukosa darah yang tinggi secara berkelanjutan. Penyakit ini muncul akibat kegagalan pankreas dalam memproduksi insulin secara cukup atau ketidakmampuan tubuh dalam menggunakan insulin secara efektif. 
    Sistem ini dikembangkan untuk mengotomatisasi proses klasifikasi risiko tersebut menggunakan algoritma **Gradient Boosting**.
    """)
    
    st.subheader("2. Implementasi Sistem")
    st.markdown("""
    - **Algoritma Utama:** *Gradient Boosting Classifier* (untuk klasifikasi cerdas).
    - **Penyeimbangan Data:** *Synthetic Minority Over-sampling Technique* (SMOTE).
    - **Metode Augmentasi:** *Bootstrapping* untuk penguatan variansi data.
    - **Perangkat Pengembangan:** Python, Streamlit Framework, dan SQLite Database.
    """)
    
    st.subheader("3. Pembuat Web")
    st.markdown("""
    **Nama:** IQBAL ALFARIDZI BALMAN  
    **NIM:** 535220248  
    **Program Studi:** Teknik Informatika  
    **Instansi:** Universitas Tarumanagara
    """)