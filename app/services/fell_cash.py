"""
FELLAH.AI — Fell-Cash Service
Prévision de trésorerie sur 8 semaines + alerte J-18.

Fonction publique :
  prevision_cash(culture, surface_ha, type_sol) -> dict
"""

from app.services.profit import calcul_profit


def prevision_cash(culture: str, surface_ha: float, type_sol: str = "autre") -> dict:
    """
    Génère une timeline de trésorerie sur 8 semaines et l'alerte J-18.

    Args:
        culture:    Nom de la culture
        surface_ha: Surface en hectares
        type_sol:   Type de sol

    Returns:
        {
            "culture", "surface_ha",
            "profit_net",       # profit final estimé
            "alerte_j18",       # montant à prévoir à J-18
            "timeline":         # liste 8 semaines {semaine, flux_dh, cumul_dh}
            "message_darija",   # conseil trésorerie en Darija
        }
    """
    try:
        p = calcul_profit(culture, surface_ha, type_sol)
        cout   = p["cout_total"]
        revenu = p["revenu_brut"]
        profit = p["profit_net"]

        # Répartition des coûts sur 8 semaines (courbe S typique agricole)
        cost_weights = [0.20, 0.20, 0.15, 0.10, 0.10, 0.10, 0.10, 0.05]
        # Revenus concentrés en fin de cycle (semaines 7-8)
        revenue_weights = [0.00, 0.00, 0.00, 0.00, 0.05, 0.10, 0.40, 0.45]

        timeline = []
        cumul = 0
        for i, (cw, rw) in enumerate(zip(cost_weights, revenue_weights)):
            flux = round(revenu * rw - cout * cw)
            cumul += flux
            timeline.append({
                "semaine":  i + 1,
                "flux_dh":  flux,
                "cumul_dh": cumul,
            })

        # Message Darija selon situation
        if profit > 50000:
            msg = "محصولك غيجيب ربح مزيان! خلي عندك الفلوس ديال الجوج شهور الأوائل."
        elif profit > 20000:
            msg = "الحساب مقبول. احرص على الدواء فالأسبوع 3 و4 باش تحمي المحصول."
        else:
            msg = "الربح خفيف. فكر تزيد في السطح أو تبدل النوع للموسم الجاي."

        return {
            "culture":       culture,
            "surface_ha":    surface_ha,
            "profit_net":    profit,
            "alerte_j18":    p["alerte_j18"],
            "timeline":      timeline,
            "message_darija": msg,
        }

    except Exception as exc:
        return {
            "culture":        culture,
            "surface_ha":     surface_ha,
            "profit_net":     0,
            "alerte_j18":     0,
            "timeline":       [],
            "message_darija": "عندنا مشكل تقني، عاود من بعد.",
            "error":          str(exc),
        }
