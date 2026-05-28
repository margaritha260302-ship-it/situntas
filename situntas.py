import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import io
import hashlib

st.set_page_config(
    page_title="SITUNTAS — Kecamatan Kota SoE",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DATA WILAYAH ──────────────────────────────────────────────────────────────
WILAYAH = {
    "Kelurahan Cendana":     ["Persit", "Sonapolen", "Oenutnanan", "Taeano"],
    "Kelurahan SoE":         ["Kantor Agama", "Sonaf"],
    "Kelurahan Karangsiri":  ["Kobelete A", "Kobelete B", "Bu'at", "Nifuboko"],
    "Kelurahan Nonohonis":   ["Nonohonis 1", "Nonohonis 2", "Oenasi"],
    "Kelurahan Kota Baru":   ["Pasar Inpres", "Kota Baru"],
    "Kelurahan Kampung Baru":["Maleset", "Bhayangkari"],
    "Kelurahan Taubneno":    ["Taubneno"],
    "Kelurahan Oekefan":     ["Oekefan 1", "Oekefan 2"],
    "Kelurahan Oebesa":      ["Besatuan", "Nekmese", "Enopetu"],
    "Kelurahan Nunumeu":     ["Nunumeu 1", "Nunumeu 2", "Nunumeu 3"],
    "Kelurahan Kobekamusa":  ["Mnelafau", "Kobekamusa"],
    "Desa Noemeto":          ["Tnoemina", "Oeniupsae", "Noemeto"],
    "Desa Kuatae":           ["Leobisa", "Kuni"],
}

BULAN_LIST = ["Januari","Februari","Maret","April","Mei","Juni",
              "Juli","Agustus","September","Oktober","November","Desember"]
TAHUN_LIST = [2024, 2025, 2026, 2027]

DATA_FILE = "data_situntas.csv"
USER_FILE = "users_situntas.csv"

# ─── USER MANAGEMENT ───────────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE)
    # Default users
    users = pd.DataFrame([
        {"username": "admin", "password": hash_password("situntas2025"), "nama": "Administrator", "role": "admin", "wilayah": "semua", "aktif": True},
        {"username": "pegawai01", "password": hash_password("pegawai123"), "nama": "Pegawai 1", "role": "pegawai", "wilayah": "Kelurahan Kota SoE", "aktif": True},
        {"username": "pegawai02", "password": hash_password("pegawai123"), "nama": "Pegawai 2", "role": "pegawai", "wilayah": "Kelurahan Karang Siri", "aktif": True},
    ])
    users.to_csv(USER_FILE, index=False)
    return users

def save_users(df):
    df.to_csv(USER_FILE, index=False)

def verify_user(username, password):
    users = load_users()
    user = users[(users["username"] == username) & (users["aktif"] == True)]
    if user.empty:
        return None
    if user.iloc[0]["password"] == hash_password(password):
        return user.iloc[0].to_dict()
    return None

# ─── DATA MANAGEMENT ───────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    df = pd.DataFrame(columns=[
        "tahun","bulan","bulan_ke","wilayah","posyandu",
        "sasaran","hadir","stunting","diinput_oleh","waktu_input"
    ])
    df.to_csv(DATA_FILE, index=False)
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_bulan_ke(nama_bulan):
    return BULAN_LIST.index(nama_bulan) + 1

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');

* { font-family: 'Plus Jakarta Sans', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1628 0%, #0D2147 40%, #0A1E45 100%) !important;
    border-right: 1px solid rgba(99,179,237,0.15);
}
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
[data-testid="stSidebar"] .stRadio label { 
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 3px 0;
    transition: all 0.2s;
    cursor: pointer;
    display: block;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(99,179,237,0.15);
    border-color: rgba(99,179,237,0.3);
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #060D1F 0%, #0A1628 50%, #0C1E3D 100%);
    min-height: 100vh;
}

/* Header */
.situntas-header {
    background: linear-gradient(135deg, #0D2147 0%, #1A3A6B 50%, #1E4080 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.situntas-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(99,179,237,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.situntas-header::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: 20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(56,189,248,0.06) 0%, transparent 70%);
    border-radius: 50%;
}
.header-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.5px;
    margin: 0;
    line-height: 1.2;
}
.header-badge {
    display: inline-block;
    background: rgba(99,179,237,0.15);
    border: 1px solid rgba(99,179,237,0.3);
    color: #63B3ED;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 0.8rem;
}
.header-sub {
    color: rgba(226,232,240,0.7);
    font-size: 0.9rem;
    margin: 0.3rem 0 0;
    font-weight: 400;
}

/* Metric cards */
.metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.5rem; }
.metric-card {
    background: linear-gradient(135deg, #0D2147 0%, #112654 100%);
    border: 1px solid rgba(99,179,237,0.15);
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
}
.metric-card:hover { transform: translateY(-2px); border-color: rgba(99,179,237,0.35); }
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 80px; height: 80px;
    border-radius: 50%;
    opacity: 0.08;
}
.mc-red::before { background: #FC8181; }
.mc-blue::before { background: #63B3ED; }
.mc-green::before { background: #68D391; }
.mc-yellow::before { background: #F6E05E; }
.metric-icon { font-size: 1.6rem; margin-bottom: 0.5rem; }
.metric-label { font-size: 0.73rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: rgba(226,232,240,0.55); margin-bottom: 0.3rem; }
.metric-value { font-size: 2.1rem; font-weight: 800; line-height: 1; color: #FFFFFF; }
.metric-sub { font-size: 0.78rem; color: rgba(226,232,240,0.45); margin-top: 0.3rem; }
.metric-delta-up { color: #FC8181; font-size: 0.78rem; font-weight: 600; }
.metric-delta-down { color: #68D391; font-size: 0.78rem; font-weight: 600; }

/* Section title */
.section-title {
    color: #E2E8F0;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin: 1.5rem 0 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(99,179,237,0.15);
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title span { color: #63B3ED; }

/* Alert box */
.alert-box {
    background: rgba(99,179,237,0.08);
    border: 1px solid rgba(99,179,237,0.2);
    border-left: 4px solid #63B3ED;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    color: #BEE3F8;
    font-size: 0.87rem;
    margin-bottom: 1rem;
}
.alert-warning {
    background: rgba(246,224,94,0.08);
    border-color: rgba(246,224,94,0.2);
    border-left-color: #F6E05E;
    color: #FEFCBF;
}

/* Status badge */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }
.badge-red { background: rgba(252,129,129,0.15); color: #FC8181; border: 1px solid rgba(252,129,129,0.3); }
.badge-green { background: rgba(104,211,145,0.15); color: #68D391; border: 1px solid rgba(104,211,145,0.3); }
.badge-yellow { background: rgba(246,224,94,0.15); color: #F6E05E; border: 1px solid rgba(246,224,94,0.3); }

/* Table */
.stDataFrame { border-radius: 12px; overflow: hidden; }
[data-testid="stDataFrame"] { background: #0D2147 !important; }

/* Input fields */
.stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div {
    background: rgba(13,33,71,0.8) !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
.stTextInput input, .stNumberInput input { color: #E2E8F0 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1A56DB 0%, #1E429F 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1E63F4 0%, #2350B5 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(26,86,219,0.4) !important;
}

/* Logo sidebar */
.sidebar-logo {
    text-align: center;
    padding: 1.5rem 1rem 1rem;
    border-bottom: 1px solid rgba(99,179,237,0.1);
    margin-bottom: 1rem;
}
.sidebar-title { font-family: 'Playfair Display', serif; font-size: 1.4rem; font-weight: 800; color: #FFFFFF !important; }
.sidebar-sub { font-size: 0.7rem; color: rgba(226,232,240,0.5) !important; letter-spacing: 1px; text-transform: uppercase; }

/* Login page */
.login-wrapper {
    min-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
.login-card {
    background: linear-gradient(135deg, #0D2147 0%, #112654 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 24px;
    padding: 3rem;
    max-width: 420px;
    width: 100%;
    box-shadow: 0 25px 60px rgba(0,0,0,0.5);
}

/* Chart container */
.chart-container {
    background: linear-gradient(135deg, #0D2147 0%, #0F2654 100%);
    border: 1px solid rgba(99,179,237,0.12);
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}

/* Public banner */
.public-banner {
    background: linear-gradient(135deg, #065F46 0%, #047857 100%);
    border: 1px solid rgba(52,211,153,0.3);
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    color: #D1FAE5;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Plotly charts dark theme override */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0A1628; }
::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.3); border-radius: 3px; }

/* Form labels */
label { color: rgba(226,232,240,0.85) !important; font-size: 0.85rem !important; font-weight: 500 !important; }
.stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label { color: rgba(226,232,240,0.85) !important; }
p, div { color: #E2E8F0; }
h1,h2,h3 { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

PLOT_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(13,33,71,0.3)',
    font=dict(color='#CBD5E0', family='Plus Jakarta Sans', size=12),
    xaxis=dict(gridcolor='rgba(99,179,237,0.08)', linecolor='rgba(99,179,237,0.15)', tickfont=dict(color='#A0AEC0')),
    yaxis=dict(gridcolor='rgba(99,179,237,0.08)', linecolor='rgba(99,179,237,0.15)', tickfont=dict(color='#A0AEC0')),
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(bgcolor='#1A3A6B', bordercolor='rgba(99,179,237,0.3)', font=dict(color='#E2E8F0')),
    legend=dict(bgcolor='rgba(13,33,71,0.8)', bordercolor='rgba(99,179,237,0.2)', borderwidth=1, font=dict(color='#CBD5E0')),
)

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_public = False

# ─── HEADER ────────────────────────────────────────────────────────────────────
def render_header(subtitle=""):
    st.markdown(f"""
    <div class="situntas-header">
        <div class="header-badge">🏥 Sistem Informasi Digital</div>
        <div class="header-title">SITUNTAS</div>
        <div class="header-sub">Sistem Informasi Terpadu Monitoring Angka Stunting Secara Realtime<br>
        Kecamatan Kota SoE — Kabupaten Timor Tengah Selatan{'<br><span style="color:#63B3ED;font-size:0.82rem;">'+subtitle+'</span>' if subtitle else ''}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── LOGIN PAGE ─────────────────────────────────────────────────────────────────
def login_page():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 3rem 0 1.5rem;'>
            <div style='font-size:3.5rem; margin-bottom:0.5rem;'>🏥</div>
            <div style='font-family:"Playfair Display",serif; font-size:2rem; font-weight:800; color:#FFFFFF;'>SITUNTAS</div>
            <div style='font-size:0.78rem; color:rgba(226,232,240,0.5); letter-spacing:1.5px; text-transform:uppercase; margin-top:4px;'>
                Sistem Informasi Terpadu Monitoring Stunting
            </div>
            <div style='font-size:0.8rem; color:rgba(99,179,237,0.7); margin-top:6px;'>
                Kecamatan Kota SoE · Kab. Timor Tengah Selatan
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
            username = st.text_input("👤  Username", placeholder="Masukkan username")
            password = st.text_input("🔑  Password", type="password", placeholder="Masukkan password")
            col_a, col_b = st.columns(2)
            with col_a:
                login_btn = st.form_submit_button("🔐  MASUK", use_container_width=True, type="primary")
            with col_b:
                publik_btn = st.form_submit_button("🌐  Lihat Dashboard Publik", use_container_width=True)

            if login_btn:
                user = verify_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.is_public = False
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah.")
            if publik_btn:
                st.session_state.is_public = True
                st.session_state.logged_in = False
                st.rerun()

        st.markdown("""
        <div style='text-align:center; font-size:0.75rem; color:rgba(226,232,240,0.3); margin-top:2rem;'>
            © 2026 Kecamatan Kota SoE · Dikembangkan oleh Margaritha Liufeto, S.H
        </div>
        """, unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
def render_sidebar(role="publik"):
    with st.sidebar:
        st.markdown("""
        <div class='sidebar-logo'>
            <div style='font-size:2.5rem;'>🏥</div>
            <div class='sidebar-title'>SITUNTAS</div>
            <div class='sidebar-sub'>Kecamatan Kota SoE</div>
        </div>
        """, unsafe_allow_html=True)

        if role == "publik":
            menu = "📊 Dashboard Publik"
            st.markdown("<div style='padding:0.5rem 1rem; background:rgba(52,211,153,0.1); border-radius:8px; margin-bottom:1rem;'><span style='color:#6EE7B7; font-size:0.8rem;'>🌐 Mode Publik — Akses Terbatas</span></div>", unsafe_allow_html=True)
            if st.button("🔐 Login sebagai Pegawai", use_container_width=True):
                st.session_state.is_public = False
                st.session_state.logged_in = False
                st.rerun()
        else:
            menu_options = ["📊 Dashboard Utama"]
            if role in ["pegawai", "admin"]:
                menu_options.append("📋 Input Data")
                menu_options.append("📤 Import Google Sheets")
            if role == "admin":
                menu_options += ["📈 Analisis & Tren", "📄 Laporan", "👥 Kelola Pengguna", "⚙️ Kelola Data"]

            menu = st.radio("Navigasi", menu_options, label_visibility="collapsed")

        st.markdown("<hr style='border-color:rgba(99,179,237,0.1); margin:1rem 0;'>", unsafe_allow_html=True)
        st.markdown("**🗓️ Filter Periode**")
        tahun = st.selectbox("Tahun", TAHUN_LIST, index=TAHUN_LIST.index(datetime.now().year) if datetime.now().year in TAHUN_LIST else 2)
        bulan = st.selectbox("Bulan", BULAN_LIST, index=datetime.now().month - 1)

        if role != "publik":
            st.markdown("<hr style='border-color:rgba(99,179,237,0.1); margin:1rem 0;'>", unsafe_allow_html=True)
            user = st.session_state.user
            st.markdown(f"""
            <div style='font-size:0.78rem; color:rgba(226,232,240,0.5);'>
                Login sebagai:<br>
                <span style='color:#63B3ED; font-weight:600;'>{user['nama']}</span><br>
                <span style='font-size:0.7rem; color:rgba(226,232,240,0.35);'>{user['role'].upper()}</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin:0.5rem 0;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Keluar", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.rerun()

    return menu, tahun, bulan

# ─── DASHBOARD ──────────────────────────────────────────────────────────────────
def page_dashboard(df, tahun, bulan, is_public=False):
    render_header()

    if is_public:
        st.markdown("""
        <div class='public-banner'>
            🌐 <strong>Dashboard Publik</strong> — Data ditampilkan secara terbuka untuk transparansi. Login diperlukan untuk fitur lainnya.
        </div>
        """, unsafe_allow_html=True)

    bulan_ke = get_bulan_ke(bulan)
    df_bulan = df[(df["tahun"] == tahun) & (df["bulan"] == bulan)]
    bulan_lalu = BULAN_LIST[bulan_ke - 2] if bulan_ke > 1 else None
    df_lalu = df[(df["tahun"] == tahun) & (df["bulan"] == bulan_lalu)] if bulan_lalu else pd.DataFrame()

    total_stunting = int(df_bulan["stunting"].sum()) if not df_bulan.empty else 0
    total_hadir    = int(df_bulan["hadir"].sum()) if not df_bulan.empty else 0
    total_sasaran  = int(df_bulan["sasaran"].sum()) if not df_bulan.empty else 0
    wilayah_lapor  = df_bulan["wilayah"].nunique() if not df_bulan.empty else 0
    posyandu_aktif = df_bulan["posyandu"].nunique() if not df_bulan.empty else 0
    pct_hadir      = round(total_hadir / total_sasaran * 100, 1) if total_sasaran > 0 else 0

    stunting_lalu = int(df_lalu["stunting"].sum()) if not df_lalu.empty else None
    hadir_lalu    = int(df_lalu["hadir"].sum()) if not df_lalu.empty else None

    def delta_stunt(now, prev):
        if prev is None: return ""
        d = now - prev
        if d > 0: return f'<span class="metric-delta-up">▲ +{d} dari bln lalu</span>'
        elif d < 0: return f'<span class="metric-delta-down">▼ {d} dari bln lalu</span>'
        return '<span style="color:#A0AEC0; font-size:0.78rem;">= sama seperti bln lalu</span>'

    st.markdown(f"<div class='section-title'><span>▌</span> Ringkasan Bulan {bulan} {tahun}</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='metric-grid'>
        <div class='metric-card mc-red'>
            <div class='metric-icon'>🔴</div>
            <div class='metric-label'>Total Kasus Stunting</div>
            <div class='metric-value'>{total_stunting:,}</div>
            <div class='metric-sub'>{delta_stunt(total_stunting, stunting_lalu)}</div>
        </div>
        <div class='metric-card mc-blue'>
            <div class='metric-icon'>👶</div>
            <div class='metric-label'>Kehadiran Posyandu</div>
            <div class='metric-value'>{total_hadir:,}</div>
            <div class='metric-sub'><span style='color:#63B3ED;'>{pct_hadir}%</span> dari {total_sasaran:,} sasaran</div>
        </div>
        <div class='metric-card mc-green'>
            <div class='metric-icon'>🏘️</div>
            <div class='metric-label'>Wilayah Melapor</div>
            <div class='metric-value'>{wilayah_lapor}</div>
            <div class='metric-sub'>dari 13 Kel/Desa</div>
        </div>
        <div class='metric-card mc-yellow'>
            <div class='metric-icon'>🏥</div>
            <div class='metric-label'>Posyandu Aktif</div>
            <div class='metric-value'>{posyandu_aktif}</div>
            <div class='metric-sub'>dari 33 posyandu</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_bulan.empty:
        st.markdown(f"""
        <div class='alert-box alert-warning'>
            ⚠️ Belum ada data untuk bulan <strong>{bulan} {tahun}</strong>. Silakan input data terlebih dahulu.
        </div>
        """, unsafe_allow_html=True)
        return

    # Agregat per wilayah
    df_wil = df_bulan.groupby("wilayah", as_index=False).agg(
        stunting=("stunting","sum"),
        hadir=("hadir","sum"),
        sasaran=("sasaran","sum")
    )
    if not df_lalu.empty:
        df_wil_lalu = df_lalu.groupby("wilayah", as_index=False).agg(stunting_lalu=("stunting","sum"))
        df_wil = df_wil.merge(df_wil_lalu, on="wilayah", how="left")
        df_wil["trend"] = df_wil.apply(lambda r: "Naik" if r["stunting"] > r.get("stunting_lalu", r["stunting"])
                                        else ("Turun" if r["stunting"] < r.get("stunting_lalu", r["stunting"]) else "Tetap"), axis=1)
    else:
        df_wil["trend"] = "Data Awal"

    df_wil["pct_hadir"] = (df_wil["hadir"] / df_wil["sasaran"] * 100).round(1).fillna(0)
    df_wil = df_wil.sort_values("stunting", ascending=True)

    warna_map = {"Naik": "#FC8181", "Turun": "#68D391", "Tetap": "#F6E05E", "Data Awal": "#63B3ED"}

    st.markdown("<div class='section-title'><span>▌</span> Kasus Stunting per Kelurahan/Desa</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig_s = go.Figure(go.Bar(
            x=df_wil["stunting"],
            y=df_wil["wilayah"],
            orientation="h",
            marker=dict(color=[warna_map.get(t,"#63B3ED") for t in df_wil["trend"]],
                       line=dict(color="rgba(0,0,0,0.2)", width=0.5)),
            text=df_wil["stunting"],
            textposition="outside",
            textfont=dict(color="#E2E8F0", size=12),
            hovertemplate="<b>%{y}</b><br>Stunting: <b>%{x}</b><extra></extra>",
        ))
        fig_s.update_layout(
            title=dict(text=f"Stunting per Wilayah — {bulan} {tahun}", font=dict(color="#E2E8F0", size=14), x=0),
            height=450, **PLOT_LAYOUT
        )
        st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.78rem; color:rgba(226,232,240,0.5); margin-top:-0.5rem; margin-bottom:0.5rem;'>
        🔴 Naik &nbsp;|&nbsp; 🟢 Turun &nbsp;|&nbsp; 🟡 Tetap &nbsp;|&nbsp; 🔵 Data Awal
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig_h = go.Figure()
        fig_h.add_trace(go.Bar(
            x=df_wil["sasaran"], y=df_wil["wilayah"], orientation="h",
            name="Sasaran", marker_color="rgba(99,179,237,0.2)",
            hovertemplate="<b>%{y}</b><br>Sasaran: %{x}<extra></extra>",
        ))
        fig_h.add_trace(go.Bar(
            x=df_wil["hadir"], y=df_wil["wilayah"], orientation="h",
            name="Hadir", marker_color="#63B3ED",
            text=[f"{v} ({p}%)" for v, p in zip(df_wil["hadir"], df_wil["pct_hadir"])],
            textposition="outside", textfont=dict(color="#E2E8F0", size=11),
            hovertemplate="<b>%{y}</b><br>Hadir: %{x}<extra></extra>",
        ))
        fig_h.update_layout(
            barmode="overlay",
            title=dict(text=f"Sasaran vs Kehadiran Posyandu — {bulan} {tahun}", font=dict(color="#E2E8F0", size=14), x=0),
            height=450, **PLOT_LAYOUT
        )
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # Tabel ringkasan
    st.markdown("<div class='section-title'><span>▌</span> Tabel Rekapitulasi Wilayah</div>", unsafe_allow_html=True)
    df_tabel = df_wil[["wilayah","sasaran","hadir","pct_hadir","stunting"]].rename(columns={
        "wilayah":"Wilayah","sasaran":"Sasaran","hadir":"Hadir",
        "pct_hadir":"Cakupan (%)","stunting":"Kasus Stunting"
    })
    st.dataframe(df_tabel.sort_values("Kasus Stunting", ascending=False), use_container_width=True, hide_index=True)

# ─── INPUT DATA ────────────────────────────────────────────────────────────────
def page_input(df, user):
    render_header("Input Data Bulanan")
    st.markdown(f"""
    <div class='alert-box'>
        ℹ️ Anda login sebagai <strong>{user['nama']}</strong>.
        {'Input data untuk semua wilayah tersedia.' if user['role']=='admin' else f"Wilayah Anda: <strong>{user['wilayah']}</strong>"}
    </div>
    """, unsafe_allow_html=True)

    wilayah_opts = list(WILAYAH.keys()) if user["role"] == "admin" else [user["wilayah"]]

    with st.form("form_input", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tahun_in = st.selectbox("Tahun *", TAHUN_LIST, index=2)
            bulan_in = st.selectbox("Bulan *", BULAN_LIST, index=datetime.now().month - 1)
            wilayah_in = st.selectbox("Kelurahan/Desa *", wilayah_opts)
        with col2:
            posyandu_opts = WILAYAH.get(wilayah_in, []) if wilayah_in else []
            posyandu_in = st.selectbox("Posyandu *", posyandu_opts)
            sasaran_in = st.number_input("Total Sasaran (jumlah anak terdaftar) *", min_value=0, step=1)
            hadir_in = st.number_input("Jumlah Kehadiran *", min_value=0, step=1)

        stunting_in = st.number_input("Jumlah Kasus Stunting *", min_value=0, step=1)

        submitted = st.form_submit_button("💾 SIMPAN DATA", use_container_width=True, type="primary")
        if submitted:
            if sasaran_in == 0:
                st.error("❌ Total sasaran tidak boleh 0.")
            elif hadir_in > sasaran_in:
                st.error("❌ Kehadiran tidak boleh melebihi sasaran.")
            else:
                cek = df[(df["tahun"]==tahun_in)&(df["bulan"]==bulan_in)&(df["posyandu"]==posyandu_in)]
                if not cek.empty:
                    st.warning(f"⚠️ Data {posyandu_in} — {bulan_in} {tahun_in} sudah ada. Gunakan menu Kelola Data untuk mengubah.")
                else:
                    new_row = {
                        "tahun":tahun_in,"bulan":bulan_in,"bulan_ke":get_bulan_ke(bulan_in),
                        "wilayah":wilayah_in,"posyandu":posyandu_in,
                        "sasaran":sasaran_in,"hadir":hadir_in,"stunting":stunting_in,
                        "diinput_oleh":user["username"],"waktu_input":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    st.success(f"✅ Data {posyandu_in} — {bulan_in} {tahun_in} berhasil disimpan!")
                    st.rerun()

    st.markdown("<div class='section-title'><span>▌</span> Data Terbaru (10 Terakhir)</div>", unsafe_allow_html=True)
    if not df.empty:
        st.dataframe(df.sort_values("waktu_input", ascending=False).head(10), use_container_width=True, hide_index=True)

    return df

# ─── IMPORT GOOGLE SHEETS ──────────────────────────────────────────────────────
def page_import(df):
    render_header("Import Data dari Google Sheets")
    st.markdown("""
    <div class='alert-box'>
        📥 <strong>Cara Import Data Google Sheets:</strong><br>
        1. Buka Google Sheets → File → Download → <strong>Comma Separated Values (.csv)</strong><br>
        2. Upload file CSV tersebut di bawah ini.<br>
        3. Sistem akan otomatis membaca dan menyimpan data ke SITUNTAS.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Format kolom CSV yang diperlukan:**")
    contoh = pd.DataFrame([{
        "tahun":2026,"bulan":"Mei","wilayah":"Kelurahan Kota SoE","posyandu":"Posyandu Mawar I",
        "sasaran":45,"hadir":38,"stunting":5
    }])
    st.dataframe(contoh, use_container_width=True, hide_index=True)

    uploaded = st.file_uploader("📂 Upload File CSV dari Google Sheets", type=["csv"])
    if uploaded:
        try:
            df_import = pd.read_csv(uploaded)
            st.markdown("**Preview data yang akan diimport:**")
            st.dataframe(df_import.head(10), use_container_width=True, hide_index=True)
            st.markdown(f"<div class='alert-box'>📊 Total: <strong>{len(df_import)}</strong> baris data siap diimport.</div>", unsafe_allow_html=True)

            if st.button("✅ Konfirmasi Import", type="primary", use_container_width=True):
                df_import["bulan_ke"] = df_import["bulan"].apply(lambda x: get_bulan_ke(x) if x in BULAN_LIST else 0)
                df_import["diinput_oleh"] = "import_gsheets"
                df_import["waktu_input"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df = pd.concat([df, df_import], ignore_index=True).drop_duplicates(
                    subset=["tahun","bulan","posyandu"], keep="last"
                )
                save_data(df)
                st.success(f"✅ {len(df_import)} data berhasil diimport!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error membaca file: {e}")
    return df

# ─── ANALISIS & TREN ──────────────────────────────────────────────────────────
def page_analisis(df, tahun):
    render_header("Analisis & Tren")
    df_tahun = df[df["tahun"] == tahun]
    if df_tahun.empty:
        st.markdown(f"<div class='alert-box alert-warning'>⚠️ Belum ada data untuk tahun {tahun}.</div>", unsafe_allow_html=True)
        return

    tab1, tab2 = st.tabs(["📉 Tren Stunting", "👶 Tren Kehadiran"])
    df_agg = df_tahun.groupby(["bulan_ke","bulan"], as_index=False).agg(
        stunting=("stunting","sum"), hadir=("hadir","sum"), sasaran=("sasaran","sum")
    ).sort_values("bulan_ke")
    df_agg["pct_hadir"] = (df_agg["hadir"]/df_agg["sasaran"]*100).round(1)

    with tab1:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_agg["bulan"], y=df_agg["stunting"],
            mode="lines+markers",
            line=dict(color="#FC8181", width=3),
            marker=dict(size=10, color="#FC8181", line=dict(color="#FFFFFF",width=2)),
            fill="tozeroy", fillcolor="rgba(252,129,129,0.08)",
            name="Stunting",
            hovertemplate="<b>%{x}</b><br>Stunting: <b>%{y}</b><extra></extra>"
        ))
        fig.update_layout(title=dict(text=f"Tren Kasus Stunting — {tahun}", font=dict(color="#E2E8F0",size=15),x=0),
                         height=380, **PLOT_LAYOUT)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        # Per wilayah
        df_wil_trend = df_tahun.groupby(["wilayah","bulan_ke","bulan"],as_index=False).agg(stunting=("stunting","sum")).sort_values("bulan_ke")
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig2 = px.line(df_wil_trend, x="bulan", y="stunting", color="wilayah",
                       markers=True, title=f"Tren Stunting per Wilayah — {tahun}",
                       labels={"bulan":"Bulan","stunting":"Kasus","wilayah":"Wilayah"})
        fig2.update_traces(line_width=2, marker_size=7)
        fig2.update_layout(height=420, **PLOT_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df_agg["bulan"],y=df_agg["sasaran"],name="Sasaran",
                              marker_color="rgba(99,179,237,0.2)"))
        fig3.add_trace(go.Bar(x=df_agg["bulan"],y=df_agg["hadir"],name="Hadir",
                              marker_color="#63B3ED"))
        fig3.update_layout(barmode="overlay",title=dict(text=f"Kehadiran vs Sasaran — {tahun}",
                          font=dict(color="#E2E8F0",size=15),x=0),height=380,**PLOT_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=df_agg["bulan"],y=df_agg["pct_hadir"],
                                  mode="lines+markers",line=dict(color="#68D391",width=3),
                                  marker=dict(size=10,color="#68D391",line=dict(color="#FFFFFF",width=2)),
                                  fill="tozeroy",fillcolor="rgba(104,211,145,0.08)",name="Cakupan %"))
        fig4.add_hline(y=80,line_dash="dash",line_color="#F6E05E",
                       annotation_text="Target 80%",annotation_font_color="#F6E05E")
        fig4.update_layout(title=dict(text="Persentase Cakupan Kehadiran Posyandu (%)",
                          font=dict(color="#E2E8F0",size=15),x=0),height=380,**PLOT_LAYOUT)
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

# ─── LAPORAN ───────────────────────────────────────────────────────────────────
def page_laporan(df, tahun, bulan):
    render_header("Laporan Bulanan")
    df_bulan = df[(df["tahun"]==tahun)&(df["bulan"]==bulan)]

    if df_bulan.empty:
        st.markdown(f"<div class='alert-box alert-warning'>⚠️ Belum ada data untuk {bulan} {tahun}.</div>", unsafe_allow_html=True)
        return

    bulan_ke = get_bulan_ke(bulan)
    bulan_lalu = BULAN_LIST[bulan_ke-2] if bulan_ke > 1 else None
    df_lalu = df[(df["tahun"]==tahun)&(df["bulan"]==bulan_lalu)] if bulan_lalu else pd.DataFrame()

    rows = []
    for wil in WILAYAH.keys():
        r_now = df_bulan[df_bulan["wilayah"]==wil]
        r_lalu = df_lalu[df_lalu["wilayah"]==wil] if not df_lalu.empty else pd.DataFrame()
        if r_now.empty:
            rows.append({"Wilayah":wil,"Sasaran":"—","Hadir":"—","Cakupan (%)":"—","Stunting":"—","Trend":"—","Status":"❌ Belum Lapor"})
        else:
            s = int(r_now["stunting"].sum()); h = int(r_now["hadir"].sum()); sa = int(r_now["sasaran"].sum())
            pct = round(h/sa*100,1) if sa > 0 else 0
            s_lalu = int(r_lalu["stunting"].sum()) if not r_lalu.empty else None
            if s_lalu is None: trend,status = "—","🔵 Data Awal"
            elif s > s_lalu: trend,status = f"▲ +{s-s_lalu}","⚠️ Naik"
            elif s < s_lalu: trend,status = f"▼ -{s_lalu-s}","✅ Turun"
            else: trend,status = "= Tetap","🟡 Tetap"
            rows.append({"Wilayah":wil,"Sasaran":sa,"Hadir":h,"Cakupan (%)":pct,"Stunting":s,"Trend":trend,"Status":status})

    df_lap = pd.DataFrame(rows)
    st.dataframe(df_lap, use_container_width=True, hide_index=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_lap.to_excel(writer, sheet_name=f"Laporan {bulan} {tahun}", index=False)
        df.to_excel(writer, sheet_name="Data Lengkap", index=False)
    buffer.seek(0)
    st.download_button("⬇️ Export ke Excel", data=buffer,
                       file_name=f"SITUNTAS_Laporan_{bulan}_{tahun}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True, type="primary")

# ─── KELOLA PENGGUNA ───────────────────────────────────────────────────────────
def page_kelola_user():
    render_header("Kelola Pengguna")
    users = load_users()

    tab1, tab2 = st.tabs(["👥 Daftar Pengguna", "➕ Tambah Pengguna"])

    with tab1:
        st.dataframe(users[["username","nama","role","wilayah","aktif"]], use_container_width=True, hide_index=True)

    with tab2:
        with st.form("form_add_user", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username *")
                new_nama = st.text_input("Nama Lengkap *")
                new_role = st.selectbox("Role *", ["pegawai","admin"])
            with col2:
                new_pass = st.text_input("Password *", type="password")
                new_wilayah = st.selectbox("Wilayah *", ["semua"] + list(WILAYAH.keys()))
                new_aktif = st.checkbox("Aktif", value=True)

            if st.form_submit_button("➕ Tambah Pengguna", type="primary", use_container_width=True):
                if not new_username or not new_nama or not new_pass:
                    st.error("❌ Username, nama, dan password wajib diisi.")
                elif new_username in users["username"].values:
                    st.error("❌ Username sudah ada.")
                else:
                    new_user = {"username":new_username,"password":hash_password(new_pass),
                                "nama":new_nama,"role":new_role,"wilayah":new_wilayah,"aktif":new_aktif}
                    users = pd.concat([users, pd.DataFrame([new_user])], ignore_index=True)
                    save_users(users)
                    st.success(f"✅ Pengguna {new_nama} berhasil ditambahkan!")
                    st.rerun()

# ─── KELOLA DATA ───────────────────────────────────────────────────────────────
def page_kelola_data(df):
    render_header("Kelola Data")
    tab1, tab2 = st.tabs(["✏️ Edit Data", "🗑️ Hapus Data"])

    with tab1:
        if df.empty:
            st.info("Belum ada data.")
        else:
            c1,c2,c3 = st.columns(3)
            with c1: t = st.selectbox("Tahun", sorted(df["tahun"].unique()), key="t_e")
            with c2: b = st.selectbox("Bulan", [x for x in BULAN_LIST if x in df[df["tahun"]==t]["bulan"].values], key="b_e")
            with c3:
                pos_opts = df[(df["tahun"]==t)&(df["bulan"]==b)]["posyandu"].unique().tolist()
                pos = st.selectbox("Posyandu", pos_opts, key="p_e")
            if pos:
                idx = df[(df["tahun"]==t)&(df["bulan"]==b)&(df["posyandu"]==pos)].index
                if len(idx) > 0:
                    i = idx[0]
                    with st.form("f_edit"):
                        e1,e2,e3 = st.columns(3)
                        with e1: ns = st.number_input("Sasaran", value=int(df.loc[i,"sasaran"]), min_value=0)
                        with e2: nh = st.number_input("Hadir", value=int(df.loc[i,"hadir"]), min_value=0)
                        with e3: nst = st.number_input("Stunting", value=int(df.loc[i,"stunting"]), min_value=0)
                        if st.form_submit_button("💾 Update", type="primary"):
                            df.loc[i,["sasaran","hadir","stunting"]] = [ns,nh,nst]
                            df.loc[i,"waktu_input"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            save_data(df)
                            st.success("✅ Data diupdate!")
                            st.rerun()

    with tab2:
        if df.empty:
            st.info("Belum ada data.")
        else:
            c1,c2,c3 = st.columns(3)
            with c1: td = st.selectbox("Tahun", sorted(df["tahun"].unique()), key="t_d")
            with c2: bd = st.selectbox("Bulan", [x for x in BULAN_LIST if x in df[df["tahun"]==td]["bulan"].values], key="b_d")
            with c3:
                pd_opts = df[(df["tahun"]==td)&(df["bulan"]==bd)]["posyandu"].unique().tolist()
                pd_sel = st.selectbox("Posyandu", pd_opts, key="p_d")
            konfirm = st.checkbox("✅ Saya yakin ingin menghapus data ini")
            if st.button("🗑️ Hapus", type="primary", disabled=not konfirm):
                df = df[~((df["tahun"]==td)&(df["bulan"]==bd)&(df["posyandu"]==pd_sel))].reset_index(drop=True)
                save_data(df)
                st.success("✅ Data dihapus!")
                st.rerun()
    return df

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    df = load_data()

    # PUBLIC MODE
    if st.session_state.is_public:
        menu, tahun, bulan = render_sidebar(role="publik")
        page_dashboard(df, tahun, bulan, is_public=True)
        return

    # NOT LOGGED IN
    if not st.session_state.logged_in:
        login_page()
        return

    # LOGGED IN
    user = st.session_state.user
    role = user["role"]
    menu, tahun, bulan = render_sidebar(role=role)

    if menu == "📊 Dashboard Utama":
        page_dashboard(df, tahun, bulan)
    elif menu == "📋 Input Data":
        df = page_input(df, user)
    elif menu == "📤 Import Google Sheets":
        df = page_import(df)
    elif menu == "📈 Analisis & Tren":
        page_analisis(df, tahun)
    elif menu == "📄 Laporan":
        page_laporan(df, tahun, bulan)
    elif menu == "👥 Kelola Pengguna":
        if role == "admin": page_kelola_user()
        else: st.error("❌ Akses ditolak.")
    elif menu == "⚙️ Kelola Data":
        if role == "admin": df = page_kelola_data(df)
        else: st.error("❌ Akses ditolak.")

if __name__ == "__main__":
    main()
