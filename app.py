import streamlit as st
import json
import os
import requests
import base64
from datetime import datetime

# =========================================================================
# 🔐 MENGAMBIL DATA REPO & TOKEN AMAN DARI STREAMLIT SECRETS (GRATIS)
# =========================================================================
try:
    GITHUB_TOKEN = st.secrets["github"]["token"]
    REPO_NAME = st.secrets["github"]["repo"]
except Exception:
    GITHUB_TOKEN = ""
    REPO_NAME = ""
# =========================================================================

DB_FILE = "turing_expenses.json"

st.set_page_config(
    page_title="Touring Expense Tracker",
    page_icon="🏍️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# =========================================================================
# FUNGSI OTOMATIS SYNC KE GITHUB
# =========================================================================
def push_to_github(data):
    if GITHUB_TOKEN.startswith("ghp_") and "/" in REPO_NAME:
        try:
            url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            res = requests.get(url, headers=headers)
            sha = res.json().get("sha") if res.status_code == 200 else None
            
            json_string = json.dumps(data, indent=4)
            content_base64 = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
            
            payload = {
                "message": "Sistem: Update turing_expenses.json dari aplikasi",
                "content": content_base64
            }
            if sha:
                payload["sha"] = sha
                
            requests.put(url, headers=headers, json=payload)
        except Exception as e:
            print(f"Gagal sinkronisasi ke GitHub: {e}")

def load_turing_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
            
    return {
        "expenses": [],
        "categories": ["Bensin", "Makan & Minum", "Penginapan", "Tiket Wisata / Tol", "Perbaikan / Sparepart", "Lain-lain"]
    }

def save_turing_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
    push_to_github(data)

# Load data aktif
shared_data = load_turing_data()
expense_list = shared_data["expenses"]
categories_list = shared_data["categories"]

# --- STATE LOGIN MANAGEMENT ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# State untuk konfirmasi reset data
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

# --- SIDEBAR: AKSES ADMIN & LOGIN ---
st.sidebar.title("🔐 Akses Admin")

if not st.session_state.is_admin:
    st.sidebar.write("Masukkan password admin untuk mencatat atau menghapus pengeluaran.")
    admin_password = st.sidebar.text_input("Password Admin", type="password", placeholder="Ketik password di sini...")
    
    if st.sidebar.button("Masuk", use_container_width=True):
        if admin_password == "123":
            st.session_state.is_admin = True
            st.sidebar.success("Login Berhasil! Selamat datang Mas Lian.")
            st.rerun()
        else:
            st.sidebar.error("Password salah! Silakan coba lagi.")
else:
    st.sidebar.success("Status: Admin Aktif (Mas Lian)")
    
    # Tampilkan Form Input Hanya Jika Sudah Login Sukses
    st.sidebar.write("---")
    with st.sidebar.form("form_tambah_pengeluaran", clear_on_submit=True):
        st.subheader("➕ Tambah Catatan")
        input_item = st.text_input("Nama Pengeluaran / Keperluan:", placeholder="Contoh: Bensin Pertamax")
        input_kategori = st.selectbox("Pilih Kategori:", categories_list)
        input_biaya = st.number_input("Nominal Biaya (Rp):", min_value=0, step=1000, value=0)
        input_catatan = st.text_area("Catatan Tambahan (Opsional):", placeholder="Misal: KM roda, bensin full tank...")
        
        submit_button = st.form_submit_button("Simpan Pengeluaran", use_container_width=True)
        
        if submit_button:
            if input_item.strip() == "" or input_biaya <= 0:
                st.sidebar.error("Gagal! Nama pengeluaran harus diisi & nominal > Rp0.")
            else:
                waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M")
                expense_list.append({
                    "waktu": waktu_sekarang,
                    "item": input_item.strip(),
                    "kategori": input_kategori,
                    "biaya": input_biaya,
                    "catatan": input_catatan.strip()
                })
                save_turing_data({"expenses": expense_list, "categories": categories_list})
                st.sidebar.success("Pengeluaran berhasil dicatat!")
                st.rerun()

    # MENU RESET DATA (HANYA UNTUK ADMIN)
    st.sidebar.write("---")
    st.sidebar.subheader("🚨 Zona Bahaya")
    
    if not st.session_state.confirm_reset:
        if st.sidebar.button("🗑️ Reset Semua Data", use_container_width=True, type="primary"):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.sidebar.warning("⚠️ YAKIN INGIN RESET DATA? Semua catatan turing akan dihapus permanen dari GitHub!")
        col_yes, col_no = st.sidebar.columns(2)
        
        if col_yes.button("Ya, Hapus", use_container_width=True, type="primary"):
            # Proses mengosongkan data kembali ke awal
            empty_data = {"expenses": [], "categories": categories_list}
            save_turing_data(empty_data)
            st.session_state.confirm_reset = False
            st.sidebar.success("Database berhasil dibersihkan kembali ke nol!")
            st.rerun()
            
        if col_no.button("Batal", use_container_width=True):
            st.session_state.confirm_reset = False
            st.rerun()

    # Tombol Keluar / Logout
    st.sidebar.write("---")
    if st.sidebar.button("Keluar (Logout)", use_container_width=True):
        st.session_state.is_admin = False
        st.session_state.confirm_reset = False
        st.sidebar.info("Anda telah logout.")
        st.rerun()

# --- HALAMAN UTAMA ---
col_judul, col_btn_sync = st.columns([7, 3])

with col_judul:
    st.title("📊 Biaya Turing")
with col_btn_sync:
    st.write("") 
    st.write("") 
    if st.button("🔄 Sinkron Data", use_container_width=True, help="Klik untuk memuat ulang data pengeluaran terbaru dari GitHub"):
        st.rerun()

st.write("Pantau rincian biaya pengeluaran turing Anda secara real-time dan aman.")
st.markdown("---")

# Hitung Total Pengeluaran Keseluruhan
total_dana = sum(item["biaya"] for item in expense_list)

# Tampilan Ringkasan dalam Metrik Utama
col_total, col_jumlah_transaksi = st.columns(2)
with col_total:
    st.metric(label="💰 Total Pengeluaran Turing", value=f"Rp {total_dana:,}")
with col_jumlah_transaksi:
    st.metric(label="📊 Jumlah Catatan", value=f"{len(expense_list)} Item")

st.markdown("---")

# Urutkan dari yang paling baru diinput
expense_list_reversed = list(reversed(expense_list))

st.subheader("📋 Rincian Pengeluaran Lengkap")
if expense_list_reversed:
    for idx, item in enumerate(expense_list_reversed):
        emoji_dict = {
            "Bensin": "⛽",
            "Makan & Minum": "🍽️",
            "Penginapan": "🏨",
            "Tiket Wisata / Tol": "🎟️",
            "Perbaikan / Sparepart": "🛠️",
            "Lain-lain": "📦"
        }
        emoji = emoji_dict.get(item["kategori"], "💰")
        
        original_idx = len(expense_list) - 1 - idx
        with st.expander(f"{emoji} {item['item']} — Rp {item['biaya']:,}"):
            st.write(f"📅 **Waktu:** {item['waktu']}")
            st.write(f"📁 **Kategori:** {item['kategori']}")
            if item['catatan']:
                st.info(f"📝 **Catatan:**\n{item['catatan']}")
                
            # Tombol Hapus Hanya Muncul Jika Statusnya Sudah Login Admin
            if st.session_state.is_admin:
                if st.button("🗑️ Hapus Catatan Ini", key=f"del_{original_idx}", use_container_width=True):
                    expense_list.pop(original_idx)
                    save_turing_data({"expenses": expense_list, "categories": categories_list})
                    st.success("Catatan berhasil dihapus!")
                    st.rerun()
else:
    st.info("Belum ada pengeluaran yang dicatat. Silakan masukkan password admin di sidebar untuk mulai mengisi data!")
