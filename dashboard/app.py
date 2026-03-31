"""
FELLAH.AI — Dashboard Streamlit
Tableau de bord en temps réel pour le suivi agricole marocain.

Lancer avec : streamlit run dashboard/app.py
"""

# ============================================================
# 1. IMPORTS + CONFIGURATION PAGE
# ============================================================
import os
import sys
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Auto-refresh (optionnel)
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
    AUTO_REFRESH = True
except ImportError:
    AUTO_REFRESH = False

st.set_page_config(
    page_title="FELLAH.AI Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Chemin vers la DB (remonte d'un niveau depuis dashboard/)
DB_PATH   = Path(__file__).parent.parent / "fellah_ai.db"
API_URL   = os.getenv("API_URL", "http://localhost:8000")

# Couleurs FELLAH.AI
C_GREEN   = "#2D6A4F"
C_RED     = "#A32D2D"
C_BROWN   = "#7C3A1E"
C_YELLOW  = "#D4A017"
C_LIGHT   = "#F0F4EF"

DISEASES  = ["mildiou", "oidium", "alternaria", "rouille", "saine"]
CULTURES  = ["tomate", "ble", "poivron", "oignon"]
REGIONS   = ["Beni Mellal", "Tadla", "Casablanca", "Marrakech", "Autre"]

# ============================================================
# 2. CSS CUSTOM
# ============================================================
st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border-left: 4px solid #2D6A4F;
        margin: 4px;
    }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #74c69d; }
    .kpi-label { font-size: 0.85rem; color: #aaa; margin-top: 4px; }
    .alert-red {
        background-color: #A32D2D22;
        border: 2px solid #A32D2D;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .alert-green {
        background-color: #2D6A4F22;
        border: 2px solid #2D6A4F;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: 900;
        color: #2D6A4F;
    }
    .status-dot-green { color: #2D6A4F; font-size: 1.1rem; }
    .status-dot-red   { color: #A32D2D; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. DONNÉES MOCK
# ============================================================
def generate_mock_data() -> pd.DataFrame:
    """Génère 25 diagnostics réalistes si la DB est vide."""
    random.seed(42)
    phones = [f"+2126{random.randint(10000000,99999999)}" for _ in range(12)]
    records = []
    for i in range(25):
        disease = random.choices(
            DISEASES,
            weights=[10, 8, 8, 6, 38],  # 60% saine, 40% maladies
            k=1
        )[0]
        records.append({
            "id":               i + 1,
            "farmer_phone":     random.choice(phones),
            "disease_detected": disease,
            "confidence_score": round(random.uniform(0.71, 0.97), 2),
            "timestamp":        datetime.now() - timedelta(
                                    hours=random.randint(0, 168)
                                ),
            "culture":          random.choice(CULTURES),
            "region":           random.choice(REGIONS),
            "profit_estimate":  round(random.uniform(28000, 65000)),
            "treatment":        {
                "mildiou":    "Bouillie bordelaise 2%",
                "oidium":     "Soufre mouillable",
                "alternaria": "Chlorothalonil",
                "rouille":    "Triazole",
                "saine":      "RAS",
            }[disease],
        })
    return pd.DataFrame(records)


# ============================================================
# 4. CONNEXION DB
# ============================================================
def load_db_data() -> pd.DataFrame:
    """Charge les diagnostics depuis SQLite. Retourne mock si vide/erreur."""
    try:
        if not DB_PATH.exists():
            return generate_mock_data()

        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT * FROM diagnostics ORDER BY timestamp DESC",
            conn,
            parse_dates=["timestamp"],
        )
        conn.close()

        if df.empty:
            return generate_mock_data()

        # Harmonise les noms de colonnes avec le reste du code
        df = df.rename(columns={
            "disease_detected": "disease_detected",
            "confidence_score": "confidence_score",
        })

        # Colonnes optionnelles absentes de la vraie DB → on les simule
        if "culture" not in df.columns:
            random.seed(0)
            df["culture"] = [random.choice(CULTURES) for _ in range(len(df))]
        if "region" not in df.columns:
            df["region"] = "Autre"
        if "profit_estimate" not in df.columns:
            df["profit_estimate"] = [random.randint(28000, 65000) for _ in range(len(df))]
        if "treatment" not in df.columns:
            mapping = {
                "mildiou": "Bouillie bordelaise 2%", "oidium": "Soufre mouillable",
                "alternaria": "Chlorothalonil", "rouille": "Triazole", "saine": "RAS",
            }
            df["treatment"] = df["disease_detected"].map(
                lambda d: mapping.get(str(d).lower(), "Consultez un agronome")
            )

        return df

    except Exception as e:
        st.sidebar.warning(f"DB inaccessible → données mock ({e})")
        return generate_mock_data()


# ============================================================
# 5. STATUT API
# ============================================================
def check_api_status() -> bool:
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ============================================================
# 6. COMPOSANTS UI
# ============================================================

def render_header(api_online: bool):
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown('<div class="header-title">🌿 FELLAH.AI</div>', unsafe_allow_html=True)
        st.markdown("**Intelligence Agricole Autonome — Tableau de Bord**")
    with col2:
        if api_online:
            st.markdown(
                '<div class="status-dot-green">🟢 API en ligne</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="status-dot-red">🔴 API hors ligne</div>',
                unsafe_allow_html=True
            )
    st.divider()


def render_kpis(df: pd.DataFrame):
    today = datetime.now().date()
    df_today = df[pd.to_datetime(df["timestamp"]).dt.date == today]

    total_farmers    = df["farmer_phone"].nunique()
    diags_today      = len(df_today)
    total_diags      = len(df)
    maladies_count   = df[df["disease_detected"].str.lower() != "saine"].shape[0]
    taux_maladie     = round(maladies_count / total_diags * 100) if total_diags > 0 else 0
    profit_moyen     = int(df["profit_estimate"].mean()) if "profit_estimate" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">🧑‍🌾 {total_farmers}</div>
            <div class="kpi-label">Fermes actives</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">🔬 {diags_today}</div>
            <div class="kpi-label">Diagnostics aujourd'hui</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        color = "#e63946" if taux_maladie > 30 else "#74c69d"
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color:{color}">
            <div class="kpi-value" style="color:{color}">🦠 {taux_maladie}%</div>
            <div class="kpi-label">Taux de maladies détectées</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">💰 {profit_moyen:,}</div>
            <div class="kpi-label">Profit moyen estimé (DH)</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    return taux_maladie


def render_alert(taux_maladie: float, df: pd.DataFrame):
    fermes_malades = df[df["disease_detected"].str.lower() != "saine"]["farmer_phone"].nunique()
    total_fermes   = df["farmer_phone"].nunique()

    if taux_maladie > 30:
        st.markdown(f"""
        <div class="alert-red">
            <h2>🚨 ALERTE ÉPIDÉMIE</h2>
            <p><b>{fermes_malades} fermes sur {total_fermes}</b> présentent des maladies actives.
            Taux de contamination : <b>{taux_maladie}%</b> — Action immédiate requise !</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-green">
            <h2>✅ CULTURES SAINES</h2>
            <p>Seulement <b>{fermes_malades} fermes</b> présentent des anomalies.
            Taux de contamination : <b>{taux_maladie}%</b> — Situation sous contrôle.</p>
        </div>""", unsafe_allow_html=True)
    st.divider()


def render_charts(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    # --- Graphique 1 : Distribution des maladies ---
    with col1:
        st.subheader("🦠 Distribution des maladies")
        disease_counts = (
            df["disease_detected"]
            .str.lower()
            .value_counts()
            .reset_index()
        )
        disease_counts.columns = ["maladie", "count"]
        colors = [C_GREEN if m == "saine" else C_RED for m in disease_counts["maladie"]]

        fig1 = px.bar(
            disease_counts,
            x="maladie", y="count",
            color="maladie",
            color_discrete_map={
                "saine":      C_GREEN,
                "mildiou":    C_RED,
                "oidium":     "#e07b54",
                "alternaria": "#c45c3e",
                "rouille":    C_BROWN,
            },
            labels={"maladie": "Maladie", "count": "Nombre"},
        )
        fig1.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Graphique 2 : Profit moyen par culture ---
    with col2:
        st.subheader("💰 Profit moyen par culture (DH)")
        profit_culture = (
            df.groupby("culture")["profit_estimate"]
            .mean()
            .round()
            .reset_index()
        )
        profit_culture.columns = ["culture", "profit_moyen"]

        fig2 = px.bar(
            profit_culture,
            x="culture", y="profit_moyen",
            color="culture",
            color_discrete_sequence=[C_GREEN, C_BROWN, C_YELLOW, "#4a7c59"],
            labels={"culture": "Culture", "profit_moyen": "Profit moyen (DH)"},
            text="profit_moyen",
        )
        fig2.update_traces(texttemplate="%{text:,.0f} DH", textposition="outside")
        fig2.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()


def render_table(df: pd.DataFrame):
    st.subheader("📋 Diagnostics récents")

    display = (
        df.sort_values("timestamp", ascending=False)
        .head(10)
        [[
            "timestamp", "farmer_phone", "culture",
            "disease_detected", "confidence_score", "treatment"
        ]]
        .copy()
    )

    display["timestamp"]       = pd.to_datetime(display["timestamp"]).dt.strftime("%d/%m %H:%M")
    display["confidence_score"] = (display["confidence_score"] * 100).round(1).astype(str) + "%"
    display.columns = ["Date/Heure", "Agriculteur", "Culture", "Maladie", "Confiance", "Traitement"]

    def color_row(row):
        color = "#A32D2D33" if row["Maladie"].lower() != "saine" else "#2D6A4F33"
        return [f"background-color: {color}"] * len(row)

    styled = display.style.apply(color_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.divider()


def render_map(df: pd.DataFrame):
    try:
        import folium  # type: ignore
        from streamlit_folium import st_folium  # type: ignore

        st.subheader("🗺️ Carte des fermes — Maroc")

        region_coords = {
            "Beni Mellal": (32.34, -6.35),
            "Tadla":       (32.50, -6.70),
            "Casablanca":  (33.57, -7.59),
            "Marrakech":   (31.63, -8.00),
            "Autre":       (31.79 + random.uniform(-1, 1), -6.99 + random.uniform(-1, 1)),
        }

        m = folium.Map(location=[31.7, -7.0], zoom_start=6)
        for _, row in df.drop_duplicates("farmer_phone").iterrows():
            lat, lon = region_coords.get(row.get("region", "Autre"), (31.79, -6.99))
            lat += random.uniform(-0.3, 0.3)
            lon += random.uniform(-0.3, 0.3)
            is_sick = str(row.get("disease_detected", "")).lower() != "saine"
            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                color=C_RED if is_sick else C_GREEN,
                fill=True,
                fill_opacity=0.8,
                popup=f"{row['farmer_phone']} — {row.get('disease_detected', '?')}",
            ).add_to(m)

        st_folium(m, width=700, height=400)
        st.divider()

    except ImportError:
        pass  # folium non installé → on skip silencieusement


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("## ⚙️ Filtres")

    regions  = ["Toutes"] + sorted(df["region"].dropna().unique().tolist())
    cultures = ["Toutes"] + sorted(df["culture"].dropna().unique().tolist())

    region_sel  = st.sidebar.selectbox("📍 Région", regions)
    culture_sel = st.sidebar.selectbox("🌱 Culture", cultures)

    if region_sel != "Toutes":
        df = df[df["region"] == region_sel]
    if culture_sel != "Toutes":
        df = df[df["culture"] == culture_sel]

    st.sidebar.divider()
    if st.sidebar.button("🔄 Rafraîchir les données"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown(f"[📄 Documentation API]({API_URL}/docs)")
    st.sidebar.divider()
    st.sidebar.markdown(f"**{len(df)}** diagnostics filtrés")
    st.sidebar.caption("FELLAH.AI · ETH Hackathon 2026")

    return df


# ============================================================
# 7. MAIN
# ============================================================
def main():
    # Auto-refresh toutes les 30 secondes
    if AUTO_REFRESH:
        st_autorefresh(interval=30_000, key="fellah_refresh")

    # Chargement des données
    df_raw = load_db_data()

    # Sidebar (renvoie df filtré)
    df = render_sidebar(df_raw)

    # Header
    api_online = check_api_status()
    render_header(api_online)

    if df.empty:
        st.warning("Aucun diagnostic trouvé pour ces filtres.")
        return

    # KPIs
    taux_maladie = render_kpis(df)

    # Alerte épidémie
    render_alert(taux_maladie, df)

    # Graphiques
    render_charts(df)

    # Tableau
    render_table(df)

    # Carte (si folium dispo)
    render_map(df)


if __name__ == "__main__":
    main()
