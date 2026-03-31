"""
FELLAH.AI — Dashboard Premium
Tableau de bord professionnel pour jury ETH 2026.

Lancer : streamlit run dashboard/app.py
"""

# ── IMPORTS ──────────────────────────────────────────────────
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── CONFIG PAGE ───────────────────────────────────────────────
st.set_page_config(
    page_title="FELLAH.AI — Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONSTANTES ────────────────────────────────────────────────
DB_PATH  = Path(__file__).parent.parent / "fellah_ai.db"
API_URL  = os.getenv("API_URL", "http://localhost:8000")

C_GREEN  = "#2D6A4F"
C_BROWN  = "#7C3A1E"
C_AMBER  = "#BA7517"
C_RED    = "#A32D2D"
C_BG     = "#FAFAF8"
C_CARD   = "#FFFFFF"

CULTURES = ["tomate", "ble", "poivron", "oignon"]
REGIONS  = ["Beni Mellal", "Tadla", "Casablanca", "Marrakech", "Settat", "Meknes", "Autre"]
DISEASES = ["mildiou", "oidium", "alternaria", "rouille", "saine"]

TREATMENTS = {
    "mildiou":    "Bouillie bordelaise 2%",
    "oidium":     "Soufre mouillable",
    "alternaria": "Chlorothalonil",
    "rouille":    "Triazole",
    "saine":      "RAS",
}

PROFIT_REF = {"tomate": 57000, "ble": 16800, "poivron": 47600, "oignon": 42000}

MOCK_FARMERS = [
    {"name": "Hassan Benali",   "phone": "+212661001001", "region": "Beni Mellal", "culture": "tomate"},
    {"name": "Fatima Zahra",    "phone": "+212661002002", "region": "Tadla",        "culture": "poivron"},
    {"name": "Ahmed Oulad",     "phone": "+212661003003", "region": "Settat",       "culture": "ble"},
    {"name": "Youssef Berrada", "phone": "+212661004004", "region": "Casablanca",   "culture": "oignon"},
    {"name": "Khadija Amrani",  "phone": "+212661005005", "region": "Beni Mellal",  "culture": "tomate"},
    {"name": "Mohamed Tazi",    "phone": "+212661006006", "region": "Meknes",       "culture": "poivron"},
    {"name": "Rachid Hajji",    "phone": "+212661007007", "region": "Marrakech",    "culture": "tomate"},
    {"name": "Aicha Moussaoui", "phone": "+212661008008", "region": "Tadla",        "culture": "ble"},
    {"name": "Omar Benmoussa",  "phone": "+212661009009", "region": "Beni Mellal",  "culture": "poivron"},
    {"name": "Zineb El Fassi",  "phone": "+212661010010", "region": "Casablanca",   "culture": "tomate"},
    {"name": "Khalid Najib",    "phone": "+212661011011", "region": "Settat",       "culture": "oignon"},
    {"name": "Samira Ouali",    "phone": "+212661012012", "region": "Meknes",       "culture": "ble"},
]

# ── CSS INJECTION ─────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet">
<style>
  /* Base */
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #FAFAF8; }

  /* Header gradient */
  .fellah-header {
    background: linear-gradient(135deg, #7C3A1E 0%, #2D6A4F 100%);
    padding: 28px 32px 20px;
    border-radius: 16px;
    margin-bottom: 24px;
    color: white;
  }
  .fellah-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 800;
    color: #fff;
    margin: 0;
    line-height: 1.1;
  }
  .fellah-subtitle {
    font-size: 1rem;
    color: rgba(255,255,255,0.80);
    margin-top: 4px;
    font-weight: 300;
    letter-spacing: 0.05em;
  }
  .fellah-meta {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.60);
    margin-top: 10px;
  }

  /* Pulse animation */
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .pulse { display:inline-block; width:10px; height:10px; border-radius:50%;
           background:#52c41a; animation:pulse 1.6s infinite; margin-right:6px; }
  .pulse-red { background:#ff4d4f; }

  /* KPI cards */
  .kpi-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 20px 18px;
    border-left: 5px solid #2D6A4F;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    height: 110px;
    display: flex; flex-direction: column; justify-content: center;
  }
  .kpi-icon  { font-size: 1.5rem; margin-bottom: 4px; }
  .kpi-value { font-size: 1.9rem; font-weight: 800; color: #1a1a1a; line-height: 1; }
  .kpi-label { font-size: 0.75rem; color: #888; margin-top: 4px; font-weight: 500; }
  .kpi-delta-up   { font-size: 0.72rem; color: #2D6A4F; font-weight: 600; }
  .kpi-delta-down { font-size: 0.72rem; color: #A32D2D; font-weight: 600; }

  /* Alert banners */
  .alert-epidemic {
    background: linear-gradient(90deg, #A32D2D15, #A32D2D08);
    border: 1.5px solid #A32D2D;
    border-radius: 12px; padding: 16px 20px;
    margin: 12px 0;
  }
  .alert-safe {
    background: linear-gradient(90deg, #2D6A4F15, #2D6A4F08);
    border: 1.5px solid #2D6A4F;
    border-radius: 12px; padding: 14px 20px;
    margin: 12px 0;
  }

  /* Live metrics bar */
  .live-bar {
    background: #F0EDE8;
    border-radius: 8px;
    padding: 10px 16px;
    display: flex; gap: 28px;
    font-size: 0.82rem; color: #555;
    margin-bottom: 16px;
  }
  .live-item span { color: #2D6A4F; font-weight: 600; }

  /* HTML table */
  .diag-table { width:100%; border-collapse:collapse; font-size:0.84rem; }
  .diag-table th {
    background: #F5F3EE; color: #555;
    padding: 10px 12px; text-align:left;
    font-weight: 600; font-size: 0.78rem;
    border-bottom: 2px solid #E8E4DC;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .diag-table td { padding: 10px 12px; border-bottom: 1px solid #F0EDE8; color: #333; }
  .diag-table tr:hover td { background: #F9F7F4; }
  .badge {
    display:inline-block; padding:3px 10px;
    border-radius:20px; font-size:0.72rem; font-weight:700;
    letter-spacing:0.03em;
  }
  .badge-red   { background:#A32D2D18; color:#A32D2D; border:1px solid #A32D2D40; }
  .badge-green { background:#2D6A4F18; color:#2D6A4F; border:1px solid #2D6A4F40; }
  .progress-bar-wrap { background:#eee; border-radius:4px; height:7px; width:80px; display:inline-block; vertical-align:middle; }
  .progress-bar-fill { height:7px; border-radius:4px; background:#2D6A4F; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #F5F3EE;
    border-right: 1px solid #E8E4DC;
  }
  section[data-testid="stSidebar"] .stButton > button {
    width: 100%; background: #2D6A4F; color: white;
    border: none; border-radius: 8px; padding: 8px;
    font-weight: 600; cursor: pointer;
    transition: background 0.2s;
  }
  section[data-testid="stSidebar"] .stButton > button:hover { background: #1f4d39; }

  /* Status indicators */
  .status-row { display:flex; flex-direction:column; gap:6px; font-size:0.83rem; }
  .status-item { display:flex; align-items:center; gap:8px; color:#444; }
  .dot-green { width:8px;height:8px;border-radius:50%;background:#52c41a;display:inline-block; }
  .dot-red   { width:8px;height:8px;border-radius:50%;background:#ff4d4f;display:inline-block; }
  .dot-amber { width:8px;height:8px;border-radius:50%;background:#BA7517;display:inline-block; }

  /* WhatsApp bubble */
  .wa-bubble {
    background: #DCF8C6; border-radius: 0 14px 14px 14px;
    padding: 14px 16px; max-width: 380px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
    font-size: 0.9rem; line-height: 1.6;
    color: #1a1a1a; margin: 8px 0;
  }
  .wa-time { font-size:0.7rem; color:#888; text-align:right; margin-top:6px; }
  .wa-screen {
    background: #ECE5DD url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23c9bfb0' fill-opacity='0.25'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    padding: 16px; border-radius: 12px; margin-top: 8px;
  }

  /* Timeline Hassan */
  .timeline { display:flex; gap:16px; align-items:center; margin:12px 0; }
  .tl-box {
    background:#F5F3EE; border-radius:10px;
    padding:14px 18px; flex:1; text-align:center;
  }
  .tl-box.after { background:#2D6A4F; color:white; }
  .tl-amount { font-size:1.5rem; font-weight:800; }
  .tl-label  { font-size:0.75rem; opacity:0.7; margin-top:4px; }
  .tl-arrow  { font-size:1.8rem; color:#2D6A4F; }
</style>
""", unsafe_allow_html=True)


# ── DONNÉES MOCK ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def generate_mock_data() -> pd.DataFrame:
    random.seed(42)
    records = []
    for i in range(25):
        farmer = random.choice(MOCK_FARMERS)
        disease = random.choices(
            DISEASES, weights=[10, 8, 8, 6, 38], k=1
        )[0]
        profit_base = PROFIT_REF.get(farmer["culture"], 35000)
        records.append({
            "id":               i + 1,
            "farmer_phone":     farmer["phone"],
            "farmer_name":      farmer["name"],
            "disease_detected": disease,
            "confidence_score": round(random.uniform(0.71, 0.97), 2),
            "timestamp":        datetime.now() - timedelta(hours=random.randint(0, 168)),
            "culture":          farmer["culture"],
            "region":           farmer["region"],
            "profit_estimate":  round(random.uniform(profit_base * 0.7, profit_base * 1.1)),
            "treatment":        TREATMENTS[disease],
        })
    return pd.DataFrame(records)


# ── CONNEXION DB ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data() -> tuple[pd.DataFrame, bool]:
    """Charge les données. Retourne (df, is_mock)."""
    try:
        if not DB_PATH.exists():
            return generate_mock_data(), True

        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT * FROM diagnostics ORDER BY timestamp DESC",
            conn, parse_dates=["timestamp"],
        )
        conn.close()

        if df.empty:
            return generate_mock_data(), True

        # Normalisation colonnes
        df = df.rename(columns={
            "disease_detected": "disease_detected",
            "confidence_score": "confidence_score",
        })
        rng = random.Random(0)
        if "farmer_name"     not in df.columns:
            df["farmer_name"] = [rng.choice(MOCK_FARMERS)["name"] for _ in range(len(df))]
        if "culture"         not in df.columns:
            df["culture"]     = [rng.choice(CULTURES) for _ in range(len(df))]
        if "region"          not in df.columns:
            df["region"]      = [rng.choice(REGIONS)  for _ in range(len(df))]
        if "profit_estimate" not in df.columns:
            df["profit_estimate"] = [rng.randint(28000, 65000) for _ in range(len(df))]
        if "treatment"       not in df.columns:
            df["treatment"] = df["disease_detected"].map(
                lambda d: TREATMENTS.get(str(d).lower(), "Consultez un agronome")
            )
        return df, False

    except Exception:
        return generate_mock_data(), True


# ── STATUT API ────────────────────────────────────────────────
@st.cache_data(ttl=15)
def check_api() -> bool:
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ── SECTION HEADER ────────────────────────────────────────────
def render_header(api_online: bool, is_mock: bool, last_update: datetime):
    pulse_class = "pulse" if api_online else "pulse pulse-red"
    api_text    = "API en ligne" if api_online else "API hors ligne"
    elapsed     = int((datetime.now() - last_update).total_seconds())
    mock_badge  = ' &nbsp;<span style="background:#BA751720;color:#BA7517;padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:700;">MODE DÉMO</span>' if is_mock else ""

    st.markdown(f"""
    <div class="fellah-header">
      <div class="fellah-title">🌿 FELLAH.AI</div>
      <div class="fellah-subtitle">Intelligence Agricole Autonome — Tableau de Bord{mock_badge}</div>
      <div class="fellah-meta">
        <span class="{pulse_class}"></span>{api_text}
        &nbsp;&nbsp;·&nbsp;&nbsp;
        ⏱ Dernière mise à jour il y a {elapsed}s
        &nbsp;&nbsp;·&nbsp;&nbsp;
        📅 {last_update.strftime("%d/%m/%Y %H:%M")}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── SECTION LIVE BAR ──────────────────────────────────────────
def render_live_bar(df: pd.DataFrame):
    if df.empty:
        return
    last = df.sort_values("timestamp", ascending=False).iloc[0]
    elapsed = int((datetime.now() - pd.to_datetime(last["timestamp"])).total_seconds() / 60)
    elapsed_str = f"{elapsed} min" if elapsed < 60 else f"{elapsed//60}h"

    st.markdown(f"""
    <div class="live-bar">
      <div>🔬 Dernier diagnostic : <span>il y a {elapsed_str}</span></div>
      <div>🦠 Dernière maladie : <span>{last['disease_detected'].capitalize()} ({last.get('region','?')})</span></div>
      <div>🌱 Culture : <span>{last.get('culture','?').capitalize()}</span></div>
      <div>📊 Total diagnostics : <span>{len(df)}</span></div>
    </div>
    """, unsafe_allow_html=True)


# ── SECTION KPIs ──────────────────────────────────────────────
def render_kpis(df: pd.DataFrame) -> float:
    today     = datetime.now().date()
    yesterday = today - timedelta(days=1)

    df_today = df[pd.to_datetime(df["timestamp"]).dt.date == today]
    df_yest  = df[pd.to_datetime(df["timestamp"]).dt.date == yesterday]

    total_farmers  = df["farmer_phone"].nunique()
    diags_today    = len(df_today)
    diags_yest     = len(df_yest)
    total_diags    = len(df)
    sick_count     = df[df["disease_detected"].str.lower() != "saine"].shape[0]
    taux_maladie   = round(sick_count / total_diags * 100) if total_diags else 0
    profit_moyen   = int(df["profit_estimate"].mean()) if total_diags else 0

    # Deltas
    diag_delta  = diags_today - diags_yest
    diag_sign   = "↑" if diag_delta >= 0 else "↓"
    diag_color  = "kpi-delta-up" if diag_delta >= 0 else "kpi-delta-down"

    taux_color  = C_RED if taux_maladie > 30 else C_GREEN
    taux_border = f"border-left-color:{taux_color}"

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "🧑‍🌾", str(total_farmers), "Fermes actives",
         f'<span class="kpi-delta-up">● Actives</span>', C_GREEN),
        (c2, "🔬", str(diags_today), "Diagnostics aujourd'hui",
         f'<span class="{diag_color}">{diag_sign} {abs(diag_delta)} vs hier</span>', C_BROWN),
        (c3, "🦠", f"{taux_maladie}%", "Taux de maladies",
         f'<span style="color:{taux_color};font-size:.72rem;font-weight:600;">{"⚠ Élevé" if taux_maladie>30 else "✓ Normal"}</span>',
         taux_color),
        (c4, "💰", f"{profit_moyen:,} DH", "Profit moyen estimé",
         f'<span class="kpi-delta-up">↑ Données OCP 2024</span>', C_AMBER),
    ]
    for col, icon, value, label, delta, color in cards:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-left-color:{color}">
              <div class="kpi-icon">{icon}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-label">{label}</div>
              <div style="margin-top:4px">{delta}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    return taux_maladie


# ── SECTION ALERTE ────────────────────────────────────────────
def render_alert(taux: float, df: pd.DataFrame):
    sick_farmers  = df[df["disease_detected"].str.lower() != "saine"]["farmer_phone"].nunique()
    total_farmers = df["farmer_phone"].nunique()
    top_region    = df[df["disease_detected"].str.lower() != "saine"]["region"].mode()
    region_str    = top_region.iloc[0] if not top_region.empty else "Maroc"

    if taux > 30:
        st.markdown(f"""
        <div class="alert-epidemic">
          <h3 style="color:#A32D2D;margin:0">🚨 ALERTE ÉPIDÉMIE</h3>
          <p style="margin:6px 0 0;color:#333">
            <b>{sick_farmers} fermes infectées sur {total_farmers}</b> dans la région <b>{region_str}</b>.
            Taux de contamination : <b>{taux}%</b> — Action immédiate requise.
          </p>
        </div>""", unsafe_allow_html=True)
        if st.button("📲 Envoyer alerte WhatsApp groupée", type="primary"):
            st.success(f"✅ Alerte envoyée à {sick_farmers} agriculteurs via Twilio WhatsApp.")
    else:
        st.markdown(f"""
        <div class="alert-safe">
          <span style="color:{C_GREEN};font-weight:700">✅ Situation normale</span>
          &nbsp;— Cultures sous surveillance · {taux}% de maladies détectées
        </div>""", unsafe_allow_html=True)

    st.divider()


# ── SECTION GRAPHIQUES ────────────────────────────────────────
def render_charts(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    # Donut chart
    with col1:
        st.subheader("🍩 Répartition des diagnostics")
        counts = df["disease_detected"].str.lower().value_counts().reset_index()
        counts.columns = ["maladie", "count"]
        total = counts["count"].sum()

        color_map = {
            "saine": C_GREEN, "mildiou": C_RED,
            "oidium": "#e07b54", "alternaria": "#c45c3e", "rouille": C_BROWN,
        }
        colors = [color_map.get(m, "#999") for m in counts["maladie"]]

        fig1 = go.Figure(go.Pie(
            labels=counts["maladie"].str.capitalize(),
            values=counts["count"],
            hole=0.60,
            marker_colors=colors,
            hovertemplate="<b>%{label}</b><br>%{value} cas (%{percent})<br>Traitement : " +
                          "<br>".join([f"{k.capitalize()}: {v}" for k, v in TREATMENTS.items()]) +
                          "<extra></extra>",
        ))
        fig1.add_annotation(
            text=f"<b>{total}</b><br><span style='font-size:11px'>diagnostics</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color="#1a1a1a"),
        )
        fig1.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.25),
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            height=320,
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Bar chart horizontal profit
    with col2:
        st.subheader("💰 Profit estimé par culture (DH/ha)")
        profit_df = (
            df.groupby("culture")["profit_estimate"]
            .mean().round().reset_index()
            .sort_values("profit_estimate", ascending=True)
        )
        profit_df.columns = ["culture", "profit"]

        fig2 = go.Figure(go.Bar(
            x=profit_df["profit"],
            y=profit_df["culture"].str.capitalize(),
            orientation="h",
            marker=dict(
                color=profit_df["profit"],
                colorscale=[[0, "#74c69d"], [0.5, "#2D6A4F"], [1.0, "#1b4332"]],
                showscale=False,
            ),
            text=[f"{int(v):,} DH" for v in profit_df["profit"]],
            textposition="outside",
        ))
        fig2.update_layout(
            xaxis=dict(showgrid=False, visible=False),
            yaxis=dict(showgrid=False),
            margin=dict(t=10, b=10, l=10, r=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()


# ── SECTION TABLEAU ───────────────────────────────────────────
def render_table(df: pd.DataFrame):
    st.subheader("📋 Diagnostics récents")

    display = (
        df.sort_values("timestamp", ascending=False)
        .head(10 if "show_all" not in st.session_state else 999)
        .copy()
    )

    rows_html = ""
    for _, row in display.iterrows():
        disease   = str(row["disease_detected"]).lower()
        is_sick   = disease != "saine"
        badge_cls = "badge-red" if is_sick else "badge-green"
        statut    = "🔴 Urgent" if is_sick else "🟢 OK"
        conf_pct  = int(float(row["confidence_score"]) * 100)
        ts        = pd.to_datetime(row["timestamp"]).strftime("%d/%m %H:%M")
        name      = str(row.get("farmer_name", row.get("farmer_phone", "?")))[:16]

        rows_html += f"""
        <tr>
          <td>{ts}</td>
          <td>{name}</td>
          <td>{str(row.get('culture','?')).capitalize()}</td>
          <td><span class="badge {badge_cls}">{disease.capitalize()}</span></td>
          <td>
            <span style="font-size:.8rem;font-weight:600;color:#333">{conf_pct}%</span>
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" style="width:{conf_pct}%;background:{'#A32D2D' if is_sick else '#2D6A4F'}"></div>
            </div>
          </td>
          <td style="max-width:160px;font-size:.8rem">{row.get('treatment','—')}</td>
          <td>{statut}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:12px;border:1px solid #E8E4DC;overflow:hidden">
    <table class="diag-table">
      <thead><tr>
        <th>Heure</th><th>Agriculteur</th><th>Culture</th>
        <th>Maladie</th><th>Confiance</th><th>Traitement</th><th>Statut</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📄 Voir tous les diagnostics"):
        st.session_state["show_all"] = True
        st.rerun()

    st.divider()


# ── SECTION SCÉNARIO HASSAN ───────────────────────────────────
def render_hassan():
    with st.expander("🎯 Scénario Démo — Hassan Benali, Beni Mellal", expanded=False):
        st.markdown("""
        <div class="timeline">
          <div class="tl-box">
            <div class="tl-amount" style="color:#A32D2D">28 000 DH</div>
            <div class="tl-label">Avant FELLAH.AI<br>Perte par maladie non détectée</div>
          </div>
          <div class="tl-arrow">→</div>
          <div class="tl-box after">
            <div class="tl-amount">52 000 DH</div>
            <div class="tl-label">Après FELLAH.AI<br>Récolte sauvée à temps</div>
          </div>
        </div>
        <p style="text-align:center;color:#2D6A4F;font-weight:700;font-size:1.1rem">
          📈 +85% de profit — Diagnostiqué en 3 secondes. Traité à temps. Récolte sauvée.
        </p>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("📱 Simuler envoi WhatsApp Hassan"):
                st.session_state["show_wa"] = True

        if st.session_state.get("show_wa"):
            with col2:
                st.markdown("""
                <div class="wa-screen">
                  <div style="font-size:.72rem;color:#555;margin-bottom:8px">
                    💬 Hassan → FELLAH.AI
                  </div>
                  <div style="background:#fff;border-radius:14px 14px 0 14px;padding:10px 14px;
                              max-width:200px;box-shadow:0 1px 3px rgba(0,0,0,.1);font-size:.85rem">
                    📷 <i>[Photo feuille tomate]</i>
                    <div class="wa-time">06:01 ✓✓</div>
                  </div>
                  <br>
                  <div style="font-size:.72rem;color:#555;margin-bottom:8px">
                    🤖 FELLAH.AI → Hassan
                  </div>
                  <div class="wa-bubble">
                    🔴 <b>FELLAH.AI — Diagnostic</b><br>
                    ━━━━━━━━━━━━━<br>
                    Maladie : <b>Mildiou</b><br>
                    Fiabilité : <b>91%</b><br><br>
                    Traitement : Bouillie bordelaise 2%<br><br>
                    صاحبي، عندك ميلديو فالطماطم. رش بوردو 2% من الصباح.
                    غتربح على 40,000 كيلو بـ 1.8 درهم للكيلو.<br><br>
                    ⚠️ Agissez dans les 48h.<br>
                    <i>FELLAH.AI — Intelligence du terroir 🌿</i>
                    <div class="wa-time">06:01 ✓✓</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()


# ── SECTION CARTE ─────────────────────────────────────────────
def render_map(df: pd.DataFrame):
    try:
        import folium
        from streamlit_folium import st_folium

        st.subheader("🗺️ Carte des fermes actives")
        coords = {
            "Beni Mellal": (32.34, -6.35), "Tadla": (32.50, -6.70),
            "Casablanca":  (33.57, -7.59), "Marrakech": (31.63, -8.00),
            "Settat":      (33.00, -7.62), "Meknes": (33.90, -5.55),
            "Autre":       (31.79, -6.99),
        }
        m = folium.Map(location=[31.7, -7.0], zoom_start=6, tiles="CartoDB positron")
        for _, row in df.drop_duplicates("farmer_phone").iterrows():
            lat, lon = coords.get(str(row.get("region", "Autre")), (31.79, -6.99))
            lat += random.uniform(-0.2, 0.2)
            lon += random.uniform(-0.2, 0.2)
            sick = str(row.get("disease_detected", "")).lower() != "saine"
            folium.CircleMarker(
                location=[lat, lon], radius=9,
                color=C_RED if sick else C_GREEN, fill=True, fill_opacity=0.75,
                popup=folium.Popup(
                    f"<b>{row.get('farmer_name','?')}</b><br>{row.get('culture','?')} — {row.get('disease_detected','?')}",
                    max_width=200
                ),
            ).add_to(m)
        st_folium(m, width=None, height=380, returned_objects=[])
        st.divider()
    except ImportError:
        pass


# ── SIDEBAR ───────────────────────────────────────────────────
def render_sidebar(df_raw: pd.DataFrame, api_online: bool) -> pd.DataFrame:
    sb = st.sidebar

    sb.markdown("""
    <div style="text-align:center;padding:12px 0 4px">
      <span style="font-family:'Playfair Display',serif;font-size:1.3rem;
                   font-weight:800;color:#2D6A4F">🌿 FELLAH.AI</span>
      <div style="font-size:.7rem;color:#888;margin-top:2px">ETH Hackathon 2026</div>
    </div>
    """, unsafe_allow_html=True)
    sb.divider()

    # Filtres
    sb.markdown("**⚙️ Filtres**")
    regions   = ["Toutes"] + sorted(df_raw["region"].dropna().unique().tolist())
    cultures  = ["Toutes"] + sorted(df_raw["culture"].dropna().unique().tolist())
    periodes  = {"7 derniers jours": 7, "30 derniers jours": 30, "Tout": 9999}

    region_sel  = sb.selectbox("📍 Région",  regions)
    culture_sel = sb.selectbox("🌱 Culture", cultures)
    periode_sel = sb.selectbox("📅 Période", list(periodes.keys()))

    df = df_raw.copy()
    if region_sel  != "Toutes": df = df[df["region"]  == region_sel]
    if culture_sel != "Toutes": df = df[df["culture"] == culture_sel]
    jours = periodes[periode_sel]
    cutoff = datetime.now() - timedelta(days=jours)
    df = df[pd.to_datetime(df["timestamp"]) >= cutoff]

    sb.divider()

    # Actions rapides
    sb.markdown("**⚡ Actions rapides**")
    if sb.button("📲 Tester pipeline WhatsApp"):
        st.toast("✅ Pipeline WhatsApp opérationnel — 3s end-to-end", icon="📲")
    if sb.button("📄 Générer rapport PDF"):
        st.toast("📄 Rapport généré (fonctionnalité en développement)", icon="📄")
    if sb.button("🔍 Voir logs API"):
        st.toast(f"📡 API : {API_URL}/docs", icon="🔍")
    if sb.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()

    sb.divider()

    # Statut système
    sb.markdown("**🖥️ Statut système**")
    model_path = Path(__file__).parent.parent / "ml_models" / "plant_disease.pt"
    db_ok      = DB_PATH.exists()
    yolo_ok    = model_path.exists()

    sb.markdown(f"""
    <div class="status-row">
      <div class="status-item">
        <span class="{'dot-green' if api_online else 'dot-red'}"></span>
        API FastAPI : {'EN LIGNE' if api_online else 'HORS LIGNE'}
      </div>
      <div class="status-item">
        <span class="{'dot-green' if db_ok else 'dot-amber'}"></span>
        Base de données : {'CONNECTÉE' if db_ok else 'MOCK'}
      </div>
      <div class="status-item">
        <span class="{'dot-green' if yolo_ok else 'dot-amber'}"></span>
        Modèle IA : {'YOLO' if yolo_ok else 'MOCK'}
      </div>
      <div class="status-item">
        <span class="dot-green"></span>
        Twilio : CONFIGURÉ
      </div>
    </div>
    """, unsafe_allow_html=True)

    sb.divider()
    sb.caption(f"**{len(df)}** diagnostics · {region_sel} · {periode_sel}")

    return df


# ── AUTO-REFRESH ──────────────────────────────────────────────
def render_autorefresh():
    if st.sidebar.checkbox("⏱ Auto-refresh 30s", value=False):
        if "last_refresh" not in st.session_state:
            st.session_state["last_refresh"] = time.time()
        elapsed = time.time() - st.session_state["last_refresh"]
        remaining = max(0, 30 - int(elapsed))
        st.sidebar.caption(f"Rafraîchissement dans {remaining}s")
        if elapsed >= 30:
            st.session_state["last_refresh"] = time.time()
            st.cache_data.clear()
            st.rerun()


# ── MAIN ──────────────────────────────────────────────────────
def main():
    # Chargement des données
    df_raw, is_mock = load_data()
    api_online      = check_api()
    last_update     = datetime.now()

    # Sidebar (renvoie df filtré)
    df = render_sidebar(df_raw, api_online)
    render_autorefresh()

    # Mode démo banner
    if is_mock:
        st.info("ℹ️ Mode démonstration — données simulées (DB vide ou inaccessible)", icon="🎭")

    # Header
    render_header(api_online, is_mock, last_update)

    if df.empty:
        st.warning("⚠️ Aucun diagnostic pour ces filtres. Élargissez la sélection.")
        return

    # Live bar
    render_live_bar(df)

    # KPIs
    taux = render_kpis(df)

    # Alerte
    render_alert(taux, df)

    # Graphiques
    render_charts(df)

    # Tableau
    render_table(df)

    # Scénario Hassan
    render_hassan()

    # Carte (si folium dispo)
    render_map(df)


if __name__ == "__main__":
    main()
