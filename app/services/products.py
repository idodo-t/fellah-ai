"""
FELLAH.AI — Product Catalog
Maps detected diseases to recommended treatment products available in Morocco.
"""

CATALOG: dict[str, dict] = {
    "mildiou": {
        "name": "Bouillie Bordelaise WG",
        "dose": "20g par litre d'eau — appliquer tôt le matin",
        "price_range": "45–80 DH / kg",
        "search_url": "https://www.google.com/search?q=bouillie+bordelaise+maroc+prix+achat",
    },
    "oidium": {
        "name": "Soufre Mouillable 80%",
        "dose": "3g par litre d'eau — éviter la chaleur (+30°C)",
        "price_range": "30–60 DH / kg",
        "search_url": "https://www.google.com/search?q=soufre+mouillable+fongicide+maroc+prix",
    },
    "alternaria": {
        "name": "Chlorothalonil 75%",
        "dose": "2g par litre d'eau — traitement toutes les 2 semaines",
        "price_range": "70–120 DH / kg",
        "search_url": "https://www.google.com/search?q=chlorothalonil+fongicide+maroc+achat",
    },
    "rouille": {
        "name": "Tébuconazole (Triazole)",
        "dose": "1 application curative suffit — 1ml par litre",
        "price_range": "80–150 DH / L",
        "search_url": "https://www.google.com/search?q=tebuconazole+fongicide+maroc+prix",
    },
}


def get_product(disease: str) -> dict | None:
    """Returns product info for a disease, or None if plant is healthy/unknown."""
    return CATALOG.get(disease.lower().strip())


def format_product_message(disease: str) -> str | None:
    """Returns a formatted WhatsApp product recommendation, or None if not applicable."""
    product = get_product(disease)
    if not product:
        return None
    return (
        f"🛒 *Produit recommandé :*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🧴 *{product['name']}*\n"
        f"💊 Dose : {product['dose']}\n"
        f"💰 Prix estimé : {product['price_range']}\n\n"
        f"🔗 Trouver en ligne : {product['search_url']}"
    )
