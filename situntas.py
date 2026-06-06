import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, io, hashlib, base64
from datetime import datetime

st.set_page_config(
    page_title="SITUNTAS — Kecamatan Kota SoE",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DATA WILAYAH & POSYANDU ────────────────────────────────────────────────────
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
TOTAL_POSYANDU = sum(len(v) for v in WILAYAH.values())  # = 33

BULAN_LIST = ["Januari","Februari","Maret","April","Mei","Juni",
              "Juli","Agustus","September","Oktober","November","Desember"]
TAHUN_LIST = [2024, 2025, 2026, 2027]
LOGO_PATH  = "logo_situntas.png"

def get_bulan_ke(b):
    try:    return BULAN_LIST.index(b) + 1
    except: return 0

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ─── GOOGLE SHEETS ──────────────────────────────────────────────────────────────
def get_gc():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(creds), None
    except Exception as e:
        return None, str(e)

def get_ws(tab):
    try:
        gc, err = get_gc()
        if gc is None: return None, err
        sh = gc.open(st.secrets.get("sheet_name","Data Stunting SITUNTAS Kota SoE"))
        return sh.worksheet(tab), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=30)
def load_data():
    ws, err = get_ws("data_stunting")
    if ws:
        try:
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                df["tahun"]    = pd.to_numeric(df["tahun"],    errors="coerce")
                df["sasaran"]  = pd.to_numeric(df["sasaran"],  errors="coerce").fillna(0).astype(int)
                df["hadir"]    = pd.to_numeric(df["hadir"],    errors="coerce").fillna(0).astype(int)
                df["stunting"] = pd.to_numeric(df["stunting"], errors="coerce").fillna(0).astype(int)
                df["bulan_ke"] = df["bulan"].apply(get_bulan_ke)
                return df
        except: pass
    if os.path.exists("data_situntas.csv"):
        return pd.read_csv("data_situntas.csv")
    return pd.DataFrame(columns=["tahun","bulan","bulan_ke","wilayah","posyandu",
                                  "sasaran","hadir","stunting","diinput_oleh","waktu_input"])

def save_data(df):
    load_data.clear()
    ws, err = get_ws("data_stunting")
    if ws is None:
        return False, f"Tidak bisa konek ke Google Sheets: {err}"
    try:
        import time
        rows = [df.columns.tolist()] + df.astype(str).values.tolist()
        ws.clear(); time.sleep(0.5)
        ws.update(rows); time.sleep(0.5)
        after = ws.get_all_values()
        if len(after) != len(df) + 1:
            return False, f"Verifikasi gagal: {len(after)-1} baris terbaca, harusnya {len(df)}"
        return True, f"OK — {len(df)} baris tersimpan"
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=30)
def load_users():
    ws, err = get_ws("users")
    if ws:
        try:
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                df.columns = [c.lower().strip() for c in df.columns]
                return df
        except: pass
    if os.path.exists("users_situntas.csv"):
        return pd.read_csv("users_situntas.csv")
    df = pd.DataFrame([{
        "username":"admin","password":hash_pw("situntas2025"),
        "nama":"Administrator","role":"admin","wilayah":"semua","aktif":"TRUE"
    }])
    save_users(df)
    return df

def save_users(df):
    load_users.clear()
    ws, err = get_ws("users")
    if ws is None:
        return False, f"Tidak bisa konek ke Google Sheets: {err}"
    try:
        import time
        rows = [df.columns.tolist()] + df.astype(str).values.tolist()
        ws.clear(); time.sleep(0.5)
        ws.update(rows); time.sleep(0.5)
        after = ws.get_all_values()
        if len(after) != len(df) + 1:
            return False, f"Verifikasi gagal: {len(after)-1} baris terbaca, harusnya {len(df)}"
        return True, "OK"
    except Exception as e:
        return False, str(e)

def verify_user(username, password):
    users = load_users()
    users["_ok"] = users["aktif"].astype(str).str.upper().isin(["TRUE","1","YES"])
    row = users[(users["username"]==username) & (users["_ok"]==True)]
    if row.empty: return None
    if str(row.iloc[0]["password"]) == hash_pw(password):
        return row.iloc[0].to_dict()
    return None

# ─── SESSION STATE ──────────────────────────────────────────────────────────────
for k, v in [("logged_in",False),("user",None),("is_public",False),
             ("hapus_target",None),("hapus_konfirm",False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── LOGO ───────────────────────────────────────────────────────────────────────
def logo_b64():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH,"rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Nunito:wght@700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
* { font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }

/* ── App Background ── */
.stApp {
    background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 30%, #E0F2FE 60%, #F0F9FF 100%);
    min-height: 100vh;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0C2D6B 0%, #1345A0 35%, #1A5CB8 65%, #1E6FD4 100%) !important;
    border-right: none !important;
    box-shadow: 6px 0 30px rgba(12,45,107,0.4) !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio > div > label {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 12px 18px;
    margin: 3px 0;
    display: flex; align-items: center; gap: 10px;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    cursor: pointer;
    font-weight: 500;
    font-size: 0.88rem;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(255,255,255,0.14);
    border-color: rgba(255,255,255,0.28);
    transform: translateX(4px);
}
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: rgba(255,255,255,0.22) !important;
    border-color: rgba(255,255,255,0.45) !important;
    font-weight: 700 !important;
    box-shadow: inset 3px 0 0 rgba(255,255,255,0.6);
}

/* ── Header Banner ── */
.hdr {
    background: linear-gradient(135deg, #0C2D6B 0%, #1345A0 40%, #1976D2 75%, #2196F3 100%);
    border-radius: 24px;
    padding: 2rem 2.8rem;
    margin-bottom: 2rem;
    display: flex; align-items: center; gap: 1.8rem;
    box-shadow: 0 12px 50px rgba(12,45,107,0.35), 0 4px 16px rgba(21,101,192,0.2);
    position: relative; overflow: hidden;
}
.hdr::before {
    content: '';
    position: absolute; top: -80%; right: -8%; width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 65%);
    border-radius: 50%;
}
.hdr::after {
    content: '';
    position: absolute; bottom: -60%; left: 5%; width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(33,150,243,0.25) 0%, transparent 65%);
    border-radius: 50%;
}
.hdr-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    color: #fff; font-size: 0.67rem; font-weight: 700;
    letter-spacing: 2.5px; text-transform: uppercase;
    padding: 5px 16px; border-radius: 30px; margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}
.hdr-title {
    font-family: 'Nunito', sans-serif;
    font-size: 2.4rem; font-weight: 900; color: #fff; margin: 0; line-height: 1.1;
    text-shadow: 0 3px 15px rgba(0,0,0,0.2);
    letter-spacing: -0.5px;
}
.hdr-sub { color: rgba(255,255,255,0.82); font-size: 0.86rem; margin: 0.5rem 0 0; line-height: 1.7; }

/* ── Metric Cards ── */
.mgrid {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 1.4rem; margin-bottom: 2rem;
}
@media(max-width:1000px) { .mgrid { grid-template-columns: repeat(2,1fr); } }
@media(max-width:600px)  { .mgrid { grid-template-columns: 1fr; } }

.mcard {
    background: #fff;
    border-radius: 20px; padding: 1.6rem 1.8rem;
    position: relative; overflow: hidden;
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s;
    box-shadow: 0 4px 24px rgba(21,101,192,0.09), 0 1px 4px rgba(0,0,0,0.04);
    border: 1px solid rgba(219,234,254,0.8);
}
.mcard:hover {
    transform: translateY(-6px);
    box-shadow: 0 16px 45px rgba(21,101,192,0.22), 0 4px 12px rgba(0,0,0,0.06);
}
.mcard::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 5px;
    border-radius: 20px 20px 0 0;
}
.mc-r::before { background: linear-gradient(90deg, #FF5252, #E53935, #B71C1C); }
.mc-b::before { background: linear-gradient(90deg, #40C4FF, #1976D2, #0D47A1); }
.mc-g::before { background: linear-gradient(90deg, #69F0AE, #43A047, #1B5E20); }
.mc-y::before { background: linear-gradient(90deg, #FFD740, #FB8C00, #E65100); }

.mcard-icon-wrap {
    width: 48px; height: 48px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; margin-bottom: 1rem;
}
.mc-r .mcard-icon-wrap { background: rgba(229,57,53,0.1); }
.mc-b .mcard-icon-wrap { background: rgba(25,118,210,0.1); }
.mc-g .mcard-icon-wrap { background: rgba(67,160,71,0.1); }
.mc-y .mcard-icon-wrap { background: rgba(251,140,0,0.1); }

.mlabel { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.8px; color: #94A3B8; margin-bottom: 0.5rem; }
.mval   { font-size: 2.6rem; font-weight: 900; line-height: 1; color: #0C2D6B; letter-spacing: -1.5px; }
.msub   { font-size: 0.77rem; color: #94A3B8; margin-top: 0.5rem; line-height: 1.5; }
.dup    { color: #E53935; font-size: 0.77rem; font-weight: 700; }
.ddown  { color: #43A047; font-size: 0.77rem; font-weight: 700; }

/* ── Section Title ── */
.sec {
    display: flex; align-items: center; gap: 12px;
    margin: 2rem 0 1.2rem;
    padding-bottom: 0.8rem;
    border-bottom: 1.5px solid rgba(219,234,254,0.9);
}
.sec-bar {
    width: 5px; height: 22px;
    background: linear-gradient(180deg, #1976D2, #42A5F5);
    border-radius: 3px; flex-shrink: 0;
}
.sec-text { color: #1345A0; font-size: 1rem; font-weight: 700; letter-spacing: -0.2px; }

/* ── Alert Boxes ── */
.abox {
    border-radius: 14px; padding: 1rem 1.4rem;
    font-size: 0.86rem; margin-bottom: 1.2rem;
    line-height: 1.7; display: flex; gap: 10px; align-items: flex-start;
}
.a-info  { background: rgba(219,234,254,0.6); border-left: 4px solid #1976D2; color: #1345A0; border: 1px solid rgba(219,234,254,0.9); border-left: 4px solid #1976D2; }
.a-warn  { background: rgba(255,237,213,0.6); border-left: 4px solid #FB8C00; color: #92400E; border: 1px solid rgba(254,215,170,0.8); border-left: 4px solid #FB8C00; }
.a-green { background: rgba(220,252,231,0.7); border-left: 4px solid #43A047; color: #14532D; border: 1px solid rgba(187,247,208,0.9); border-left: 4px solid #43A047; }
.a-red   { background: rgba(254,226,226,0.7); border-left: 4px solid #E53935; color: #7F1D1D; border: 1px solid rgba(254,202,202,0.9); border-left: 4px solid #E53935; }
.a-pub   { background: linear-gradient(135deg, rgba(220,252,231,0.8), rgba(187,247,208,0.6)); border-left: 4px solid #43A047; color: #14532D; font-weight: 600; border: 1px solid rgba(187,247,208,0.9); border-left: 4px solid #43A047; }

/* ── Chart Container ── */
.cbox {
    background: #fff; border-radius: 20px; padding: 1.6rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 4px 24px rgba(21,101,192,0.07), 0 1px 4px rgba(0,0,0,0.03);
    border: 1px solid rgba(219,234,254,0.7);
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1976D2, #1345A0) !important;
    border: none !important; border-radius: 12px !important;
    color: #fff !important; font-weight: 600 !important;
    box-shadow: 0 4px 16px rgba(25,118,210,0.35) !important;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
    padding: 0.65rem 1.6rem !important; font-size: 0.88rem !important;
    letter-spacing: 0.2px !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2196F3, #1976D2) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(25,118,210,0.45) !important;
}
.stButton > button:active { transform: translateY(0px) !important; }

/* ── Inputs ── */
.stTextInput > div > div,
.stSelectbox > div > div,
.stNumberInput > div > div {
    background: #F8FAFF !important;
    border: 1.5px solid #BFDBFE !important;
    border-radius: 12px !important;
    transition: all 0.2s !important;
}
.stTextInput > div > div:focus-within,
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div:focus-within {
    border-color: #1976D2 !important;
    box-shadow: 0 0 0 4px rgba(25,118,210,0.12) !important;
    background: #fff !important;
}

/* ── Labels ── */
label { color: #1345A0 !important; font-size: 0.83rem !important; font-weight: 600 !important; }
p, div { color: #1E3A5F; }
h1,h2,h3 { color: #1345A0 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(239,246,255,0.9);
    border-radius: 16px; padding: 6px; gap: 4px;
    border: 1px solid rgba(219,234,254,0.8);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px; color: #1976D2 !important;
    font-weight: 600; padding: 0.55rem 1.3rem;
    font-size: 0.87rem; transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1976D2, #1345A0) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(25,118,210,0.35) !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border-radius: 16px !important; overflow: hidden !important;
    box-shadow: 0 4px 20px rgba(21,101,192,0.09) !important;
    border: 1px solid rgba(219,234,254,0.8) !important;
}

/* ── Dropdown Options (fix teks putih di sidebar) ── */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div {
    color: #1E3A5F !important;
    background: #fff !important;
}
[data-baseweb="popover"] ul li,
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] ul li,
[data-baseweb="menu"] [role="option"] {
    color: #1E3A5F !important;
    background: #fff !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="menu"] [role="option"]:hover {
    background: #EFF6FF !important;
    color: #1345A0 !important;
}
[data-baseweb="popover"] [aria-selected="true"],
[data-baseweb="menu"] [aria-selected="true"] {
    background: #DBEAFE !important;
    color: #1345A0 !important;
    font-weight: 700 !important;
}
/* Input teks di selectbox sidebar tetap terbaca */
[data-testid="stSidebar"] .stSelectbox input {
    color: #1E3A5F !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #EFF6FF; border-radius: 3px; }
::-webkit-scrollbar-thumb { background: rgba(25,118,210,0.35); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(25,118,210,0.55); }

/* ── Role Badges ── */
.role-badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 12px; border-radius: 30px;
    font-size: 0.68rem; font-weight: 700;
    letter-spacing: 1.2px; text-transform: uppercase;
}
.rb-admin   { background: rgba(229,57,53,0.12); color: #B71C1C; border: 1px solid rgba(229,57,53,0.2); }
.rb-pegawai { background: rgba(25,118,210,0.1);  color: #1345A0; border: 1px solid rgba(25,118,210,0.18); }

/* ── Login Card ── */
.login-card {
    background: rgba(255,255,255,0.92);
    border-radius: 24px; padding: 2.5rem;
    box-shadow: 0 20px 60px rgba(12,45,107,0.15), 0 4px 16px rgba(0,0,0,0.06);
    border: 1px solid rgba(219,234,254,0.8);
    backdrop-filter: blur(20px);
}

/* ── Divider ── */
hr { border-color: rgba(219,234,254,0.6) !important; }

/* ── Form submit button full width ── */
.stFormSubmitButton > button {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(239,246,255,0.5)",
    font=dict(color="#1E3A5F", family="Plus Jakarta Sans", size=12),
    xaxis=dict(gridcolor="rgba(25,118,210,0.08)", tickfont=dict(color="#1976D2"), linecolor="rgba(25,118,210,0.12)"),
    yaxis=dict(gridcolor="rgba(25,118,210,0.08)", tickfont=dict(color="#1976D2"), linecolor="rgba(25,118,210,0.12)"),
    margin=dict(l=20,r=20,t=50,b=20),
    hoverlabel=dict(bgcolor="#fff", font=dict(color="#1E3A5F"), bordercolor="rgba(25,118,210,0.2)"),
    legend=dict(bgcolor="rgba(255,255,255,0.95)", borderwidth=1, bordercolor="rgba(219,234,254,0.8)", font=dict(color="#1E3A5F")),
)

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def render_header(subtitle=""):
    lb = logo_b64()
    img = (f'<img src="data:image/png;base64,{lb}" '
           f'style="width:82px;height:82px;object-fit:contain;border-radius:16px;'
           f'background:rgba(255,255,255,0.95);padding:6px;flex-shrink:0;'
           f'box-shadow:0 6px 20px rgba(0,0,0,0.18);">') \
           if lb else '<div style="font-size:3rem;">🏥</div>'
    sub = (f'<br><span style="color:rgba(255,255,255,.78);font-size:.79rem;font-style:italic;">'
           f'{subtitle}</span>') if subtitle else ""
    st.markdown(
        f'<div class="hdr">{img}'
        f'<div style="position:relative;z-index:1;">'
        f'<div class="hdr-badge">🏥 Sistem Informasi Digital</div>'
        f'<div class="hdr-title">SITUNTAS</div>'
        f'<div class="hdr-sub">Sistem Informasi Terpadu Monitoring Angka Stunting Secara Realtime<br>'
        f'Kecamatan Kota SoE — Kabupaten Timor Tengah Selatan{sub}</div>'
        f'</div></div>',
        unsafe_allow_html=True)

def abox(msg, t="info"):
    cls = {"info":"a-info","warn":"a-warn","green":"a-green","red":"a-red","pub":"a-pub"}.get(t,"a-info")
    st.markdown(f'<div class="abox {cls}">{msg}</div>', unsafe_allow_html=True)

def sec(title):
    st.markdown(f'<div class="sec"><span class="sec-bar"></span><span class="sec-text">{title}</span></div>', unsafe_allow_html=True)

# ─── LOGIN ───────────────────────────────────────────────────────────────────────
def login_page():
    _, col, _ = st.columns([1,1.2,1])
    with col:
        lb = logo_b64()
        img = (f'<img src="data:image/png;base64,{lb}" '
               f'style="width:110px;height:110px;object-fit:contain;border-radius:20px;'
               f'box-shadow:0 8px 30px rgba(21,101,192,0.25);">') if lb else '<div style="font-size:4rem;">🏥</div>'
        st.markdown(
            f'<div style="text-align:center;padding:2.5rem 0 1.5rem;">{img}'
            f'<div style="font-family:Nunito,sans-serif;font-size:2.4rem;font-weight:900;'
            f'color:#0C2D6B;margin-top:1rem;letter-spacing:-0.5px;">SITUNTAS</div>'
            f'<div style="font-size:.75rem;color:#1976D2;letter-spacing:2px;text-transform:uppercase;'
            f'margin-top:8px;font-weight:700;">Sistem Informasi Terpadu Monitoring Stunting</div>'
            f'<div style="font-size:.82rem;color:#64B5F6;margin-top:8px;font-weight:500;">'
            f'Kecamatan Kota SoE &middot; Kab. Timor Tengah Selatan</div>'
            f'</div>', unsafe_allow_html=True)
        with st.form("lf"):
            u = st.text_input("Username", placeholder="Masukkan username")
            p = st.text_input("Password", type="password", placeholder="Masukkan password")
            ca, cb = st.columns(2)
            with ca: lb_btn = st.form_submit_button("🔐  MASUK", use_container_width=True, type="primary")
            with cb: pb_btn = st.form_submit_button("🌐  Publik", use_container_width=True)
            if lb_btn:
                user = verify_user(u.strip(), p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user      = user
                    st.session_state.is_public = False
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah.")
            if pb_btn:
                st.session_state.is_public = True
                st.rerun()
        st.markdown('<div style="text-align:center;font-size:.73rem;color:#94A3B8;'
                    'margin-top:.8rem;padding-bottom:2rem;">'
                    '© 2026 Kecamatan Kota SoE &middot; Dikembangkan oleh Margaritha Liufeto, S.H</div>',
                    unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
def render_sidebar(role="publik"):
    with st.sidebar:
        lb = logo_b64()
        if lb:
            st.markdown(
                f'<div style="text-align:center;padding:1.5rem 0 .8rem;">'
                f'<img src="data:image/png;base64,{lb}" '
                f'style="width:88px;height:88px;object-fit:contain;border-radius:18px;'
                f'background:rgba(255,255,255,0.95);padding:6px;box-shadow:0 6px 18px rgba(0,0,0,0.2);">'
                f'<div style="font-family:Nunito,sans-serif;font-size:1.45rem;font-weight:900;'
                f'margin-top:.8rem;letter-spacing:-0.3px;">SITUNTAS</div>'
                f'<div style="font-size:.64rem;opacity:.55;letter-spacing:1.5px;'
                f'text-transform:uppercase;margin-top:3px;">Kecamatan Kota SoE</div>'
                f'</div><hr style="border-color:rgba(255,255,255,.1);margin:.5rem 0 .8rem;">',
                unsafe_allow_html=True)

        if role == "publik":
            menu = st.radio("Menu", ["📊 Dashboard","📈 Analisis & Tren"], label_visibility="collapsed")
            st.markdown('<div style="padding:.7rem 1.1rem;background:rgba(255,255,255,.1);'
                        'border-radius:12px;margin-bottom:.8rem;font-size:.79rem;font-weight:600;'
                        'border:1px solid rgba(255,255,255,.15);">'
                        '🌐 Mode Publik — Akses Terbatas</div>', unsafe_allow_html=True)
            if st.button("🔐 Login sebagai Pegawai", use_container_width=True):
                st.session_state.is_public = False
                st.session_state.logged_in = False
                st.rerun()
        else:
            if role == "admin":
                opts = [
                    "📊 Dashboard Utama",
                    "📋 Input Data",
                    "📤 Import CSV",
                    "📈 Analisis & Tren",
                    "📄 Laporan",
                    "👥 Kelola Pengguna",
                    "⚙️ Kelola Data",
                    "🔧 Test Koneksi",
                ]
            else:
                opts = [
                    "📊 Dashboard Utama",
                    "📋 Input Data",
                    "📤 Import CSV",
                    "⚙️ Kelola Data",
                ]
            menu = st.radio("Menu", opts, label_visibility="collapsed")

        st.markdown("<hr style='border-color:rgba(255,255,255,.1);margin:.8rem 0;'>", unsafe_allow_html=True)
        st.markdown("<span style='font-size:.78rem;font-weight:700;opacity:.85;'>🗓️ Filter Periode</span>",
                    unsafe_allow_html=True)
        curr_y = datetime.now().year
        tahun  = st.selectbox("Tahun", TAHUN_LIST,
                              index=TAHUN_LIST.index(curr_y) if curr_y in TAHUN_LIST else 2,
                              label_visibility="collapsed")
        bulan  = st.selectbox("Bulan", BULAN_LIST, index=datetime.now().month-1,
                               label_visibility="collapsed")

        if role != "publik":
            st.markdown("<hr style='border-color:rgba(255,255,255,.1);margin:.8rem 0;'>", unsafe_allow_html=True)
            u   = st.session_state.user
            rb  = "rb-admin" if u["role"]=="admin" else "rb-pegawai"
            wil = "Semua wilayah" if str(u.get("wilayah","")).lower() in ["semua",""] else str(u["wilayah"])
            st.markdown(
                f'<div style="font-size:.77rem;line-height:1.7;opacity:.92;">'
                f'Login sebagai:<br>'
                f'<b style="font-size:.9rem;">{u["nama"]}</b><br>'
                f'<span class="role-badge {rb}" style="margin:.35rem 0;display:inline-flex;">'
                f'{str(u["role"]).upper()}</span><br>'
                f'<span style="font-size:.7rem;opacity:.65;">{wil}</span></div>',
                unsafe_allow_html=True)
            st.markdown("<div style='height:.4rem;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Keluar", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user      = None
                st.rerun()

    return menu, tahun, bulan

# ─── DASHBOARD ──────────────────────────────────────────────────────────────────
def page_dashboard(df, tahun, bulan, is_public=False):
    render_header()
    if is_public:
        abox("🌐 <b>Dashboard Publik</b> — Data ditampilkan secara terbuka untuk transparansi masyarakat.", "pub")

    bk  = get_bulan_ke(bulan)
    db  = df[(df["tahun"]==tahun)&(df["bulan"]==bulan)] if not df.empty else pd.DataFrame()
    bl  = BULAN_LIST[bk-2] if bk > 1 else None
    dl  = df[(df["tahun"]==tahun)&(df["bulan"]==bl)] if (bl and not df.empty) else pd.DataFrame()

    ts  = int(db["stunting"].sum()) if not db.empty else 0
    th  = int(db["hadir"].sum())    if not db.empty else 0
    tsa = int(db["sasaran"].sum())  if not db.empty else 0
    wl  = db["wilayah"].nunique()   if not db.empty else 0
    pa  = db["posyandu"].nunique()  if not db.empty else 0
    ph  = round(th/tsa*100,1)       if tsa > 0 else 0
    sl  = int(dl["stunting"].sum()) if not dl.empty else None

    def dlt(n, p):
        if p is None: return ""
        d = n - p
        if d > 0: return f'<span class="dup">▲ +{d} dari bln lalu</span>'
        if d < 0: return f'<span class="ddown">▼ {abs(d)} dari bln lalu</span>'
        return '<span style="color:#94A3B8;font-size:.76rem;">= sama seperti bln lalu</span>'

    sec(f"Ringkasan {bulan} {tahun}")
    st.markdown(f"""
    <div class="mgrid">
      <div class="mcard mc-r">
        <div class="mcard-icon-wrap">🔴</div>
        <div class="mlabel">Total Kasus Stunting</div>
        <div class="mval">{ts:,}</div>
        <div class="msub">{dlt(ts,sl) or '&nbsp;'}</div>
      </div>
      <div class="mcard mc-b">
        <div class="mcard-icon-wrap">👶</div>
        <div class="mlabel">Kehadiran Posyandu</div>
        <div class="mval">{th:,}</div>
        <div class="msub"><span style="color:#1976D2;font-weight:700;">{ph}%</span> dari {tsa:,} sasaran</div>
      </div>
      <div class="mcard mc-g">
        <div class="mcard-icon-wrap">🏘️</div>
        <div class="mlabel">Wilayah Melapor</div>
        <div class="mval">{wl}</div>
        <div class="msub">dari {len(WILAYAH)} Kel/Desa</div>
      </div>
      <div class="mcard mc-y">
        <div class="mcard-icon-wrap">🏥</div>
        <div class="mlabel">Posyandu Aktif</div>
        <div class="mval">{pa}</div>
        <div class="msub">dari {TOTAL_POSYANDU} posyandu</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if db.empty:
        abox(f"⚠️ Belum ada data untuk <b>{bulan} {tahun}</b>. Silakan input data terlebih dahulu.", "warn")
        return

    dw = db.groupby("wilayah",as_index=False).agg(
        stunting=("stunting","sum"), hadir=("hadir","sum"), sasaran=("sasaran","sum"))
    if not dl.empty:
        dw2 = dl.groupby("wilayah",as_index=False).agg(sl2=("stunting","sum"))
        dw  = dw.merge(dw2, on="wilayah", how="left")
        dw["trend"] = dw.apply(
            lambda r: "Naik"  if r["stunting"] > r.get("sl2", r["stunting"])
                 else "Turun" if r["stunting"] < r.get("sl2", r["stunting"])
                 else "Tetap", axis=1)
    else:
        dw["trend"] = "Data Awal"
    dw["ph2"] = (dw["hadir"]/dw["sasaran"]*100).round(1).fillna(0)
    dw = dw.sort_values("stunting", ascending=True)
    wm = {"Naik":"#EF5350","Turun":"#66BB6A","Tetap":"#FFA726","Data Awal":"#42A5F5"}

    sec(f"Kasus Stunting per Kelurahan/Desa — {bulan} {tahun}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=dw["stunting"], y=dw["wilayah"], orientation="h",
            marker_color=[wm.get(t,"#1976D2") for t in dw["trend"]],
            marker_line_width=0,
            text=dw["stunting"], textposition="outside",
            textfont=dict(color="#1E3A5F",size=12,weight=700),
            hovertemplate="<b>%{y}</b><br>Stunting: <b>%{x}</b><extra></extra>"))
        fig.update_layout(title=dict(text="Kasus Stunting per Wilayah",
                          font=dict(color="#1E3A5F",size=14,weight=700),x=0),
                          height=470, **PL)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:.75rem;color:#64748B;margin-top:-6px;padding:0 4px;">'
                    '🔴 Naik &nbsp;|&nbsp; 🟢 Turun &nbsp;|&nbsp; 🟡 Tetap &nbsp;|&nbsp; 🔵 Data Awal</div>',
                    unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=dw["sasaran"],y=dw["wilayah"],orientation="h",
                              name="Sasaran",marker_color="rgba(219,234,254,0.9)",marker_line_width=0))
        fig2.add_trace(go.Bar(x=dw["hadir"],y=dw["wilayah"],orientation="h",
                              name="Hadir",marker_color="#1976D2",marker_line_width=0,
                              text=[f"{v} ({p}%)" for v,p in zip(dw["hadir"],dw["ph2"])],
                              textposition="outside",textfont=dict(color="#1E3A5F",size=11)))
        fig2.update_layout(barmode="overlay",
                           title=dict(text="Sasaran vs Kehadiran",
                           font=dict(color="#1E3A5F",size=14,weight=700),x=0),
                           height=470, **PL)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    sec("Tabel Rekapitulasi Wilayah")
    df_tb = dw[["wilayah","sasaran","hadir","ph2","stunting","trend"]].rename(columns={
        "wilayah":"Wilayah","sasaran":"Sasaran","hadir":"Hadir",
        "ph2":"Cakupan (%)","stunting":"Kasus Stunting","trend":"Trend"})
    st.dataframe(df_tb.sort_values("Kasus Stunting",ascending=False),
                 use_container_width=True, hide_index=True)

# ─── INPUT DATA ──────────────────────────────────────────────────────────────────
def page_input(df, user):
    render_header("Input Data Bulanan")
    role    = str(user.get("role","")).lower()
    wilayah = str(user.get("wilayah","semua"))
    opts    = list(WILAYAH.keys()) if (role=="admin" or wilayah.lower()=="semua") else [wilayah]

    rb  = "rb-admin" if role=="admin" else "rb-pegawai"
    wik = "Akses <b>semua wilayah</b>" if role=="admin" else f"Wilayah: <b>{wilayah}</b>"
    abox(f'<span class="role-badge {rb}">{role.upper()}</span> &nbsp;{user["nama"]} &nbsp;|&nbsp; {wik}')

    with st.form("fi", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ti = st.selectbox("Tahun *", TAHUN_LIST, index=2)
            bi = st.selectbox("Bulan *", BULAN_LIST, index=datetime.now().month-1)
            wi = st.selectbox("Kelurahan/Desa *", opts)
        with c2:
            pi  = st.selectbox("Posyandu *", WILAYAH.get(wi,[]))
            sai = st.number_input("Total Sasaran (jumlah anak terdaftar) *", min_value=0, step=1)
            hi  = st.number_input("Jumlah Kehadiran *", min_value=0, step=1)
        sti = st.number_input("Jumlah Kasus Stunting *", min_value=0, step=1)
        sub = st.form_submit_button("💾  SIMPAN DATA", use_container_width=True, type="primary")

    if sub:
        if sai == 0:
            st.error("❌ Total sasaran tidak boleh 0.")
        elif hi > sai:
            st.error("❌ Kehadiran tidak boleh melebihi total sasaran.")
        elif sti > hi:
            st.error("❌ Kasus stunting tidak boleh melebihi jumlah kehadiran.")
        else:
            load_data.clear()
            df_f = load_data()
            cek  = df_f[(df_f["tahun"]==ti)&(df_f["bulan"]==bi)&(df_f["posyandu"]==pi)] \
                   if not df_f.empty else pd.DataFrame()
            if not cek.empty:
                st.warning(f"⚠️ Data {pi} — {bi} {ti} sudah ada. Gunakan menu Kelola Data untuk mengubah.")
            else:
                nr = {"tahun":ti,"bulan":bi,"bulan_ke":get_bulan_ke(bi),"wilayah":wi,"posyandu":pi,
                      "sasaran":sai,"hadir":hi,"stunting":sti,
                      "diinput_oleh":user["username"],
                      "waktu_input":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                df_f = pd.concat([df_f, pd.DataFrame([nr])], ignore_index=True)
                ok, msg = save_data(df_f)
                if ok:
                    st.success(f"✅ Data {pi} — {bi} {ti} berhasil disimpan!")
                else:
                    st.error(f"❌ Gagal simpan: {msg}")
                st.rerun()

    if not df.empty:
        sec("10 Data Terbaru")
        st.dataframe(df.sort_values("waktu_input",ascending=False).head(10),
                     use_container_width=True, hide_index=True)
    return df

# ─── IMPORT CSV ───────────────────────────────────────────────────────────────────
def page_import(df):
    render_header("Import Data CSV")
    abox("📥 <b>Cara pakai:</b><br>"
         "1. Siapkan file CSV dengan kolom: <code>tahun, bulan, wilayah, posyandu, sasaran, hadir, stunting</code><br>"
         "2. Upload file di bawah ini → Klik <b>Konfirmasi Import</b>")
    sec("Contoh Format CSV")
    st.dataframe(pd.DataFrame([{
        "tahun":2026,"bulan":"Mei","wilayah":"Kelurahan Cendana",
        "posyandu":"Persit","sasaran":45,"hadir":38,"stunting":5}]),
        use_container_width=True, hide_index=True)
    up = st.file_uploader("📂 Upload File CSV", type=["csv"])
    if up:
        try:
            di = pd.read_csv(up)
            sec("Preview Data")
            st.dataframe(di.head(10), use_container_width=True, hide_index=True)
            abox(f"📊 Total <b>{len(di)}</b> baris data siap diimport.")
            if st.button("✅ Konfirmasi Import", type="primary", use_container_width=True):
                with st.spinner("Menyimpan data ke Google Sheets..."):
                    di["bulan_ke"]     = di["bulan"].apply(get_bulan_ke)
                    di["diinput_oleh"] = "import_csv"
                    di["waktu_input"]  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df = pd.concat([df, di], ignore_index=True)\
                           .drop_duplicates(subset=["tahun","bulan","posyandu"], keep="last")
                    ok, msg = save_data(df)
                if ok:
                    st.success(f"✅ {len(di)} data berhasil diimport!")
                    st.rerun()
                else:
                    st.error(f"❌ Gagal simpan: {msg}")
                    st.info("💡 Cek halaman **Test Koneksi** untuk memeriksa koneksi Google Sheets.")
        except Exception as e:
            st.error(f"❌ Error membaca file: {e}")
    return df

# ─── ANALISIS ────────────────────────────────────────────────────────────────────
def page_analisis(df, tahun):
    render_header("Analisis & Tren")
    dt = df[df["tahun"]==tahun] if not df.empty else pd.DataFrame()
    if dt.empty:
        abox(f"⚠️ Belum ada data untuk tahun {tahun}.", "warn"); return

    da = dt.groupby(["bulan_ke","bulan"],as_index=False).agg(
        stunting=("stunting","sum"), hadir=("hadir","sum"), sasaran=("sasaran","sum")
    ).sort_values("bulan_ke")
    da["ph"] = (da["hadir"]/da["sasaran"]*100).round(1)

    t1, t2 = st.tabs(["📉 Tren Stunting","👶 Tren Kehadiran"])
    with t1:
        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(
            x=da["bulan"], y=da["stunting"], mode="lines+markers",
            line=dict(color="#E53935",width=3.5,shape="spline"),
            marker=dict(size=10,color="#E53935",line=dict(color="#fff",width=2.5)),
            fill="tozeroy", fillcolor="rgba(229,57,53,0.07)",
            hovertemplate="<b>%{x}</b><br>Stunting: <b>%{y}</b><extra></extra>"))
        fig.update_layout(title=dict(text=f"Tren Kasus Stunting — {tahun}",
                          font=dict(color="#1E3A5F",size=15,weight=700),x=0), height=380, **PL)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        dw = dt.groupby(["wilayah","bulan_ke","bulan"],as_index=False)\
               .agg(stunting=("stunting","sum")).sort_values("bulan_ke")
        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig2 = px.line(dw,x="bulan",y="stunting",color="wilayah",markers=True,
                       title=f"Tren Stunting per Wilayah — {tahun}",
                       labels={"bulan":"Bulan","stunting":"Kasus","wilayah":"Wilayah"})
        fig2.update_traces(line_width=2.5,marker_size=8)
        fig2.update_layout(height=430, **PL)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=da["bulan"],y=da["sasaran"],name="Sasaran",
                              marker_color="rgba(219,234,254,0.9)",marker_line_width=0))
        fig3.add_trace(go.Bar(x=da["bulan"],y=da["hadir"],name="Hadir",
                              marker_color="#1976D2",marker_line_width=0))
        fig3.update_layout(barmode="overlay",
                           title=dict(text=f"Kehadiran vs Sasaran — {tahun}",
                           font=dict(color="#1E3A5F",size=15,weight=700),x=0), height=380, **PL)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cbox">', unsafe_allow_html=True)
        fig4 = go.Figure(go.Scatter(
            x=da["bulan"], y=da["ph"], mode="lines+markers",
            line=dict(color="#43A047",width=3.5,shape="spline"),
            marker=dict(size=10,color="#43A047",line=dict(color="#fff",width=2.5)),
            fill="tozeroy", fillcolor="rgba(67,160,71,0.07)"))
        fig4.add_hline(y=80, line_dash="dash", line_color="#FB8C00", line_width=2,
                       annotation_text="  Target 80%", annotation_font_color="#FB8C00",
                       annotation_font_size=12)
        fig4.update_layout(title=dict(text="Cakupan Kehadiran Posyandu (%)",
                           font=dict(color="#1E3A5F",size=15,weight=700),x=0), height=380, **PL)
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

# ─── LAPORAN ─────────────────────────────────────────────────────────────────────
def page_laporan(df, tahun, bulan):
    render_header("Laporan Bulanan")
    db = df[(df["tahun"]==tahun)&(df["bulan"]==bulan)] if not df.empty else pd.DataFrame()
    if db.empty:
        abox(f"⚠️ Belum ada data untuk {bulan} {tahun}.", "warn"); return

    bk  = get_bulan_ke(bulan)
    bl  = BULAN_LIST[bk-2] if bk > 1 else None
    dl  = df[(df["tahun"]==tahun)&(df["bulan"]==bl)] if (bl and not df.empty) else pd.DataFrame()

    rows = []
    for wil in WILAYAH:
        r  = db[db["wilayah"]==wil]
        rl = dl[dl["wilayah"]==wil] if not dl.empty else pd.DataFrame()
        if r.empty:
            rows.append({"Wilayah":wil,"Sasaran":"—","Hadir":"—","Cakupan (%)":"—",
                         "Stunting":"—","Trend":"—","Status":"❌ Belum Lapor"})
        else:
            s  = int(r["stunting"].sum()); h = int(r["hadir"].sum()); sa = int(r["sasaran"].sum())
            p  = round(h/sa*100,1) if sa > 0 else 0
            sl2= int(rl["stunting"].sum()) if not rl.empty else None
            if sl2 is None:   tr,st2 = "—","🔵 Data Awal"
            elif s > sl2:     tr,st2 = f"▲ +{s-sl2}","⚠️ Naik"
            elif s < sl2:     tr,st2 = f"▼ -{sl2-s}","✅ Turun"
            else:             tr,st2 = "= Tetap","🟡 Tetap"
            rows.append({"Wilayah":wil,"Sasaran":sa,"Hadir":h,"Cakupan (%)":p,
                         "Stunting":s,"Trend":tr,"Status":st2})

    df_lap = pd.DataFrame(rows)
    sec(f"Rekap Laporan {bulan} {tahun}")
    st.dataframe(df_lap, use_container_width=True, hide_index=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        df_lap.to_excel(wr, sheet_name=f"Laporan {bulan} {tahun}", index=False)
        if not df.empty: df.to_excel(wr, sheet_name="Data Lengkap", index=False)
    buf.seek(0)
    st.download_button(
        "⬇️  Export ke Excel", data=buf,
        file_name=f"SITUNTAS_{bulan}_{tahun}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True, type="primary")

# ─── KELOLA PENGGUNA ──────────────────────────────────────────────────────────────
def page_kelola_user():
    render_header("Kelola Pengguna")
    # Selalu load fresh dari Sheets, bukan cache
    load_users.clear()
    users = load_users()
    t1, t2, t3, t4 = st.tabs(["👥 Daftar Pengguna","➕ Tambah Pengguna","🗑️ Hapus Pengguna","🔑 Reset Password"])

    with t1:
        sec(f"Total {len(users)} Pengguna Terdaftar")
        st.dataframe(users[["username","nama","role","wilayah","aktif"]],
                     use_container_width=True, hide_index=True)
        if st.button("🔄 Refresh Data Pengguna", use_container_width=True):
            load_users.clear()
            st.rerun()

    with t2:
        with st.form("fu", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nu  = st.text_input("Username *")
                nn  = st.text_input("Nama Lengkap *")
                nr  = st.selectbox("Role *", ["pegawai","admin"])
            with c2:
                np_ = st.text_input("Password *", type="password")
                nw  = st.selectbox("Wilayah *", ["semua"]+list(WILAYAH.keys()))
                na  = st.checkbox("Aktif", value=True)
            if st.form_submit_button("➕ Tambah Pengguna", type="primary", use_container_width=True):
                if not nu or not nn or not np_:
                    st.error("❌ Username, nama, dan password wajib diisi.")
                elif nu in users["username"].values:
                    st.error(f"❌ Username '{nu}' sudah digunakan.")
                else:
                    baru = {"username":nu,"password":hash_pw(np_),"nama":nn,
                            "role":nr,"wilayah":nw,"aktif":str(na).upper()}
                    users_baru = pd.concat([users, pd.DataFrame([baru])], ignore_index=True)
                    with st.spinner("Menyimpan pengguna ke Google Sheets..."):
                        ok, msg = save_users(users_baru)
                    if ok:
                        st.success(f"✅ Pengguna {nn} berhasil ditambahkan dan tersimpan!")
                        st.rerun()
                    else:
                        st.error(f"❌ Gagal simpan ke Google Sheets: {msg}")
                        st.info("💡 Cek tab **Test Koneksi** untuk memeriksa koneksi.")

    with t3:
        abox("⚠️ Hapus pengguna dari sistem. <b>Akun admin tidak dapat dihapus.</b>", "warn")
        non_admin = users[users["username"] != "admin"]["username"].tolist()
        if not non_admin:
            abox("Tidak ada pengguna yang dapat dihapus.", "info")
        else:
            pilih_hapus = st.selectbox("Pilih Pengguna yang akan Dihapus", non_admin, key="sel_hapus_user")
            row_hapus = users[users["username"]==pilih_hapus].iloc[0]
            abox(f"<b>Username:</b> {row_hapus['username']}<br>"
                 f"<b>Nama:</b> {row_hapus['nama']}<br>"
                 f"<b>Role:</b> {row_hapus['role']} &nbsp;|&nbsp; <b>Wilayah:</b> {row_hapus['wilayah']}", "warn")

            konfirm_key = f"konfirm_hapus_user_{pilih_hapus}"
            if not st.session_state.get(konfirm_key):
                if st.button(f"🗑️ Hapus '{pilih_hapus}'", type="primary", use_container_width=True, key="btn_hapus_user"):
                    st.session_state[konfirm_key] = True
                    st.rerun()
            else:
                abox(f"⚠️ <b>Yakin hapus pengguna '{pilih_hapus}'?</b> Tindakan ini permanen!", "red")
                cc, cd = st.columns(2)
                with cc:
                    if st.button("✅ Ya, Hapus", type="primary", use_container_width=True, key="btn_konfirm_hapus_user"):
                        users_baru = users[users["username"] != pilih_hapus].reset_index(drop=True)
                        with st.spinner("Menghapus pengguna..."):
                            ok, msg = save_users(users_baru)
                        st.session_state[konfirm_key] = False
                        if ok:
                            st.success(f"✅ Pengguna '{pilih_hapus}' berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error(f"❌ Gagal hapus: {msg}")
                with cd:
                    if st.button("❌ Batal", use_container_width=True, key="btn_batal_hapus_user"):
                        st.session_state[konfirm_key] = False
                        st.rerun()

    with t4:
        abox("Gunakan fitur ini untuk mereset password pengguna yang lupa password.")
        with st.form("freset", clear_on_submit=True):
            pilih   = st.selectbox("Pilih Pengguna *", users["username"].tolist())
            pw_baru = st.text_input("Password Baru *", type="password")
            if st.form_submit_button("🔑 Reset Password", type="primary"):
                if not pw_baru:
                    st.error("❌ Password baru tidak boleh kosong.")
                else:
                    idx = users[users["username"]==pilih].index[0]
                    users.loc[idx,"password"] = hash_pw(pw_baru)
                    with st.spinner("Menyimpan..."):
                        ok, msg = save_users(users)
                    if ok: st.success(f"✅ Password {pilih} berhasil direset!")
                    else:  st.error(f"❌ Gagal: {msg}")
                    st.rerun()

# ─── KELOLA DATA ─────────────────────────────────────────────────────────────────
def page_kelola_data(df, user):
    render_header("Kelola Data")
    role = str(user.get("role","")).lower()

    if role == "admin":
        df_akses = df.copy() if not df.empty else pd.DataFrame()
        abox("<span class='role-badge rb-admin'>ADMIN</span> &nbsp;"
             "Dapat melihat, mengedit, dan <b>menghapus semua data</b> dari seluruh pengguna.")
    else:
        df_akses = df[df["diinput_oleh"]==user["username"]].copy() if not df.empty else pd.DataFrame()
        abox("<span class='role-badge rb-pegawai'>PEGAWAI</span> &nbsp;"
             f"Hanya dapat mengelola data yang diinput oleh <b>{user['username']}</b>.")

    if role == "admin":
        t1, t2, t3 = st.tabs(["✏️ Edit Data","🗑️ Hapus Data","🛠️ Hapus Paksa (Admin)"])
    else:
        t1, t2 = st.tabs(["✏️ Edit Data","🗑️ Hapus Data"])
        t3 = None

    with t1:
        if df_akses.empty:
            abox("Belum ada data yang dapat diedit.", "warn")
        else:
            tahun_opts = sorted(df_akses["tahun"].dropna().astype(str).unique().tolist())
            c1, c2, c3 = st.columns(3)
            with c1: te = st.selectbox("Tahun", tahun_opts, key="edit_tahun")
            with c2:
                bl_opts = [b for b in BULAN_LIST if b in df_akses[df_akses["tahun"].astype(str)==te]["bulan"].values]
                be = st.selectbox("Bulan", bl_opts or ["—"], key="edit_bulan")
            with c3:
                ps_opts = df_akses[(df_akses["tahun"].astype(str)==te)&(df_akses["bulan"]==be)]["posyandu"].unique().tolist()
                pe = st.selectbox("Posyandu", ps_opts or ["—"], key="edit_pos")

            if pe and pe != "—":
                idx = df[(df["tahun"].astype(str)==te)&(df["bulan"]==be)&(df["posyandu"]==pe)].index
                if len(idx) > 0:
                    i = idx[0]
                    abox(f"<b>{pe}</b> — {be} {te} &nbsp;|&nbsp; Wilayah: {df.loc[i,'wilayah']} &nbsp;|&nbsp; Diinput: <b>{df.loc[i,'diinput_oleh']}</b>")
                    with st.form("fed"):
                        e1, e2, e3 = st.columns(3)
                        with e1: ns  = st.number_input("Sasaran",  value=int(df.loc[i,"sasaran"]),  min_value=0)
                        with e2: nh  = st.number_input("Hadir",    value=int(df.loc[i,"hadir"]),    min_value=0)
                        with e3: nst = st.number_input("Stunting", value=int(df.loc[i,"stunting"]), min_value=0)
                        if st.form_submit_button("💾 Simpan Perubahan", type="primary"):
                            if nh > ns: st.error("❌ Hadir tidak boleh melebihi sasaran.")
                            elif nst > nh: st.error("❌ Stunting tidak boleh melebihi hadir.")
                            else:
                                load_data.clear()
                                df_f = load_data()
                                idx2 = df_f[(df_f["tahun"].astype(str)==te)&(df_f["bulan"]==be)&(df_f["posyandu"]==pe)].index
                                if len(idx2) > 0:
                                    df_f.loc[idx2[0],["sasaran","hadir","stunting"]] = [ns,nh,nst]
                                    df_f.loc[idx2[0],"waktu_input"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    ok, msg = save_data(df_f)
                                    if ok: st.success("✅ Data berhasil diperbarui!")
                                    else:  st.error(f"❌ Gagal: {msg}")
                                st.rerun()

    with t2:
        if df_akses.empty:
            abox("Belum ada data yang dapat dihapus.", "warn")
        else:
            tahun_opts2 = sorted(df_akses["tahun"].dropna().astype(str).unique().tolist())
            c1, c2, c3 = st.columns(3)
            with c1: td = st.selectbox("Tahun", tahun_opts2, key="del_tahun")
            with c2:
                bl_opts2 = [b for b in BULAN_LIST if b in df_akses[df_akses["tahun"].astype(str)==td]["bulan"].values]
                bd = st.selectbox("Bulan", bl_opts2 or ["—"], key="del_bulan")
            with c3:
                ps_opts2 = df_akses[(df_akses["tahun"].astype(str)==td)&(df_akses["bulan"]==bd)]["posyandu"].unique().tolist()
                pd_sel = st.selectbox("Posyandu", ps_opts2 or ["—"], key="del_pos")

            if pd_sel and pd_sel != "—":
                row = df_akses[(df_akses["tahun"].astype(str)==td)&(df_akses["bulan"]==bd)&(df_akses["posyandu"]==pd_sel)]
                if not row.empty:
                    r = row.iloc[0]
                    abox(f"<b>Data yang dipilih:</b><br>"
                         f"📍 {r['posyandu']} — {r['bulan']} {r['tahun']}<br>"
                         f"👥 Sasaran: <b>{r['sasaran']}</b> | Hadir: <b>{r['hadir']}</b> | Stunting: <b>{r['stunting']}</b><br>"
                         f"🔑 Diinput oleh: <b>{r['diinput_oleh']}</b>", "warn")

                hapus_key = f"{td}|{bd}|{pd_sel}"
                if not st.session_state.get("hapus_konfirm"):
                    if st.button("🗑️ Hapus Data Ini", type="primary", key="btn_hapus"):
                        st.session_state.hapus_target  = hapus_key
                        st.session_state.hapus_konfirm = True
                        st.rerun()

                if (st.session_state.get("hapus_konfirm") and
                        st.session_state.get("hapus_target") == hapus_key):
                    abox("⚠️ <b>Konfirmasi Hapus</b> — Tindakan ini tidak dapat dibatalkan!", "red")
                    cc, cd = st.columns(2)
                    with cc:
                        if st.button("✅ Ya, Hapus Permanen", type="primary", key="btn_konfirm_hapus"):
                            load_data.clear()
                            df_f = load_data()
                            df_f = df_f[~(
                                (df_f["tahun"].astype(str)==td) &
                                (df_f["bulan"]==bd) &
                                (df_f["posyandu"]==pd_sel)
                            )].reset_index(drop=True)
                            ok, msg = save_data(df_f)
                            st.session_state.hapus_konfirm = False
                            st.session_state.hapus_target  = None
                            if ok: st.success("✅ Data berhasil dihapus!")
                            else:  st.error(f"❌ Gagal menghapus: {msg}")
                            st.rerun()
                    with cd:
                        if st.button("❌ Batal", key="btn_batal_hapus"):
                            st.session_state.hapus_konfirm = False
                            st.session_state.hapus_target  = None
                            st.rerun()

    if role == "admin" and t3 is not None:
        with t3:
            abox("🛠️ <b>Mode Admin — Hapus Paksa</b><br>"
                 "Gunakan ini untuk menghapus data yang tidak muncul di filter biasa.", "red")
            load_data.clear()
            df_all = load_data()
            if df_all.empty:
                abox("Tidak ada data sama sekali.", "warn")
            else:
                df_display = df_all.reset_index(drop=True).copy()
                df_display.insert(0, "No", range(1, len(df_display)+1))
                sec(f"Semua Data ({len(df_display)} baris)")
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                c_inp, c_btn = st.columns([2,1])
                with c_inp:
                    no_hapus = st.number_input("Nomor Baris (kolom No)", min_value=1,
                                               max_value=len(df_display), step=1, key="no_hapus_paksa")
                with c_btn:
                    st.markdown("<div style='margin-top:1.6rem;'></div>", unsafe_allow_html=True)
                    preview_btn = st.button("🔍 Preview", key="preview_hapus", use_container_width=True)

                if preview_btn or st.session_state.get("hapus_paksa_preview"):
                    st.session_state["hapus_paksa_preview"] = True
                    idx_real = no_hapus - 1
                    if 0 <= idx_real < len(df_all):
                        r = df_all.iloc[idx_real]
                        abox(f"<b>Baris No. {no_hapus}:</b><br>"
                             f"📍 {r.get('posyandu','—')} — {r.get('bulan','—')} {r.get('tahun','—')}<br>"
                             f"👥 Sasaran: <b>{r.get('sasaran','—')}</b> | Hadir: <b>{r.get('hadir','—')}</b> | Stunting: <b>{r.get('stunting','—')}</b><br>"
                             f"🔑 Diinput: <b>{r.get('diinput_oleh','—')}</b>", "red")
                        cc, cd = st.columns(2)
                        with cc:
                            if st.button("🗑️ HAPUS BARIS INI", type="primary", key="btn_hapus_paksa", use_container_width=True):
                                df_baru = df_all.drop(index=idx_real).reset_index(drop=True)
                                ok, msg = save_data(df_baru)
                                st.session_state["hapus_paksa_preview"] = False
                                if ok: st.success(f"✅ Baris No.{no_hapus} berhasil dihapus!")
                                else:  st.error(f"❌ Gagal: {msg}")
                                st.rerun()
                        with cd:
                            if st.button("❌ Batal", key="btn_batal_paksa", use_container_width=True):
                                st.session_state["hapus_paksa_preview"] = False
                                st.rerun()
    return df

# ─── TEST KONEKSI ─────────────────────────────────────────────────────────────────
def page_test():
    render_header("Diagnostik & Test Koneksi")

    sec("Baca Google Sheets Real-time")
    if st.button("📥 Baca Isi Google Sheets Sekarang", type="primary", use_container_width=True):
        ws, err = get_ws("data_stunting")
        if ws:
            try:
                vals = ws.get_all_values()
                n = len(vals) - 1
                abox(f"✅ Google Sheets berisi <b>{n}</b> baris data.", "green")
                if n > 0:
                    df_raw = pd.DataFrame(vals[1:], columns=vals[0])
                    st.dataframe(df_raw, use_container_width=True, hide_index=True)
            except Exception as e:
                abox(f"❌ Gagal baca: {e}", "red")
        else:
            abox(f"❌ Tidak bisa konek: {err}", "red")

    st.markdown("---")
    sec("Hapus Darurat — Kosongkan Semua Data")
    abox("⚠️ Akan menghapus <b>SEMUA</b> baris data stunting dan menyisakan header saja.", "red")

    if "konfirm_kosongkan" not in st.session_state:
        st.session_state.konfirm_kosongkan = False

    if not st.session_state.get("konfirm_kosongkan"):
        if st.button("🧹 Kosongkan Semua Data Stunting", use_container_width=True):
            st.session_state.konfirm_kosongkan = True
            st.rerun()
    else:
        abox("⚠️ <b>PERINGATAN</b> — Semua data DIHAPUS PERMANEN!", "red")
        cc, cd = st.columns(2)
        with cc:
            if st.button("✅ Ya, Kosongkan", type="primary", use_container_width=True):
                ws, err = get_ws("data_stunting")
                if ws:
                    try:
                        import time
                        HEADER = ["tahun","bulan","bulan_ke","wilayah","posyandu",
                                  "sasaran","hadir","stunting","diinput_oleh","waktu_input"]
                        ws.clear(); time.sleep(0.8)
                        ws.update([HEADER])
                        load_data.clear()
                        st.session_state.konfirm_kosongkan = False
                        abox("✅ Sheet berhasil dikosongkan.", "green")
                        st.rerun()
                    except Exception as e:
                        abox(f"❌ Gagal: {e}", "red")
                else:
                    abox(f"❌ Tidak bisa konek: {err}", "red")
        with cd:
            if st.button("❌ Batal", use_container_width=True):
                st.session_state.konfirm_kosongkan = False
                st.rerun()

    st.markdown("---")
    sec("Diagnostik Koneksi")
    try:
        sn = st.secrets["sheet_name"]
        abox(f"✅ sheet_name: <code>{sn}</code>", "green")
    except Exception as e:
        abox(f"❌ Gagal baca sheet_name: {e}", "red")
    try:
        gcp = st.secrets["gcp_service_account"]
        abox(f"✅ gcp_service_account OK. Email: <code>{gcp.get('client_email','-')}</code>", "green")
    except Exception as e:
        abox(f"❌ Gagal baca gcp: {e}", "red")

    gc, err = get_gc()
    if gc:
        abox("✅ Koneksi Google berhasil!", "green")
        try:
            sh   = gc.open(st.secrets["sheet_name"])
            tabs = [w.title for w in sh.worksheets()]
            abox(f"✅ Spreadsheet: <b>{sh.title}</b> | Tab: {tabs}", "green")
        except Exception as e:
            abox(f"❌ Gagal buka spreadsheet: {e}", "red")
    else:
        abox(f"❌ Koneksi GAGAL: {err}", "red")

# ─── MAIN ─────────────────────────────────────────────────────────────────────────
def main():
    df = load_data()

    if st.session_state.is_public:
        menu, tahun, bulan = render_sidebar("publik")
        if menu == "📈 Analisis & Tren":
            page_analisis(df, tahun)
        else:
            page_dashboard(df, tahun, bulan, is_public=True)
        return

    if not st.session_state.logged_in:
        login_page()
        return

    user = st.session_state.user
    role = str(user.get("role","")).lower()
    menu, tahun, bulan = render_sidebar(role)

    if   menu == "📊 Dashboard Utama":  page_dashboard(df, tahun, bulan)
    elif menu == "📋 Input Data":        df = page_input(df, user)
    elif menu == "📤 Import CSV":         df = page_import(df)
    elif menu == "📈 Analisis & Tren":   page_analisis(df, tahun)
    elif menu == "📄 Laporan":           page_laporan(df, tahun, bulan)
    elif menu == "👥 Kelola Pengguna":
        if role == "admin": page_kelola_user()
        else: st.error("❌ Akses ditolak.")
    elif menu == "⚙️ Kelola Data":       df = page_kelola_data(df, user)
    elif menu == "🔧 Test Koneksi":
        if role == "admin": page_test()
        else: st.error("❌ Akses ditolak.")

if __name__ == "__main__":
    main()
