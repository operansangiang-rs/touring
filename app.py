import streamlit as st
import json
import os
import requests
import base64
from datetime import datetime
import plotly.express as px
import re
import time  # Ditambahkan untuk memberi jeda notifikasi

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

# FUNGSI FILTER FORMAT BIAYA BER-TITIK KE ANGKA MENTAH
def clean_numeric_string(s):
    return int(re.sub(r'[^\d]', '', str(s))) if re.sub(r'[^\d]', '', str(s)) else 0

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
    default_data = {
        "deposit": 0,
        "expenses": [],
        "categories": ["Bensin", "Makan & Minum", "Penginapan", "Tiket Wisata / Tol", "Perbaikan / Sparepart", "Lain-lain"]
    }
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if "deposit" not in data:
                    data["deposit"] = 0
                return data
        except Exception:
            pass
            
    return default_data

def save_turing_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
    push_to_github(data)

# Load data aktif
shared_data = load_turing_data()
deposit_amount = shared_data.get("deposit", 0)
expense_list = shared_data["expenses"]
categories_list = shared_data["categories"]

# --- STATE LOGIN MANAGEMENT ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

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
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("Password salah! Silakan coba lagi.")
else:
    st.sidebar.success("Status: Admin Aktif (Mas Lian)")
    
    st.sidebar.write("---")
    
    # 💵 PENGATURAN DEPOSIT UANG (KHUSUS ADMIN)
    st.sidebar.subheader("💵 Atur Uang Deposit")
    raw_deposit_input = st.sidebar.text_input(
        "Nominal Deposit / Modal awal (Rp):", 
        value=f"{deposit_amount:,}".replace(",", "."), 
        placeholder="Contoh: 1.500.000"
    )
    int_deposit_input = clean_numeric_string(raw_deposit_input)
    
    if st.sidebar.button("Simpan Deposit", use_container_width=True):
        shared_data["deposit"] = int_deposit_input
        save_turing_data(shared_data)
        st.sidebar.success("✅ Deposit berhasil diperbarui!")
        time.sleep(1.5)
        st.rerun()

    st.sidebar.write("---")

    # ➕ TAMBAH CATATAN PENGELUARAN
    st.sidebar.subheader("➕ Tambah Catatan")
    input_kategori = st.sidebar.selectbox("Kategori Pengeluaran:", categories_list)
    
    raw_biaya = st.sidebar.text_input("Nominal Biaya (Rp):", value="0", placeholder="Contoh: 50.000")
    int_biaya = clean_numeric_string(raw_biaya)
    
    if int_biaya > 0:
        st.sidebar.caption(f"Konfirmasi Nominal: **Rp {int_biaya:,.0f}**".replace(",", "."))

    input_catatan = st.sidebar.text_area("Catatan Tambahan (Opsional):", placeholder="Misal: Rest Area KM 57...")
    
    submit_button = st.sidebar.button("Simpan Pengeluaran", use_container_width=True, type="primary")
    
    if submit_button:
        if int_biaya <= 0:
            st.sidebar.error("Gagal! Nominal biaya harus lebih dari Rp0.")
        else:
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M")
            expense_list.append({
                "waktu": waktu_sekarang,
                "item": input_kategori,
                "kategori": input_kategori,
                "biaya": int_biaya,
                "catatan": input_catatan.strip()
            })
            save_turing_data({"deposit": deposit_amount, "expenses": expense_list, "categories": categories_list})
            
            # Tampilkan notifikasi di sidebar + pop-up toast ringkas
            st.sidebar.success("✅ Pengeluaran berhasil disimpan!")
            st.toast("✅ Pengeluaran berhasil disimpan!", icon="🎉")
            
            # Jeda 1.5 detik agar pengguna sempat melihat notifikasi
            time.sleep(1.5)
            st.rerun()

    # MENU RESET DATA (HANYA UNTUK ADMIN)
    st.sidebar.write("---")
    st.sidebar.subheader("🚨 Zona Bahaya")
    
    if not st.session_state.confirm_reset:
        if st.sidebar.button("🗑️ Reset Semua Data", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()
    else:
        st.sidebar.warning("⚠️ YAKIN INGIN RESET DATA?")
        col_yes, col_no = st.sidebar.columns(2)
        
        if col_yes.button("Ya, Hapus", use_container_width=True, type="primary"):
            empty_data = {"deposit": 0, "expenses": [], "categories": categories_list}
            save_turing_data(empty_data)
            st.session_state.confirm_reset = False
            st.sidebar.success("✅ Database berhasil dibersihkan!")
            time.sleep(1.5)
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
        time.sleep(1)
        st.rerun()

# --- HALAMAN UTAMA ---
col_judul, col_btn_sync = st.columns([7, 3])

with col_judul:
    st.title("📊 Biaya Turing")
with col_btn_sync:
    st.write("") 
    st.write("") 
    if st.button("🔄 Sinkron Data", use_container_width=True):
        st.rerun()

st.write("Pantau rincian biaya pengeluaran turing Anda secara real-time dan aman.")
st.markdown("---")

# Hitung Total Pengeluaran Keseluruhan & Sisa Deposit
total_dana = sum(item["biaya"] for item in expense_list)
sisa_deposit = deposit_amount - total_dana

# Tampilan Ringkasan dalam Metrik Utama (Format Titik Indonesia)
col_dep, col_total, col_sisa = st.columns(3)

with col_dep:
    st.metric(label="💵 Uang Deposit", value=f"Rp {deposit_amount:,.0f}".replace(",", "."))

with col_total:
    st.metric(label="💰 Terpakai", value=f"Rp {total_dana:,.0f}".replace(",", "."))

with col_sisa:
    st.metric(
        label="💳 Sisa Deposit", 
        value=f"Rp {sisa_deposit:,.0f}".replace(",", "."),
        delta=f"Rp {sisa_deposit:,.0f}".replace(",", "."),
        delta_color="normal" if sisa_deposit >= 0 else "inverse"
    )

st.caption(f"📊 Total Catatan Transaksi: **{len(expense_list)} Item**")
st.markdown("---")

# --- FITUR GRAFIK ---
if expense_list:
    with st.expander("🍕 Lihat Grafik Distribusi Biaya"):
        category_totals = {}
        for item in expense_list:
            cat = item["kategori"]
            cost = item["biaya"]
            category_totals[cat] = category_totals.get(cat, 0) + cost
            
        chart_labels = list(category_totals.keys())
        chart_values = list(category_totals.values())
        
        fig = px.pie(
            names=chart_labels, 
            values=chart_values, 
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=300)
        
        st.plotly_chart(fig, use_container_width=True)
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
        formatted_biaya = f"Rp {item['biaya']:,.0f}".replace(",", ".")
        
        with st.expander(f"{emoji} {item['kategori']} — {formatted_biaya}"):
            st.write(f"📅 **Waktu:** {item['waktu']}")
            if item['catatan']:
                st.info(f"📝 **Catatan:**\n{item['catatan']}")
                
            if st.session_state.is_admin:
                if st.button("🗑️ Hapus Catatan Ini", key=f"del_{original_idx}", use_container_width=True):
                    expense_list.pop(original_idx)
                    save_turing_data({"deposit": deposit_amount, "expenses": expense_list, "categories": categories_list})
                    st.success("Catatan berhasil dihapus!")
                    time.sleep(1.2)
                    st.rerun()
else:
    st.info("Belum ada pengeluaran yang dicatat. Silakan masukkan password admin di sidebar untuk mulai mengisi data!")
