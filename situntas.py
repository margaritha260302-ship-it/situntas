import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, io, hashlib, base64, json
from datetime import datetime

st.set_page_config(
    page_title="SITUNTAS — Kecamatan Kota SoE",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

WILAYAH = {
    "Kelurahan Kota SoE": ["Posyandu Mawar I", "Posyandu Mawar II", "Posyandu Mawar III"],
    "Kelurahan Karang Siri": ["Posyandu Melati I", "Posyandu Melati II", "Posyandu Melati III"],
    "Kelurahan Benpasi": ["Posyandu Anggrek I", "Posyandu Anggrek II", "Posyandu Anggrek III"],
    "Kelurahan Nonohonis": ["Posyandu Kenanga I", "Posyandu Kenanga II", "Posyandu Kenanga III"],
    "Kelurahan Baumata Barat": ["Posyandu Dahlia I", "Posyandu Dahlia II", "Posyandu Dahlia III"],
    "Kelurahan Soe": ["Posyandu Bougenville I", "Posyandu Bougenville II", "Posyandu Bougenville III"],
    "Kelurahan Kesetnana": ["Posyandu Flamboyan I", "Posyandu Flamboyan II", "Posyandu Flamboyan III"],
    "Kelurahan Noemuti": ["Posyandu Cempaka I", "Posyandu Cempaka II", "Posyandu Cempaka III"],
    "Kelurahan Oelami": ["Posyandu Tulip I", "Posyandu Tulip II", "Posyandu Tulip III"],
    "Kelurahan Karang Anyar": ["Posyandu Aster I", "Posyandu Aster II", "Posyandu Aster III"],
    "Kelurahan Nunmafo": ["Posyandu Seruni I", "Posyandu Seruni II", "Posyandu Seruni III"],
    "Desa Oelbubuk": ["Posyandu Nusa I", "Posyandu Nusa II", "Posyandu Nusa III"],
    "Desa Nulle": ["Posyandu Indah I", "Posyandu Indah II", "Posyandu Indah III"],
}
BULAN_LIST = ["Januari","Februari","Maret","April","Mei","Juni",
              "Juli","Agustus","September","Oktober","November","Desember"]
TAHUN_LIST = [2024, 2025, 2026, 2027]
LOGO_PATH = "logo_situntas.png"

def get_bulan_ke(b): return BULAN_LIST.index(b) + 1
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

# ─── GOOGLE SHEETS CONNECTION ──────────────────────────────────────────────────
def get_gsheet_client():
    """Tidak pakai cache supaya koneksi selalu fresh"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client, None
    except Exception as e:
        return None, str(e)

def get_sheet(name):
    try:
        gc, err = get_gsheet_client()
        if gc is None:
            return None, "Gagal konek: " + str(err)
        sheet_name = st.secrets["sheet_name"]
        sh = gc.open(sheet_name)
        ws = sh.worksheet(name)
        return ws, None
    except Exception as e:
        return None, str(e)

# ─── DATA FUNCTIONS ────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    ws, err = get_sheet("data_stunting")
    if ws:
        try:
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                if "bulan_ke" not in df.columns:
                    df["bulan_ke"] = df["bulan"].apply(lambda x: get_bulan_ke(x) if x in BULAN_LIST else 0)
                return df
        except: pass
    if os.path.exists("data_situntas.csv"):
        return pd.read_csv("data_situntas.csv")
    return pd.DataFrame(columns=["tahun","bulan","bulan_ke","wilayah","posyandu",
                                  "sasaran","hadir","stunting","diinput_oleh","waktu_input"])

def save_data(df):
    load_data.clear()
    ws, err = get_sheet("data_stunting")
    if ws:
        try:
            all_data = [df.columns.tolist()] + df.astype(str).values.tolist()
            ws.clear()
            ws.update(all_data)
            return True, "OK"
        except Exception as e:
            return False, str(e)
    return False, "Tidak bisa konek: " + str(err)

@st.cache_data(ttl=30)
def load_users():
    ws, err = get_sheet("users")
    if ws:
        try:
            records = ws.get_all_records()
            if records: return pd.DataFrame(records)
        except: pass
    if os.path.exists("users_situntas.csv"):
        return pd.read_csv("users_situntas.csv")
    df = pd.DataFrame([
        {"username":"admin","password":hash_pw("situntas2025"),"nama":"Administrator","role":"admin","wilayah":"semua","aktif":True},
    ])
    save_users(df)
    return df

def save_users(df):
    load_users.clear()
    ws, err = get_sheet("users")
    if ws:
        try:
            ws.clear()
            ws.update([df.columns.tolist()] + df.astype(str).values.tolist())
            return True, "OK"
        except Exception as e:
            return False, str(e)
    return False, str(err)

def verify_user(username, password):
    users = load_users()
    # aktif bisa berupa bool True atau string "TRUE" / "True" dari Google Sheets
    users["_aktif"] = users["aktif"].astype(str).str.upper().isin(["TRUE","1","YES"])
    user = users[(users["username"]==username) & (users["_aktif"]==True)]
    if user.empty: return None
    if str(user.iloc[0]["password"]) == hash_pw(password):
        return user.iloc[0].to_dict()
    return None

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Nunito:wght@700;800;900&display=swap');
* { font-family: 'Plus Jakarta Sans', sans-serif; }
.stApp { background: linear-gradient(160deg, #E8F4FD 0%, #C8E6FA 40%, #D6EEFB 70%, #EBF5FD 100%); min-height:100vh; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1565C0 0%, #1976D2 50%, #1E88E5 100%) !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio label { background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12); border-radius:10px; padding:10px 14px; margin:3px 0; display:block; }
[data-testid="stSidebar"] .stRadio label:hover { background:rgba(255,255,255,0.18); }
.situntas-header { background:linear-gradient(135deg,#1565C0,#1976D2,#42A5F5); border-radius:20px; padding:1.8rem 2.5rem; margin-bottom:1.5rem; display:flex; align-items:center; gap:1.5rem; box-shadow:0 8px 32px rgba(21,101,192,0.25); }
.header-badge { display:inline-block; background:rgba(255,255,255,0.2); border:1px solid rgba(255,255,255,0.35); color:#FFFFFF; font-size:0.7rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:3px 12px; border-radius:20px; margin-bottom:0.7rem; }
.header-title { font-family:'Nunito',sans-serif; font-size:2rem; font-weight:900; color:#FFFFFF; margin:0; line-height:1.2; }
.header-sub { color:rgba(255,255,255,0.85); font-size:0.88rem; margin:0.3rem 0 0; }
.metric-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:1.5rem; }
.metric-card { background:#FFFFFF; border-radius:16px; padding:1.3rem 1.5rem; position:relative; overflow:hidden; transition:transform 0.2s,box-shadow 0.2s; box-shadow:0 4px 16px rgba(21,101,192,0.1); }
.metric-card:hover { transform:translateY(-3px); box-shadow:0 8px 28px rgba(21,101,192,0.18); }
.metric-card::after { content:''; position:absolute; top:0; left:0; right:0; height:4px; border-radius:16px 16px 0 0; }
.mc-red::after { background:linear-gradient(90deg,#EF5350,#E53935); }
.mc-blue::after { background:linear-gradient(90deg,#42A5F5,#1976D2); }
.mc-green::after { background:linear-gradient(90deg,#66BB6A,#43A047); }
.mc-yellow::after { background:linear-gradient(90deg,#FFA726,#FB8C00); }
.metric-icon { font-size:1.6rem; margin-bottom:0.5rem; }
.metric-label { font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#90A4AE; margin-bottom:0.3rem; }
.metric-value { font-size:2.2rem; font-weight:800; line-height:1; color:#1A237E; }
.metric-sub { font-size:0.78rem; color:#90A4AE; margin-top:0.3rem; }
.metric-delta-up { color:#E53935; font-size:0.78rem; font-weight:700; }
.metric-delta-down { color:#43A047; font-size:0.78rem; font-weight:700; }
.section-title { color:#1565C0; font-size:1rem; font-weight:700; margin:1.5rem 0 0.8rem; padding-bottom:0.5rem; border-bottom:2px solid rgba(21,101,192,0.15); display:flex; align-items:center; gap:8px; }
.alert-box { background:rgba(21,101,192,0.07); border:1px solid rgba(21,101,192,0.2); border-left:4px solid #1976D2; border-radius:10px; padding:0.9rem 1.2rem; color:#1565C0; font-size:0.87rem; margin-bottom:1rem; }
.alert-warning { background:rgba(255,152,0,0.07); border-color:rgba(255,152,0,0.25); border-left-color:#FB8C00; color:#E65100; }
.chart-container { background:#FFFFFF; border-radius:16px; padding:1.2rem; margin-bottom:1rem; box-shadow:0 4px 16px rgba(21,101,192,0.08); }
.public-banner { background:linear-gradient(135deg,#E8F5E9,#C8E6C9); border:1px solid #A5D6A7; border-left:4px solid #43A047; border-radius:12px; padding:0.8rem 1.2rem; color:#2E7D32; font-size:0.85rem; font-weight:600; margin-bottom:1.2rem; }
.stButton > button { background:linear-gradient(135deg,#1976D2,#1565C0) !important; border:none !important; border-radius:10px !important; color:white !important; font-weight:600 !important; box-shadow:0 4px 12px rgba(21,101,192,0.3) !important; }
.stButton > button:hover { background:linear-gradient(135deg,#1E88E5,#1976D2) !important; transform:translateY(-1px) !important; }
.stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div { background:#FFFFFF !important; border:1.5px solid #BBDEFB !important; border-radius:10px !important; }
.sidebar-title { font-family:'Nunito',sans-serif; font-size:1.4rem; font-weight:900; color:#FFFFFF !important; letter-spacing:1px; }
.sidebar-sub { font-size:0.68rem; color:rgba(255,255,255,0.65) !important; letter-spacing:1px; text-transform:uppercase; }
label { color:#1565C0 !important; font-size:0.85rem !important; font-weight:600 !important; }
p, div { color:#1A237E; }
h1,h2,h3 { color:#1565C0 !important; }
.stTabs [data-baseweb="tab-list"] { background:rgba(255,255,255,0.6); border-radius:10px; padding:4px; }
.stTabs [data-baseweb="tab"] { border-radius:8px; color:#1565C0 !important; font-weight:600; }
.stTabs [aria-selected="true"] { background:#1976D2 !important; color:white !important; }
</style>
""", unsafe_allow_html=True)

PLOT_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(227,242,253,0.4)',
    font=dict(color='#1A237E', family='Plus Jakarta Sans', size=12),
    xaxis=dict(gridcolor='rgba(21,101,192,0.08)', linecolor='rgba(21,101,192,0.15)', tickfont=dict(color='#1565C0')),
    yaxis=dict(gridcolor='rgba(21,101,192,0.08)', linecolor='rgba(21,101,192,0.15)', tickfont=dict(color='#1565C0')),
    margin=dict(l=20,r=20,t=40,b=20),
    hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='rgba(21,101,192,0.3)', font=dict(color='#1A237E')),
    legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor='rgba(21,101,192,0.2)', borderwidth=1, font=dict(color='#1A237E')),
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.is_public = False

def get_logo_b64():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def render_header(subtitle=""):
    logo_b64 = get_logo_b64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:80px;height:80px;object-fit:contain;border-radius:12px;background:white;padding:6px;flex-shrink:0;">' if logo_b64 else '<div style="font-size:3rem;">&#x1F3E5;</div>'
    subtitle_html = f'<br><span style="color:rgba(255,255,255,0.85);font-size:0.82rem;font-style:italic;">{subtitle}</span>' if subtitle else ""
    st.markdown(f"""
    <div class="situntas-header">
        {logo_html}
        <div>
            <div class="header-badge">Sistem Informasi Digital</div>
            <div class="header-title">SITUNTAS</div>
            <div class="header-sub">Sistem Informasi Terpadu Monitoring Angka Stunting Secara Realtime<br>
            Kecamatan Kota SoE — Kabupaten Timor Tengah Selatan{subtitle_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def login_page():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        logo_b64 = get_logo_b64()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:130px;height:130px;object-fit:contain;border-radius:16px;box-shadow:0 4px 16px rgba(21,101,192,0.2);">' if logo_b64 else '<div style="font-size:4rem;">&#x1F3E5;</div>'
        st.markdown(f"""
        <div style='text-align:center;padding:3rem 0 1rem;'>
            {logo_html}
            <div style='font-family:"Nunito",sans-serif;font-size:2.2rem;font-weight:900;color:#1565C0;letter-spacing:1px;margin-top:1rem;'>SITUNTAS</div>
            <div style='font-size:0.78rem;color:#1976D2;letter-spacing:1.5px;text-transform:uppercase;margin-top:4px;font-weight:600;'>Sistem Informasi Terpadu Monitoring Stunting</div>
            <div style='font-size:0.82rem;color:#42A5F5;margin-top:6px;'>Kecamatan Kota SoE &middot; Kab. Timor Tengah Selatan</div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            col_a, col_b = st.columns(2)
            with col_a:
                login_btn = st.form_submit_button("MASUK", use_container_width=True, type="primary")
            with col_b:
                publik_btn = st.form_submit_button("Dashboard Publik", use_container_width=True)
            if login_btn:
                user = verify_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.is_public = False
                    st.rerun()
                else:
                    st.error("Username atau password salah.")
            if publik_btn:
                st.session_state.is_public = True
                st.rerun()
        st.markdown("<div style='text-align:center;font-size:0.75rem;color:#90A4AE;margin-top:1rem;padding-bottom:2rem;'>2026 Kecamatan Kota SoE &middot; Dikembangkan oleh Margaritha Liufeto, S.H</div>", unsafe_allow_html=True)

def render_sidebar(role="publik"):
    with st.sidebar:
        logo_b64 = get_logo_b64()
        if logo_b64:
            st.markdown(f"""
            <div style='text-align:center;padding:1.2rem 0 0.8rem;'>
                <img src="data:image/png;base64,{logo_b64}" style="width:90px;height:90px;object-fit:contain;border-radius:14px;background:white;padding:6px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">
                <div class='sidebar-title' style='margin-top:0.6rem;'>SITUNTAS</div>
                <div class='sidebar-sub'>Kecamatan Kota SoE</div>
            </div>
            <hr style='border-color:rgba(255,255,255,0.15);margin:0 0 1rem;'>
            """, unsafe_allow_html=True)

        if role == "publik":
            menu = "Dashboard Publik"
            st.markdown("<div style='padding:0.5rem 1rem;background:rgba(255,255,255,0.15);border-radius:8px;margin-bottom:1rem;'><span style='color:#FFFFFF;font-size:0.8rem;'>Mode Publik</span></div>", unsafe_allow_html=True)
            if st.button("Login sebagai Pegawai", use_container_width=True):
                st.session_state.is_public = False
                st.session_state.logged_in = False
                st.rerun()
        else:
            menu_opts = ["Dashboard Utama"]
            if role in ["pegawai","admin"]:
                menu_opts += ["Input Data", "Import Google Sheets"]
            if role == "admin":
                menu_opts += ["Analisis & Tren", "Laporan", "Kelola Pengguna", "Kelola Data"]
            menu = st.radio("Navigasi", menu_opts, label_visibility="collapsed")

        st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:1rem 0;'>", unsafe_allow_html=True)
        st.markdown("**Filter Periode**")
        tahun = st.selectbox("Tahun", TAHUN_LIST, index=TAHUN_LIST.index(datetime.now().year) if datetime.now().year in TAHUN_LIST else 2)
        bulan = st.selectbox("Bulan", BULAN_LIST, index=datetime.now().month-1)

        if role != "publik":
            st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:1rem 0;'>", unsafe_allow_html=True)
            user = st.session_state.user
            wilayah_info = "Akses semua wilayah." if user["role"] == "admin" else ("Wilayah: " + str(user["wilayah"]))
            st.markdown(
                "<div style='font-size:0.78rem;color:rgba(255,255,255,0.7);'>Login sebagai:<br>"
                "<span style='color:#FFFFFF;font-weight:700;'>" + str(user["nama"]) + "</span><br>"
                "<span style='font-size:0.7rem;background:rgba(255,255,255,0.15);padding:2px 8px;border-radius:10px;'>"
                + str(user["role"]).upper() + "</span><br>"
                "<span style='font-size:0.7rem;color:rgba(255,255,255,0.6);'>" + wilayah_info + "</span></div>",
                unsafe_allow_html=True
            )
            st.markdown("<div style='margin:0.5rem 0;'></div>", unsafe_allow_html=True)
            if st.button("Keluar", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.rerun()
    return menu, tahun, bulan

# ─── TEST KONEKSI (halaman debug) ──────────────────────────────────────────────
def page_test_koneksi():
    render_header("Test Koneksi Google Sheets")
    st.markdown("### Diagnostik Koneksi")

    # Test 1: secrets
    st.markdown("**1. Cek Secrets**")
    try:
        sn = st.secrets["sheet_name"]
        st.success("sheet_name = " + sn)
    except Exception as e:
        st.error("GAGAL baca sheet_name: " + str(e))

    try:
        gcp = st.secrets["gcp_service_account"]
        st.success("gcp_service_account ditemukan, client_email = " + str(gcp.get("client_email","-")))
    except Exception as e:
        st.error("GAGAL baca gcp_service_account: " + str(e))

    # Test 2: koneksi gspread
    st.markdown("**2. Cek Koneksi gspread**")
    gc, err = get_gsheet_client()
    if gc:
        st.success("Koneksi gspread berhasil!")
    else:
        st.error("Koneksi GAGAL: " + str(err))
        return

    # Test 3: buka spreadsheet
    st.markdown("**3. Cek Buka Spreadsheet**")
    try:
        sh = gc.open(st.secrets["sheet_name"])
        st.success("Spreadsheet ditemukan: " + sh.title)
        worksheets = [ws.title for ws in sh.worksheets()]
        st.info("Sheet yang ada: " + str(worksheets))
    except Exception as e:
        st.error("GAGAL buka spreadsheet: " + str(e))
        return

    # Test 4: buka sheet data_stunting
    st.markdown("**4. Cek Sheet data_stunting**")
    ws, err = get_sheet("data_stunting")
    if ws:
        st.success("Sheet data_stunting berhasil dibuka!")
        try:
            vals = ws.get_all_values()
            st.info("Baris di sheet: " + str(len(vals)) + " baris. Header: " + str(vals[0] if vals else "kosong"))
        except Exception as e:
            st.error("Gagal baca: " + str(e))
    else:
        st.error("GAGAL buka data_stunting: " + str(err))

    # Test 5: tulis data test
    st.markdown("**5. Test Tulis Data**")
    if st.button("Klik untuk Test Simpan 1 Baris Data", type="primary"):
        ws, err = get_sheet("data_stunting")
        if ws:
            try:
                test_row = ["TEST", "Mei", "5", "Kelurahan Test", "Posyandu Test",
                            "10", "8", "1", "admin", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                ws.append_row(test_row)
                st.success("BERHASIL tulis data test! Cek Google Sheets sekarang.")
            except Exception as e:
                st.error("GAGAL tulis: " + str(e))
        else:
            st.error("Tidak bisa buka sheet: " + str(err))

    st.markdown("**6. Hapus Data Test**")
    if st.button("Hapus baris TEST dari Sheets"):
        ws, err = get_sheet("data_stunting")
        if ws:
            try:
                vals = ws.get_all_values()
                for i, row in enumerate(vals):
                    if row and row[0] == "TEST":
                        ws.delete_rows(i+1)
                        st.success("Baris TEST berhasil dihapus.")
                        break
            except Exception as e:
                st.error("Gagal hapus: " + str(e))

# ─── DASHBOARD ──────────────────────────────────────────────────────────────────
def page_dashboard(df, tahun, bulan, is_public=False):
    render_header()
    if is_public:
        st.markdown("<div class='public-banner'><strong>Dashboard Publik</strong> — Login diperlukan untuk fitur lainnya.</div>", unsafe_allow_html=True)

    bulan_ke = get_bulan_ke(bulan)
    df_bulan = df[(df["tahun"]==tahun) & (df["bulan"]==bulan)] if not df.empty else pd.DataFrame()
    bulan_lalu = BULAN_LIST[bulan_ke-2] if bulan_ke > 1 else None
    df_lalu = df[(df["tahun"]==tahun) & (df["bulan"]==bulan_lalu)] if (bulan_lalu and not df.empty) else pd.DataFrame()

    total_stunting = int(df_bulan["stunting"].sum()) if not df_bulan.empty else 0
    total_hadir = int(df_bulan["hadir"].sum()) if not df_bulan.empty else 0
    total_sasaran = int(df_bulan["sasaran"].sum()) if not df_bulan.empty else 0
    wilayah_lapor = df_bulan["wilayah"].nunique() if not df_bulan.empty else 0
    posyandu_aktif = df_bulan["posyandu"].nunique() if not df_bulan.empty else 0
    pct_hadir = round(total_hadir/total_sasaran*100,1) if total_sasaran > 0 else 0
    stunting_lalu = int(df_lalu["stunting"].sum()) if not df_lalu.empty else None

    def delta(now, prev):
        if prev is None: return ""
        d = now - prev
        if d > 0: return '<span class="metric-delta-up">+' + str(d) + ' dari bln lalu</span>'
        elif d < 0: return '<span class="metric-delta-down">' + str(d) + ' dari bln lalu</span>'
        return '<span style="color:#90A4AE;font-size:0.78rem;">sama bln lalu</span>'

    st.markdown("<div class='section-title'><span>|</span> Ringkasan Bulan " + bulan + " " + str(tahun) + "</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='metric-grid'>"
        "<div class='metric-card mc-red'><div class='metric-icon'>&#x1F534;</div><div class='metric-label'>Total Kasus Stunting</div><div class='metric-value'>" + str(total_stunting) + "</div><div class='metric-sub'>" + delta(total_stunting, stunting_lalu) + "</div></div>"
        "<div class='metric-card mc-blue'><div class='metric-icon'>&#x1F476;</div><div class='metric-label'>Kehadiran Posyandu</div><div class='metric-value'>" + str(total_hadir) + "</div><div class='metric-sub'><span style='color:#1976D2;'>" + str(pct_hadir) + "%</span> dari " + str(total_sasaran) + " sasaran</div></div>"
        "<div class='metric-card mc-green'><div class='metric-icon'>&#x1F3D8;</div><div class='metric-label'>Wilayah Melapor</div><div class='metric-value'>" + str(wilayah_lapor) + "</div><div class='metric-sub'>dari 13 Kel/Desa</div></div>"
        "<div class='metric-card mc-yellow'><div class='metric-icon'>&#x1F3E5;</div><div class='metric-label'>Posyandu Aktif</div><div class='metric-value'>" + str(posyandu_aktif) + "</div><div class='metric-sub'>dari 33 posyandu</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

    if df_bulan.empty:
        st.markdown("<div class='alert-box alert-warning'>Belum ada data untuk bulan <strong>" + bulan + " " + str(tahun) + "</strong>.</div>", unsafe_allow_html=True)
        return

    df_wil = df_bulan.groupby("wilayah",as_index=False).agg(stunting=("stunting","sum"),hadir=("hadir","sum"),sasaran=("sasaran","sum"))
    if not df_lalu.empty:
        df_wil_lalu = df_lalu.groupby("wilayah",as_index=False).agg(stunting_lalu=("stunting","sum"))
        df_wil = df_wil.merge(df_wil_lalu, on="wilayah", how="left")
        df_wil["trend"] = df_wil.apply(lambda r: "Naik" if r["stunting"]>r.get("stunting_lalu",r["stunting"]) else ("Turun" if r["stunting"]<r.get("stunting_lalu",r["stunting"]) else "Tetap"), axis=1)
    else:
        df_wil["trend"] = "Data Awal"
    df_wil["pct_hadir"] = (df_wil["hadir"]/df_wil["sasaran"]*100).round(1).fillna(0)
    df_wil = df_wil.sort_values("stunting", ascending=True)
    warna_map = {"Naik":"#E53935","Turun":"#43A047","Tetap":"#FB8C00","Data Awal":"#1976D2"}

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig = go.Figure(go.Bar(x=df_wil["stunting"],y=df_wil["wilayah"],orientation="h",
                               marker=dict(color=[warna_map.get(t,"#1976D2") for t in df_wil["trend"]]),
                               text=df_wil["stunting"],textposition="outside",textfont=dict(color="#1A237E",size=12),
                               hovertemplate="<b>%{y}</b><br>Stunting: <b>%{x}</b><extra></extra>"))
        fig.update_layout(title=dict(text="Stunting per Wilayah",font=dict(color="#1A237E",size=14),x=0),height=450,**PLOT_LAYOUT)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_wil["sasaran"],y=df_wil["wilayah"],orientation="h",name="Sasaran",marker_color="rgba(21,101,192,0.15)"))
        fig2.add_trace(go.Bar(x=df_wil["hadir"],y=df_wil["wilayah"],orientation="h",name="Hadir",marker_color="#1976D2",
                              text=[f"{v} ({p}%)" for v,p in zip(df_wil["hadir"],df_wil["pct_hadir"])],
                              textposition="outside",textfont=dict(color="#1A237E",size=11)))
        fig2.update_layout(barmode="overlay",title=dict(text="Sasaran vs Kehadiran",font=dict(color="#1A237E",size=14),x=0),height=450,**PLOT_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'><span>|</span> Tabel Rekapitulasi Wilayah</div>", unsafe_allow_html=True)
    df_tabel = df_wil[["wilayah","sasaran","hadir","pct_hadir","stunting"]].rename(columns={"wilayah":"Wilayah","sasaran":"Sasaran","hadir":"Hadir","pct_hadir":"Cakupan (%)","stunting":"Kasus Stunting"})
    st.dataframe(df_tabel.sort_values("Kasus Stunting",ascending=False), use_container_width=True, hide_index=True)

# ─── INPUT DATA ────────────────────────────────────────────────────────────────
def page_input(df, user):
    render_header("Input Data Bulanan")
    if user["role"] == "admin":
        info_wilayah = "Akses semua wilayah."
    else:
        info_wilayah = "Wilayah: <strong>" + str(user["wilayah"]) + "</strong>"
    st.markdown("<div class='alert-box'>Login sebagai <strong>" + str(user["nama"]) + "</strong>. " + info_wilayah + "</div>", unsafe_allow_html=True)

    wilayah_opts = list(WILAYAH.keys()) if user["role"]=="admin" else [user["wilayah"]]
    with st.form("form_input", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tahun_in = st.selectbox("Tahun *", TAHUN_LIST, index=2)
            bulan_in = st.selectbox("Bulan *", BULAN_LIST, index=datetime.now().month-1)
            wilayah_in = st.selectbox("Kelurahan/Desa *", wilayah_opts)
        with col2:
            posyandu_in = st.selectbox("Posyandu *", WILAYAH.get(wilayah_in,[]))
            sasaran_in = st.number_input("Total Sasaran *", min_value=0, step=1)
            hadir_in = st.number_input("Jumlah Kehadiran *", min_value=0, step=1)
        stunting_in = st.number_input("Jumlah Kasus Stunting *", min_value=0, step=1)
        submitted = st.form_submit_button("SIMPAN DATA", use_container_width=True, type="primary")

    if submitted:
        if sasaran_in == 0:
            st.error("Total sasaran tidak boleh 0.")
        elif hadir_in > sasaran_in:
            st.error("Kehadiran tidak boleh melebihi sasaran.")
        else:
            # Selalu ambil data terbaru dari Sheets sebelum simpan
            load_data.clear()
            df_fresh = load_data()
            cek = df_fresh[(df_fresh["tahun"]==tahun_in)&(df_fresh["bulan"]==bulan_in)&(df_fresh["posyandu"]==posyandu_in)] if not df_fresh.empty else pd.DataFrame()
            if not cek.empty:
                st.warning("Data " + posyandu_in + " — " + bulan_in + " " + str(tahun_in) + " sudah ada.")
            else:
                new_row = {"tahun":tahun_in,"bulan":bulan_in,"bulan_ke":get_bulan_ke(bulan_in),
                           "wilayah":wilayah_in,"posyandu":posyandu_in,"sasaran":sasaran_in,
                           "hadir":hadir_in,"stunting":stunting_in,"diinput_oleh":user["username"],
                           "waktu_input":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                df_fresh = pd.concat([df_fresh, pd.DataFrame([new_row])], ignore_index=True)
                ok, msg = save_data(df_fresh)
                if ok:
                    st.success("Data " + posyandu_in + " — " + bulan_in + " " + str(tahun_in) + " berhasil disimpan!")
                else:
                    st.error("GAGAL simpan ke Google Sheets: " + msg)
                st.rerun()

    st.markdown("<div class='section-title'><span>|</span> Data Terbaru</div>", unsafe_allow_html=True)
    if not df.empty:
        st.dataframe(df.sort_values("waktu_input",ascending=False).head(10), use_container_width=True, hide_index=True)
    return df

# ─── IMPORT ────────────────────────────────────────────────────────────────────
def page_import(df):
    render_header("Import Data dari Google Sheets")
    st.markdown("<div class='alert-box'>Cara Import:<br>1. Buka Google Sheets > File > Download > <strong>CSV</strong><br>2. Upload file di bawah ini > Konfirmasi Import</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload File CSV", type=["csv"])
    if uploaded:
        try:
            df_import = pd.read_csv(uploaded)
            st.dataframe(df_import.head(), use_container_width=True, hide_index=True)
            st.markdown("<div class='alert-box'>Total: <strong>" + str(len(df_import)) + "</strong> baris data.</div>", unsafe_allow_html=True)
            if st.button("Konfirmasi Import", type="primary", use_container_width=True):
                df_import["bulan_ke"] = df_import["bulan"].apply(lambda x: get_bulan_ke(x) if x in BULAN_LIST else 0)
                df_import["diinput_oleh"] = "import"
                df_import["waktu_input"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df = pd.concat([df, df_import], ignore_index=True).drop_duplicates(subset=["tahun","bulan","posyandu"],keep="last")
                ok, msg = save_data(df)
                if ok:
                    st.success(str(len(df_import)) + " data berhasil diimport!")
                else:
                    st.error("Gagal simpan: " + msg)
                st.rerun()
        except Exception as e:
            st.error("Error: " + str(e))
    return df

# ─── ANALISIS ──────────────────────────────────────────────────────────────────
def page_analisis(df, tahun):
    render_header("Analisis & Tren")
    df_tahun = df[df["tahun"]==tahun] if not df.empty else pd.DataFrame()
    if df_tahun.empty:
        st.markdown("<div class='alert-box alert-warning'>Belum ada data untuk tahun " + str(tahun) + ".</div>", unsafe_allow_html=True)
        return
    df_agg = df_tahun.groupby(["bulan_ke","bulan"],as_index=False).agg(stunting=("stunting","sum"),hadir=("hadir","sum"),sasaran=("sasaran","sum")).sort_values("bulan_ke")
    df_agg["pct_hadir"] = (df_agg["hadir"]/df_agg["sasaran"]*100).round(1)
    tab1, tab2 = st.tabs(["Tren Stunting","Tren Kehadiran"])
    with tab1:
        st.markdown("<div class='chart-container'>",unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(x=df_agg["bulan"],y=df_agg["stunting"],mode="lines+markers",line=dict(color="#E53935",width=3),marker=dict(size=10,color="#E53935",line=dict(color="#FFFFFF",width=2)),fill="tozeroy",fillcolor="rgba(229,57,53,0.08)"))
        fig.update_layout(title=dict(text="Tren Stunting " + str(tahun),font=dict(color="#1A237E",size=15),x=0),height=380,**PLOT_LAYOUT)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.markdown("</div>",unsafe_allow_html=True)
        df_wt = df_tahun.groupby(["wilayah","bulan_ke","bulan"],as_index=False).agg(stunting=("stunting","sum")).sort_values("bulan_ke")
        st.markdown("<div class='chart-container'>",unsafe_allow_html=True)
        fig2 = px.line(df_wt,x="bulan",y="stunting",color="wilayah",markers=True,title="Tren per Wilayah " + str(tahun))
        fig2.update_traces(line_width=2,marker_size=7)
        fig2.update_layout(height=420,**PLOT_LAYOUT)
        st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
        st.markdown("</div>",unsafe_allow_html=True)
    with tab2:
        st.markdown("<div class='chart-container'>",unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df_agg["bulan"],y=df_agg["sasaran"],name="Sasaran",marker_color="rgba(21,101,192,0.2)"))
        fig3.add_trace(go.Bar(x=df_agg["bulan"],y=df_agg["hadir"],name="Hadir",marker_color="#1976D2"))
        fig3.update_layout(barmode="overlay",title=dict(text="Kehadiran vs Sasaran " + str(tahun),font=dict(color="#1A237E",size=15),x=0),height=380,**PLOT_LAYOUT)
        st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown("<div class='chart-container'>",unsafe_allow_html=True)
        fig4 = go.Figure(go.Scatter(x=df_agg["bulan"],y=df_agg["pct_hadir"],mode="lines+markers",line=dict(color="#43A047",width=3),marker=dict(size=10,color="#43A047")))
        fig4.add_hline(y=80,line_dash="dash",line_color="#FB8C00",annotation_text="Target 80%",annotation_font_color="#FB8C00")
        fig4.update_layout(title=dict(text="Cakupan Kehadiran (%)",font=dict(color="#1A237E",size=15),x=0),height=380,**PLOT_LAYOUT)
        st.plotly_chart(fig4,use_container_width=True,config={"displayModeBar":False})
        st.markdown("</div>",unsafe_allow_html=True)

# ─── LAPORAN ───────────────────────────────────────────────────────────────────
def page_laporan(df, tahun, bulan):
    render_header("Laporan Bulanan")
    df_bulan = df[(df["tahun"]==tahun)&(df["bulan"]==bulan)] if not df.empty else pd.DataFrame()
    if df_bulan.empty:
        st.markdown("<div class='alert-box alert-warning'>Belum ada data untuk " + bulan + " " + str(tahun) + ".</div>", unsafe_allow_html=True)
        return
    bulan_ke = get_bulan_ke(bulan)
    bulan_lalu = BULAN_LIST[bulan_ke-2] if bulan_ke > 1 else None
    df_lalu = df[(df["tahun"]==tahun)&(df["bulan"]==bulan_lalu)] if (bulan_lalu and not df.empty) else pd.DataFrame()
    rows = []
    for wil in WILAYAH.keys():
        r = df_bulan[df_bulan["wilayah"]==wil]
        rl = df_lalu[df_lalu["wilayah"]==wil] if not df_lalu.empty else pd.DataFrame()
        if r.empty:
            rows.append({"Wilayah":wil,"Sasaran":"—","Hadir":"—","Cakupan (%)":"—","Stunting":"—","Trend":"—","Status":"Belum Lapor"})
        else:
            s=int(r["stunting"].sum()); h=int(r["hadir"].sum()); sa=int(r["sasaran"].sum())
            pct=round(h/sa*100,1) if sa>0 else 0
            sl=int(rl["stunting"].sum()) if not rl.empty else None
            if sl is None: trend,status="—","Data Awal"
            elif s>sl: trend,status="Naik +"+str(s-sl),"Naik"
            elif s<sl: trend,status="Turun -"+str(sl-s),"Turun"
            else: trend,status="Tetap","Tetap"
            rows.append({"Wilayah":wil,"Sasaran":sa,"Hadir":h,"Cakupan (%)":pct,"Stunting":s,"Trend":trend,"Status":status})
    df_lap = pd.DataFrame(rows)
    st.dataframe(df_lap, use_container_width=True, hide_index=True)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_lap.to_excel(writer, sheet_name="Laporan " + bulan + " " + str(tahun), index=False)
        if not df.empty: df.to_excel(writer, sheet_name="Data Lengkap", index=False)
    buffer.seek(0)
    st.download_button("Export ke Excel", data=buffer, file_name="SITUNTAS_" + bulan + "_" + str(tahun) + ".xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")

# ─── KELOLA USER ───────────────────────────────────────────────────────────────
def page_kelola_user():
    render_header("Kelola Pengguna")
    users = load_users()
    tab1, tab2 = st.tabs(["Daftar Pengguna","Tambah Pengguna"])
    with tab1:
        st.dataframe(users[["username","nama","role","wilayah","aktif"]], use_container_width=True, hide_index=True)
    with tab2:
        with st.form("form_add_user", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                nu=st.text_input("Username *"); nn=st.text_input("Nama Lengkap *"); nr=st.selectbox("Role *",["pegawai","admin"])
            with c2:
                np=st.text_input("Password *",type="password"); nw=st.selectbox("Wilayah *",["semua"]+list(WILAYAH.keys())); na=st.checkbox("Aktif",value=True)
            if st.form_submit_button("Tambah", type="primary", use_container_width=True):
                if not nu or not nn or not np:
                    st.error("Semua field wajib diisi.")
                elif nu in users["username"].values:
                    st.error("Username sudah ada.")
                else:
                    users = pd.concat([users, pd.DataFrame([{"username":nu,"password":hash_pw(np),"nama":nn,"role":nr,"wilayah":nw,"aktif":na}])], ignore_index=True)
                    ok, msg = save_users(users)
                    if ok:
                        st.success(nn + " berhasil ditambahkan!")
                    else:
                        st.error("Gagal simpan: " + msg)
                    st.rerun()

# ─── KELOLA DATA ───────────────────────────────────────────────────────────────
def page_kelola_data(df):
    render_header("Kelola Data")
    tab1, tab2 = st.tabs(["Edit","Hapus"])
    with tab1:
        if df.empty: st.info("Belum ada data.")
        else:
            c1,c2,c3=st.columns(3)
            with c1: t=st.selectbox("Tahun",sorted(df["tahun"].unique()),key="te")
            with c2: b=st.selectbox("Bulan",[x for x in BULAN_LIST if x in df[df["tahun"]==t]["bulan"].values],key="be")
            with c3: p=st.selectbox("Posyandu",df[(df["tahun"]==t)&(df["bulan"]==b)]["posyandu"].unique().tolist(),key="pe")
            if p:
                idx=df[(df["tahun"]==t)&(df["bulan"]==b)&(df["posyandu"]==p)].index
                if len(idx)>0:
                    i=idx[0]
                    with st.form("fe"):
                        e1,e2,e3=st.columns(3)
                        with e1: ns=st.number_input("Sasaran",value=int(df.loc[i,"sasaran"]),min_value=0)
                        with e2: nh=st.number_input("Hadir",value=int(df.loc[i,"hadir"]),min_value=0)
                        with e3: nst=st.number_input("Stunting",value=int(df.loc[i,"stunting"]),min_value=0)
                        if st.form_submit_button("Update",type="primary"):
                            df.loc[i,["sasaran","hadir","stunting"]]=[ns,nh,nst]
                            df.loc[i,"waktu_input"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ok, msg = save_data(df)
                            if ok: st.success("Update berhasil!")
                            else: st.error("Gagal: " + msg)
                            st.rerun()
    with tab2:
        if df.empty: st.info("Belum ada data.")
        else:
            c1,c2,c3=st.columns(3)
            with c1: td=st.selectbox("Tahun",sorted(df["tahun"].unique()),key="td")
            with c2: bd=st.selectbox("Bulan",[x for x in BULAN_LIST if x in df[df["tahun"]==td]["bulan"].values],key="bd")
            with c3: pd_sel=st.selectbox("Posyandu",df[(df["tahun"]==td)&(df["bulan"]==bd)]["posyandu"].unique().tolist(),key="pd")
            if st.checkbox("Yakin hapus?") and st.button("Hapus",type="primary"):
                df=df[~((df["tahun"]==td)&(df["bulan"]==bd)&(df["posyandu"]==pd_sel))].reset_index(drop=True)
                ok, msg = save_data(df)
                if ok: st.success("Data berhasil dihapus!")
                else: st.error("Gagal: " + msg)
                st.rerun()
    return df

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    df = load_data()
    if st.session_state.is_public:
        menu, tahun, bulan = render_sidebar(role="publik")
        page_dashboard(df, tahun, bulan, is_public=True)
        return
    if not st.session_state.logged_in:
        login_page(); return
    user = st.session_state.user
    role = user["role"]
    menu, tahun, bulan = render_sidebar(role=role)
    if menu=="Dashboard Utama": page_dashboard(df,tahun,bulan)
    elif menu=="Input Data": df=page_input(df,user)
    elif menu=="Import Google Sheets": df=page_import(df)
    elif menu=="Analisis & Tren": page_analisis(df,tahun)
    elif menu=="Laporan": page_laporan(df,tahun,bulan)
    elif menu=="Kelola Pengguna":
        if role=="admin": page_kelola_user()
        else: st.error("Akses ditolak.")
    elif menu=="Kelola Data":
        if role=="admin": df=page_kelola_data(df)
        else: st.error("Akses ditolak.")


if __name__ == "__main__":
    main()
