"""
FELLAH.AI — Profit Service
Calculs financiers agricoles marocains.

Fonction publique :
  calculate_profit(crop: str, surface_ha: float) -> dict
"""

# ---------------------------------------------------------------------------
# Données métier Maroc 2024
# ---------------------------------------------------------------------------
CROPS = {
    "tomate": {
        "yield_kg_ha":  40_000,
        "price_dh_kg":  1.80,
        "cost_dh_ha":   15_000,
    },
    "ble": {
        "yield_kg_ha":  3_500,
        "price_dh_kg":  3.20,
        "cost_dh_ha":   4_500,
    },
    "poivron": {
        "yield_kg_ha":  28_000,
        "price_dh_kg":  2.50,
        "cost_dh_ha":   18_000,
    },
}

# Aliases pour accepter les variantes de noms
ALIASES = {
    "blé": "ble", "wheat": "ble", "قمح": "ble",
    "tomato": "tomate", "طماطم": "tomate",
    "pepper": "poivron", "فلفل": "poivron",
}


def _normalize(crop: str) -> str:
    """Normalise le nom de la culture (lowercase, alias)."""
    key = crop.lower().strip()
    return ALIASES.get(key, key)


def calculate_profit(crop: str, surface_ha: float) -> dict:
    """
    Calcule le profit net pour une culture donnée.

    Args:
        crop:       Nom de la culture (tomate, ble/blé, poivron)
        surface_ha: Surface en hectares

    Returns:
        {
            "crop":           str,    # nom normalisé
            "surface_ha":     float,
            "revenue_dh":     float,  # chiffre d'affaires brut
            "cost_dh":        float,  # coût total de production
            "profit_dh":      float,  # bénéfice net
            "profit_per_ha":  float,  # bénéfice net par hectare
            "yield_kg":       float,  # production totale en kg
            "roi_pct":        float,  # retour sur investissement (%)
        }

    Garantie : ne lève jamais d'exception — retourne toujours le bon format.
    """
    try:
        key = _normalize(crop)
        data = CROPS.get(key)

        if data is None:
            # Culture inconnue : retour avec valeurs nulles et message
            return {
                "crop":          crop,
                "surface_ha":    surface_ha,
                "revenue_dh":    0.0,
                "cost_dh":       0.0,
                "profit_dh":     0.0,
                "profit_per_ha": 0.0,
                "yield_kg":      0.0,
                "roi_pct":       0.0,
                "error":         f"Culture '{crop}' inconnue. Cultures disponibles : {', '.join(CROPS)}",
            }

        yield_kg   = data["yield_kg_ha"]  * surface_ha
        revenue_dh = yield_kg             * data["price_dh_kg"]
        cost_dh    = data["cost_dh_ha"]   * surface_ha
        profit_dh  = revenue_dh - cost_dh
        roi_pct    = (profit_dh / cost_dh * 100) if cost_dh > 0 else 0.0

        return {
            "crop":          key,
            "surface_ha":    surface_ha,
            "revenue_dh":    round(revenue_dh, 2),
            "cost_dh":       round(cost_dh, 2),
            "profit_dh":     round(profit_dh, 2),
            "profit_per_ha": round(profit_dh / surface_ha, 2) if surface_ha > 0 else 0.0,
            "yield_kg":      round(yield_kg, 2),
            "roi_pct":       round(roi_pct, 1),
        }

    except Exception as exc:
        return {
            "crop":          crop,
            "surface_ha":    surface_ha,
            "revenue_dh":    0.0,
            "cost_dh":       0.0,
            "profit_dh":     0.0,
            "profit_per_ha": 0.0,
            "yield_kg":      0.0,
            "roi_pct":       0.0,
            "error":         str(exc),
        }