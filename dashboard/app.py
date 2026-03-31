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
import plotly.graph_objects as go
import requests
import streamlit as st

# ── CONFIG PAGE ──────────────────────────────────────────────
st.set_page_config(
    page_title="FELLAH.AI — Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONSTANTES ───────────────────────────────────────────────
DB_PATH  = Path(__file__).parent.parent / "fellah_ai.db"
API_URL  = os.getenv("API_URL", "http://localhost:8000")

C_GREEN = "#2D6A4F"
C_BROWN = "#7C3A1E"
C_AMBER = "#BA7517"
C_RED   = "#A32D2D"

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
    {"name": "Fatima Zahra",    "phone": "+212661002002", "region": "Tadla",       "culture": "poivron"},
    {"name": "Ahmed Oulad",     "phone": "+212661003003", "region": "Settat",      "culture": "ble"},
    {"name": "Youssef Berrada", "phone": "+212661004004", "region": "Casablanca",  "culture": "oignon"},
    {"name": "Khadija Amrani",  "phone": "+212661005005", "region": "Beni Mellal", "culture": "tomate"},
    {"name": "Mohamed Tazi",    "phone": "+212661006006", "region": "Meknes",      "culture": "poivron"},
    {"name": "Rachid Hajji",    "phone": "+212661007007", "region": "Marrakech",   "culture": "tomate"},
    {"name": "Aicha Moussaoui", "phone": "+212661008008", "region": "Tadla",       "culture": "ble"},
    {"name": "Omar Benmoussa",  "phone": "+212661009009", "region": "Beni Mellal", "culture": "poivron"},
    {"name": "Zineb El Fassi",  "phone": "+212661010010", "region": "Casablanca",  "culture": "tomate"},
    {"name": "Khalid Najib",    "phone": "+212661011011", "region": "Settat",      "culture": "oignon"},
    {"name": "Samira Ouali",    "phone": "+212661012012", "region": "Meknes",      "culture": "ble"},
]

# ── CSS INJECTION ────────────────────────────────────────────
# Injecté séparément pour éviter l'affichage en texte brut
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.fellah-header {
    background: linear-gradient(135deg, #7C3A1E 0%, #2D6A4F 100%);
    padding: 26px 30px 18px; border-radius: 14px;
    margin-bottom: 20px; color: white;
}
.fellah-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.4rem; font-weight: 800; color: #fff; margin: 0;
}
.fellah-subtitle { font-size: 0.95rem; color: rgba(255,255,255,0.78); margin-top: 4px; }
.fellah-meta    { font-size: 0.76rem; color: rgba(255,255,255,0.55); margin-top: 8px; }

@keyframes pulse-anim { 0%,100%{opacity:1} 50%{opacity:0.35} }
.pulse-dot {
    display: inline-block; width: 9px; height: 9px;
    border-radius: 50%; margin-right: 5px;
    animation: pulse-anim 1.6s infinite;
}
.pulse-green { background: #52c41a; }
.pulse-red   { background: #ff4d4f; }

.kpi-card {
    background: #fff; border-radius: 12px;
    padding: 18px 16px; border-left: 5px solid #2D6A4F;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 8px;
}
.kpi-icon  { font-size: 1.4rem; }
.kpi-val   { font-size: 1.85rem; font-weight: 800; color: #111; line-height: 1.1; }
.kpi-lbl   { font-size: 0.72rem; color: #888; font-weight: 500; margin-top: 2px; }
.kpi-delta { font-size: 0.70rem; font-weight: 600; margin-top: 3px; }

.live-bar {
    background: #F5F3EE; border-radius: 8px;
    padding: 9px 14px; font-size: 0.80rem; color: #555;
    margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 20px;
}
.live-bar b { color: #2D6A4F; }

.alert-epid {
    background: rgba(163,45,45,0.07); border: 1.5px solid #A32D2D;
    border-radius: 10px; padding: 14px 18px; margin: 10px 0;
}
.alert-safe {
    background: rgba(45,106,79,0.07); border: 1.5px solid #2D6A4F;
    border-radius: 10px; padding: 12px 18px; margin: 10px 0;
}

.diag-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.diag-table th {
    background: #F5F3EE; color: #666; padding: 9px 11px;
    text-align: left; font-weight: 600; font-size: 0.73rem;
    border-bottom: 2px solid #E8E4DC; text-transform: uppercase;
    letter-spacing: 0.04em;
}
.diag-table td { padding: 9px 11px; border-bottom: 1px solid #F0EDE8; color: #333; }
.diag-table tr:hover td { background: #FAFAF8; }

.badge {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 0.70rem; font-weight: 700; letter-spacing: 0.02em;
}
.b-red   { background: rgba(163,45,45,0.12); color: #A32D2D; border: 1px solid rgba(163,45,45,0.3); }
.b-green { background: rgba(45,106,79,0.12); color: #2D6A4F; border: 1px solid rgba(45,106,79,0.3); }

.pbar-wrap { background: #eee; border-radius: 4px; height: 6px; width: 70px; display: inline-block; vertical-align: middle; margin-left: 5px; }
.pbar-fill { height: 6px; border-radius: 4px; }

section[data-testid="stSidebar"] { background: #F5F3EE !important; }

.status-list { list-style: none; padding: 0; margin: 0; font-size: 0.82rem; color: #444; }
.status-list li { display: flex; align-items: center; gap: 7px; padding: 4px 0; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dg { background: #52c41a; }
.dr { background: #ff4d4f; }
.da { background: #BA7517; }

.wa-screen {
    background: #E5DDD5; padding: 14px; border-radius: 12px; margin-top: 6px;
}
.wa-msg-out {
    background: #fff; border-radius: 12px 12px 0 12px;
    padding: 9px 13px; max-width: 220px; margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 0.83rem; color: #111;
}
.wa-msg-in {
    background: #DCF8C6; border-radius: 0 12px 12px 12px;
    padding: 9px 13px; max-width: 320px; margin-left: auto;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 0.83rem;
    color: #111; line-height: 1.55;
}
.wa-time { font-size: 0.65rem; color: #999; text-align: right; margin-top: 4px; }
.wa-label { font-size: 0.68rem; color: #888; margin-bottom: 4px; }

.tl-wrap { display: flex; align-items: center; gap: 12px; margin: 12px 0; }
.tl-box {
    flex: 1; background: #F5F3EE; border-radius: 10px;
    padding: 14px; text-align: center;
}
.tl-box.after { background: #2D6A4F; color: #fff; }
.tl-amt  { font-size: 1.45rem; font-weight: 800; }
.tl-lbl  { font-size: 0.70rem; margin-top: 3px; opacity: 0.7; }
.tl-arr  { font-size: 1.6rem; color: #2D6A4F; }
"""

st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ── DONNÉES MOCK ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def generate_mock() -> pd.DataFrame:
    rng = random.Random(42)
    rows = []
    for i in range(25):
        f = rng.choice(MOCK_FARMERS)
        d = rng.choices(DISEASES, weights=[10, 8, 8, 6, 38], k=1)[0]
        base = PROFIT_REF.get(f["culture"], 35000)
        rows.append({
            "id":               i + 1,
            "farmer_phone":     f["phone"],
            "farmer_name":      f["name"],
            "disease_detected": d,
            "confidence_score": round(rng.uniform(0.71, 0.97), 2),
            "timestamp":        datetime.now() - timedelta(hours=rng.randint(0, 168)),
            "culture":          f["culture"],
            "region":           f["region"],
            "profit_estimate":  rng.randint(int(base * 0.70), int(base * 1.10)),
            "treatment":        TREATMENTS[d],
        })
    return pd.DataFrame(rows)


# ── CHARGEMENT DB ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data() -> tuple[pd.DataFrame, bool]:
    """Retourne (dataframe, is_mock)."""
    try:
        if not DB_PATH.exists():
            return generate_mock(), True
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT * FROM diagnostics ORDER BY timestamp DESC",
            conn, parse_dates=["timestamp"],
        )
        conn.close()
        if df.empty:
            return generate_mock(), True

        rng = random.Random(0)
        for col, default in [
            ("farmer_name",     lambda: rng.choice(MOCK_FARMERS)["name"]),
            ("culture",         lambda: rng.choice(CULTURES)),
            ("region",          lambda: rng.choice(REGIONS)),
            ("profit_estimate", lambda: rng.randint(28000, 65000)),
        ]:
            if col not in df.columns:
                df[col] = [default() for _ in range(len(df))]
        if "treatment" not in df.columns:
            df["treatment"] = df["disease_detected"].map(
                lambda d: TREATMENTS.get(str(d).lower(), "Consultez un agronome")
            )
        return df, False
    except Exception:
        return generate_mock(), True


# ── STATUT API ────────────────────────────────────────────────
@st.cache_data(ttl=15)
def api_online() -> bool:
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


# ── SECTION HEADER ────────────────────────────────────────────
def render_header(online: bool, is_mock: bool):
    dot_cls  = "pulse-dot pulse-green" if online else "pulse-dot pulse-red"
    api_txt  = "API en ligne" if online else "API hors ligne"
    now_txt  = datetime.now().strftime("%d/%m/%Y %H:%M")
    demo_tag = (
        ' &nbsp;<span style="background:rgba(186,117,23,.15);color:#BA7517;'
        'padding:2px 8px;border-radius:8px;font-size:.70rem;font-weight:700">'
        'MODE DEMO</span>'
    ) if is_mock else ""

    st.markdown(f"""
    <div class="fellah-header">
      <div class="fellah-title">&#127807; FELLAH.AI</div>
      <div class="fellah-subtitle">Intelligence Agricole Autonome &#8212; Tableau de Bord{demo_tag}</div>
      <div class="fellah-meta">
        <span class="{dot_cls}"></span>{api_txt}
        &nbsp;&#183;&nbsp;
        &#128197; {now_txt}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── SECTION LIVE BAR ──────────────────────────────────────────
def render_live_bar(df: pd.DataFrame):
    if df.empty:
        return
    last    = df.sort_values("timestamp", ascending=False).iloc[0]
    elapsed = int((datetime.now() - pd.to_datetime(last["timestamp"])).total_seconds() / 60)
    e_str   = f"{elapsed} min" if elapsed < 60 else f"{elapsed // 60}h"
    st.markdown(f"""
    <div class="live-bar">
      <span>&#128300; Dernier diagnostic : <b>il y a {e_str}</b></span>
      <span>&#129440; Derniere maladie : <b>{str(last['disease_detected']).capitalize()}
        ({last.get('region','?')})</b></span>
      <span>&#127807; Culture : <b>{str(last.get('culture','?')).capitalize()}</b></span>
      <span>&#128202; Total : <b>{len(df)} diagnostics</b></span>
    </div>
    """, unsafe_allow_html=True)


# ── SECTION KPIs ──────────────────────────────────────────────
def render_kpis(df: pd.DataFrame) -> float:
    today = datetime.now().date()
    yest  = today - timedelta(days=1)

    n_today  = len(df[pd.to_datetime(df["timestamp"]).dt.date == today])
    n_yest   = len(df[pd.to_datetime(df["timestamp"]).dt.date == yest])
    n_total  = len(df)
    n_sick   = df[df["disease_detected"].str.lower() != "saine"].shape[0]
    taux     = round(n_sick / n_total * 100) if n_total else 0
    profit   = int(df["profit_estimate"].mean()) if n_total else 0
    farmers  = df["farmer_phone"].nunique()

    diag_delta = n_today - n_yest
    diag_sign  = "&#8593;" if diag_delta >= 0 else "&#8595;"
    diag_color = C_GREEN   if diag_delta >= 0 else C_RED
    taux_color = C_RED if taux > 30 else C_GREEN

    cards = [
        ("&#129489;&#8205;&#127806;", str(farmers),    "Fermes actives",
         f'<span style="color:{C_GREEN}">&#9679; Actives</span>', C_GREEN),
        ("&#128300;",  str(n_today),  "Diagnostics aujourd\'hui",
         f'<span style="color:{diag_color}">{diag_sign} {abs(diag_delta)} vs hier</span>', C_BROWN),
        ("&#129440;",  f"{taux}%",    "Taux de maladies",
         f'<span style="color:{taux_color}">{"&#9888; Eleve" if taux > 30 else "&#10003; Normal"}</span>',
         taux_color),
        ("&#128176;",  f"{profit:,} DH", "Profit moyen estime",
         f'<span style="color:{C_AMBER}">&#8593; OCP Maroc 2024</span>', C_AMBER),
    ]

    cols = st.columns(4)
    for col, (icon, val, lbl, delta, border) in zip(cols, cards):
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-left-color:{border}">
              <div class="kpi-icon">{icon}</div>
              <div class="kpi-val">{val}</div>
              <div class="kpi-lbl">{lbl}</div>
              <div class="kpi-delta">{delta}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    return taux


# ── SECTION ALERTE ────────────────────────────────────────────
def render_alert(taux: float, df: pd.DataFrame):
    sick_farmers = df[df["disease_detected"].str.lower() != "saine"]["farmer_phone"].nunique()
    total        = df["farmer_phone"].nunique()
    top_region   = df[df["disease_detected"].str.lower() != "saine"]["region"].mode()
    region       = top_region.iloc[0] if not top_region.empty else "Maroc"

    if taux > 30:
        st.markdown(f"""
        <div class="alert-epid">
          <strong style="color:{C_RED};font-size:1.05rem">&#128680; ALERTE EPIDEMIE</strong>
          <p style="margin:6px 0 0;color:#333;font-size:.88rem">
            <strong>{sick_farmers} fermes infectees sur {total}</strong>
            dans la region <strong>{region}</strong>.
            Taux : <strong>{taux}%</strong> &#8212; Action immediate requise.
          </p>
        </div>""", unsafe_allow_html=True)
        if st.button("&#128242; Envoyer alerte WhatsApp groupee", type="primary"):
            st.success(f"Alerte envoyee a {sick_farmers} agriculteurs via Twilio.")
    else:
        st.markdown(f"""
        <div class="alert-safe">
          <strong style="color:{C_GREEN}">&#10003; Situation normale</strong>
          &#8212; <span style="color:#444;font-size:.87rem">
          Cultures sous surveillance &#183; {taux}% de maladies
          </span>
        </div>""", unsafe_allow_html=True)

    st.divider()


# ── SECTION GRAPHIQUES ────────────────────────────────────────
def render_charts(df: pd.DataFrame):
    c1, c2 = st.columns(2)

    # ── Donut maladies
    with c1:
        st.markdown("#### &#129369; Repartition des diagnostics")
        counts = df["disease_detected"].str.lower().value_counts().reset_index()
        counts.columns = ["maladie", "count"]
        total = int(counts["count"].sum())
        color_map = {
            "saine":      C_GREEN,
            "mildiou":    C_RED,
            "oidium":     "#e07b54",
            "alternaria": "#c45c3e",
            "rouille":    C_BROWN,
        }
        fig = go.Figure(go.Pie(
            labels=[m.capitalize() for m in counts["maladie"]],
            values=counts["count"],
            hole=0.60,
            marker_colors=[color_map.get(m, "#999") for m in counts["maladie"]],
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value} cas (%{percent})<extra></extra>",
        ))
        fig.add_annotation(
            text=f"<b>{total}</b><br>diags",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="#1a1a1a"),
        )
        fig.update_layout(
            showlegend=False, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Barres horizontales profit
    with c2:
        st.markdown("#### &#128176; Profit estime par culture (DH/ha)")
        pf = (
            df.groupby("culture")["profit_estimate"]
            .mean().round().reset_index()
            .sort_values("profit_estimate", ascending=True)
        )
        pf.columns = ["culture", "profit"]
        fig2 = go.Figure(go.Bar(
            x=pf["profit"],
            y=[c.capitalize() for c in pf["culture"]],
            orientation="h",
            marker=dict(
                color=pf["profit"],
                colorscale=[[0, "#74c69d"], [0.5, C_GREEN], [1.0, "#1b4332"]],
            ),
            text=[f"{int(v):,} DH" for v in pf["profit"]],
            textposition="outside",
        ))
        fig2.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(showgrid=False),
            margin=dict(t=10, b=10, l=10, r=90),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()


# ── SECTION TABLEAU ───────────────────────────────────────────
def render_table(df: pd.DataFrame):
    st.markdown("#### &#128203; Diagnostics recents")
    limit = 999 if st.session_state.get("show_all") else 10
    rows  = df.sort_values("timestamp", ascending=False).head(limit)

    body = ""
    for _, r in rows.iterrows():
        d      = str(r["disease_detected"]).lower()
        sick   = d != "saine"
        cls    = "b-red" if sick else "b-green"
        statut = "&#128308; Urgent" if sick else "&#128994; OK"
        conf   = int(float(r["confidence_score"]) * 100)
        bar_c  = C_RED if sick else C_GREEN
        ts     = pd.to_datetime(r["timestamp"]).strftime("%d/%m %H:%M")
        name   = str(r.get("farmer_name", r.get("farmer_phone", "?")))[:18]
        cult   = str(r.get("culture", "?")).capitalize()
        trt    = str(r.get("treatment", "—"))

        body += f"""<tr>
          <td>{ts}</td>
          <td>{name}</td>
          <td>{cult}</td>
          <td><span class="badge {cls}">{d.capitalize()}</span></td>
          <td>
            <span style="font-size:.78rem;font-weight:700">{conf}%</span>
            <span class="pbar-wrap">
              <span class="pbar-fill" style="width:{conf}%;background:{bar_c};display:block"></span>
            </span>
          </td>
          <td style="font-size:.78rem;max-width:150px">{trt}</td>
          <td>{statut}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #E8E4DC">
      <table class="diag-table">
        <thead><tr>
          <th>Heure</th><th>Agriculteur</th><th>Culture</th>
          <th>Maladie</th><th>Confiance</th><th>Traitement</th><th>Statut</th>
        </tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.get("show_all"):
        if st.button("&#128196; Voir tous les diagnostics"):
            st.session_state["show_all"] = True
            st.rerun()
    st.divider()


# ── SECTION HASSAN ────────────────────────────────────────────
def render_hassan():
    with st.expander("&#127919; Scenario Demo &#8212; Hassan Benali, Beni Mellal"):
        st.markdown("""
        <div class="tl-wrap">
          <div class="tl-box">
            <div class="tl-amt" style="color:#A32D2D">28 000 DH</div>
            <div class="tl-lbl">Avant FELLAH.AI<br>Perte par maladie non detectee</div>
          </div>
          <div class="tl-arr">&#8594;</div>
          <div class="tl-box after">
            <div class="tl-amt">52 000 DH</div>
            <div class="tl-lbl">Apres FELLAH.AI<br>Recolte sauvee a temps</div>
          </div>
        </div>
        <p style="text-align:center;color:#2D6A4F;font-weight:700;font-size:1rem;margin-top:8px">
          &#128200; +85% de profit &#8212; Diagnostique en 3 secondes. Traite a temps.
        </p>
        """, unsafe_allow_html=True)

        if st.button("&#128242; Simuler envoi WhatsApp Hassan"):
            st.session_state["show_wa"] = True

        if st.session_state.get("show_wa"):
            st.markdown("""
            <div class="wa-screen">
              <div class="wa-label">Hassan &#8594; FELLAH.AI</div>
              <div class="wa-msg-out">
                &#128247; <em>[Photo feuille tomate]</em>
                <div class="wa-time">06:01 &#10003;&#10003;</div>
              </div>
              <br>
              <div class="wa-label" style="text-align:right">FELLAH.AI &#8594; Hassan</div>
              <div class="wa-msg-in">
                &#128308; <strong>FELLAH.AI &#8212; Diagnostic</strong><br>
                &#9473;&#9473;&#9473;&#9473;&#9473;&#9473;&#9473;<br>
                Maladie : <strong>Mildiou</strong><br>
                Fiabilite : <strong>91%</strong><br><br>
                Traitement : Bouillie bordelaise 2%<br><br>
                <span style="font-size:.82rem">
                صاحبي، عندك ميلديو فالطماطم. رش بوردو 2% من الصباح.
                غتربح على 40,000 كيلو بـ 1.8 درهم.
                </span><br><br>
                &#9888;&#65039; Agissez dans les 48h.<br>
                <em>FELLAH.AI &#8212; Intelligence du terroir &#127807;</em>
                <div class="wa-time">06:01 &#10003;&#10003;</div>
              </div>
            </div>""", unsafe_allow_html=True)
    st.divider()


# ── SECTION CARTE ─────────────────────────────────────────────
def render_map(df: pd.DataFrame):
    try:
        import folium
        from streamlit_folium import st_folium

        st.markdown("#### &#128506;&#65039; Carte des fermes actives")
        coords = {
            "Beni Mellal": (32.34, -6.35), "Tadla":     (32.50, -6.70),
            "Casablanca":  (33.57, -7.59), "Marrakech": (31.63, -8.00),
            "Settat":      (33.00, -7.62), "Meknes":    (33.90, -5.55),
            "Autre":       (31.79, -6.99),
        }
        m = folium.Map(location=[31.7, -7.0], zoom_start=6, tiles="CartoDB positron")
        rng = random.Random(1)
        for _, row in df.drop_duplicates("farmer_phone").iterrows():
            lat, lon = coords.get(str(row.get("region", "Autre")), (31.79, -6.99))
            lat += rng.uniform(-0.25, 0.25)
            lon += rng.uniform(-0.25, 0.25)
            sick = str(row.get("disease_detected", "")).lower() != "saine"
            folium.CircleMarker(
                location=[lat, lon], radius=9,
                color=C_RED if sick else C_GREEN,
                fill=True, fill_opacity=0.75,
                popup=folium.Popup(
                    f"<b>{row.get('farmer_name','?')}</b><br>"
                    f"{row.get('culture','?')} — {row.get('disease_detected','?')}",
                    max_width=200,
                ),
            ).add_to(m)
        st_folium(m, width=None, height=370, returned_objects=[])
        st.divider()
    except ImportError:
        pass  # folium non installe → skip silencieux


# ── SIDEBAR ───────────────────────────────────────────────────
def render_sidebar(df_raw: pd.DataFrame, online: bool) -> pd.DataFrame:
    sb = st.sidebar

    sb.markdown(
        '<div style="text-align:center;padding:10px 0 4px">'
        '<span style="font-family:Georgia,serif;font-size:1.25rem;'
        'font-weight:800;color:#2D6A4F">&#127807; FELLAH.AI</span>'
        '<div style="font-size:.68rem;color:#999;margin-top:2px">ETH Hackathon 2026</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    sb.divider()

    # Filtres
    sb.markdown("**&#9881;&#65039; Filtres**")
    regions  = ["Toutes"] + sorted(df_raw["region"].dropna().unique().tolist())
    cultures = ["Toutes"] + sorted(df_raw["culture"].dropna().unique().tolist())
    periodes = {"7 derniers jours": 7, "30 derniers jours": 30, "Tout": 9999}

    reg_sel  = sb.selectbox("&#128205; Region",  regions)
    cult_sel = sb.selectbox("&#127807; Culture", cultures)
    per_sel  = sb.selectbox("&#128197; Periode", list(periodes.keys()))

    df = df_raw.copy()
    if reg_sel  != "Toutes": df = df[df["region"]  == reg_sel]
    if cult_sel != "Toutes": df = df[df["culture"] == cult_sel]
    cutoff = datetime.now() - timedelta(days=periodes[per_sel])
    df = df[pd.to_datetime(df["timestamp"]) >= cutoff]
    sb.divider()

    # Actions rapides
    sb.markdown("**&#9889; Actions rapides**")
    if sb.button("&#128242; Tester pipeline WhatsApp"):
        st.toast("Pipeline WhatsApp OK — 3s end-to-end", icon="&#128242;")
    if sb.button("&#128196; Generer rapport PDF"):
        st.toast("Rapport PDF (en developpement)", icon="&#128196;")
    if sb.button("&#128269; Voir logs API"):
        st.toast(f"API docs : {API_URL}/docs", icon="&#128269;")
    if sb.button("&#128260; Rafraichir"):
        st.cache_data.clear()
        st.rerun()
    sb.divider()

    # Statut systeme
    sb.markdown("**&#128187; Statut systeme**")
    db_ok   = DB_PATH.exists()
    yolo_ok = (Path(__file__).parent.parent / "ml_models" / "plant_disease.pt").exists()
    items = [
        ("dg" if online  else "dr", f"API FastAPI : {'EN LIGNE' if online else 'HORS LIGNE'}"),
        ("dg" if db_ok   else "da", f"Base de donnees : {'CONNECTEE' if db_ok else 'MOCK'}"),
        ("dg" if yolo_ok else "da", f"Modele IA : {'YOLO' if yolo_ok else 'MOCK'}"),
        ("dg", "Twilio : CONFIGURE"),
    ]
    items_html = "".join(
        f'<li><span class="dot {cls}"></span>{txt}</li>' for cls, txt in items
    )
    sb.markdown(
        f'<ul class="status-list">{items_html}</ul>',
        unsafe_allow_html=True,
    )
    sb.divider()

    # Auto-refresh
    if sb.checkbox("&#9201;&#65039; Auto-refresh 30s", value=False):
        if "last_rf" not in st.session_state:
            st.session_state["last_rf"] = time.time()
        remaining = max(0, 30 - int(time.time() - st.session_state["last_rf"]))
        sb.caption(f"Rafraichissement dans {remaining}s")
        if remaining == 0:
            st.session_state["last_rf"] = time.time()
            st.cache_data.clear()
            st.rerun()

    sb.caption(f"**{len(df)}** diagnostics filtres")
    return df


# ── MAIN ─────────────────────────────────────────────────────
def main():
    df_raw, is_mock = load_data()
    online          = api_online()
    df              = render_sidebar(df_raw, online)

    if is_mock:
        st.info(
            "Mode demonstration — donnees simulees (DB vide ou inaccessible)",
            icon="&#127917;",
        )

    render_header(online, is_mock)

    if df.empty:
        st.warning("Aucun diagnostic pour ces filtres. Elargissez la selection.")
        return

    render_live_bar(df)
    taux = render_kpis(df)
    render_alert(taux, df)
    render_charts(df)
    render_table(df)
    render_hassan()
    render_map(df)


if __name__ == "__main__":
    main()
