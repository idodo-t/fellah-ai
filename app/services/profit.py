"""
FELLAH.AI — Profit Service
Calculs financiers agricoles marocains avec type de sol.

Fonction publique :
  calcul_profit(culture, surface_ha, type_sol) -> dict
"""

SOL = {"argileux": 1.20, "sableux": 0.85, "limoneux": 1.10, "autre": 1.00}

OCP = {
    "tomate":  {"r": 40000, "p": 1.80, "c": 15000, "risk": 0.15},
    "ble":     {"r":  3500, "p": 3.20, "c":  4500, "risk": 0.10},
    "poivron": {"r": 28000, "p": 2.50, "c": 18000, "risk": 0.22},
    "oignon":  {"r": 35000, "p": 1.20, "c":  8000, "risk": 0.12},
}


def calcul_profit(culture: str, surface_ha: float, type_sol: str = "autre") -> dict:
    """
    Calcule le profit net pour une culture donnée avec facteur sol.

    Args:
        culture:    Nom de la culture (tomate, ble, poivron, oignon)
        surface_ha: Surface en hectares
        type_sol:   Type de sol (argileux, sableux, limoneux, autre)

    Returns:
        {
            "culture", "surface_ha", "type_sol",
            "sol_multiplier", "revenu_brut",
            "cout_total", "profit_net",
            "alerte_j18", "meilleur_choix"
        }

    Garantie : ne lève jamais d'exception.
    """
    try:
        d = OCP.get(culture.lower(), OCP["ble"])
        m = SOL.get(type_sol.lower(), 1.0)

        revenu = d["r"] * surface_ha * d["p"] * m
        cout   = d["c"] * surface_ha
        profit = (revenu - cout) * (1 - d["risk"])

        return {
            "culture":        culture,
            "surface_ha":     surface_ha,
            "type_sol":       type_sol,
            "sol_multiplier": m,
            "revenu_brut":    round(revenu),
            "cout_total":     round(cout),
            "profit_net":     round(profit),
            "alerte_j18":     round(cout * 0.30),
            "meilleur_choix": profit > 30000,
        }

    except Exception as exc:
        return {
            "culture":        culture,
            "surface_ha":     surface_ha,
            "type_sol":       type_sol,
            "sol_multiplier": 1.0,
            "revenu_brut":    0,
            "cout_total":     0,
            "profit_net":     0,
            "alerte_j18":     0,
            "meilleur_choix": False,
            "error":          str(exc),
        }


# Alias pour compatibilité avec l'ancienne signature
def calculate_profit(crop: str, surface_ha: float) -> dict:
    return calcul_profit(crop, surface_ha)
