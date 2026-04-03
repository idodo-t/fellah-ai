"""
FELLAH.AI — Crop Recommender
Answers: "What should I plant THIS MONTH?"

Logic:
  1. Filter crops whose planting window includes the current month
  2. Rank by net profit using the farmer's actual profile (region/soil/irrigation)
  3. Return TOP 3 with formatted summary
"""

from datetime import datetime
from .profit import calcul_profit, CULTURES_DB

# ─── Planting windows (months when you sow/transplant) ──────────────────────
PLANTING_MONTHS: dict[str, list[int]] = {
    "tomate":          [8, 9, 10],
    "ble":             [11, 12],
    "poivron":         [2, 3, 8, 9],
    "oignon":          [10, 11],
    "pomme_de_terre":  [1, 2, 9, 10],
    "olive":           [12, 1, 2],
    "orange":          [3, 4, 5],
    "fraise":          [9, 10],
    "haricot_vert":    [3, 4, 10, 11],
    "pasteque":        [2, 3, 4],
    "courgette":       [2, 3, 8, 9],
    "betterave":       [10, 11],
}

_EMOJI = {
    "tomate": "🍅", "ble": "🌾", "poivron": "🌶️", "oignon": "🧅",
    "pomme_de_terre": "🥔", "olive": "🫒", "orange": "🍊", "fraise": "🍓",
    "haricot_vert": "🌿", "pasteque": "🍉", "courgette": "🥒", "betterave": "🌱",
}


def recommend(
    region: str = "haouz",
    surface_ha: float = 1.0,
    soil_type: str = "limoneux",
    irrigation: str = "goutte_a_goutte",
    top_n: int = 3,
    month: int | None = None,
) -> list[dict]:
    """
    Returns top_n crops to plant this month, ranked by net profit.
    Pass month=X to override current month (useful for testing).
    """
    current_month = month or datetime.now().month

    results = []
    for crop in CULTURES_DB:
        if current_month not in PLANTING_MONTHS.get(crop, []):
            continue
        p = calcul_profit(crop, surface_ha, soil_type, region, irrigation)
        if "error" in p:
            continue
        results.append({
            "crop":       crop,
            "emoji":      _EMOJI.get(crop, "🌱"),
            "profit_net": p["profit_net"],
            "roi_pct":    p["roi_pct"],
            "revenu_brut":p["revenu_brut"],
            "cout_total": p["cout_total"],
            "saison":     p.get("saison", {}),
            "conseil":    p.get("conseil", ""),
            "meilleur_mois_vente": p.get("meilleur_mois_vente", ""),
        })

    results.sort(key=lambda x: x["profit_net"], reverse=True)
    return results[:top_n]


def to_prompt_context(
    region: str = "haouz",
    surface_ha: float = 1.0,
    soil_type: str = "limoneux",
    irrigation: str = "goutte_a_goutte",
) -> str:
    """
    Formatted string to inject into the Gemini system prompt.
    Empty string if no crops are plantable this month.
    """
    recs = recommend(region, surface_ha, soil_type, irrigation)
    if not recs:
        return ""

    month_name = datetime(2000, datetime.now().month, 1).strftime("%B")
    lines = [
        f"\n═══ TOP CULTURES À PLANTER CE MOIS ({month_name.upper()}) "
        f"— basé sur profil ({region}, {surface_ha}ha, {irrigation}) ═══"
    ]
    for i, r in enumerate(recs, 1):
        lines.append(
            f"{i}. {r['emoji']} {r['crop'].upper()} "
            f"→ Profit estimé: {r['profit_net']:,} DH "
            f"| ROI: {r['roi_pct']}% "
            f"| Vente idéale: {r['meilleur_mois_vente']}"
        )
    lines.append(
        "Quand le fermier demande quoi planter, propose ces cultures EN PREMIER "
        "avec leurs chiffres exacts.\n"
    )
    return "\n".join(lines)
