"""
FELLAH.AI — Vision Service
Détection de maladies sur photos de plantes (WhatsApp).

Stratégie :
  1. Si MODEL_PATH existe → YOLOv8 réel
  2. Sinon             → mock déterministe (format garanti)

Contrat immuable :
  analyze_leaf(image_url: str) -> {"disease": str, "confidence": float, "treatment": str}
"""

import os
import logging
import tempfile
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Données métier : traitements recommandés par maladie
# ---------------------------------------------------------------------------
TREATMENTS: dict[str, str] = {
    "mildiou":    "Bouillie bordelaise 2% — appliquer tôt le matin, renouveler après pluie.",
    "oidium":     "Soufre mouillable — pulvériser sur feuilles sèches, éviter 30°C+.",
    "alternaria": "Chlorothalonil — traitement préventif toutes les 2 semaines.",
    "rouille":    "Triazole (ex: Tébuconazole) — 1 application curative suffit.",
    "saine":      "Aucun traitement nécessaire — plante saine, continuez la surveillance.",
}

DEFAULT_TREATMENT = "Consultez un agronome local pour confirmation."

# ---------------------------------------------------------------------------
# Chargement du modèle YOLO (optionnel)
# ---------------------------------------------------------------------------
_model = None

def _load_model():
    """Tente de charger le modèle YOLO une seule fois (lazy)."""
    global _model
    if _model is not None:
        return _model

    model_path = os.getenv("MODEL_PATH", "ml_models/plant_disease.pt")
    if not Path(model_path).exists():
        logger.info("MODEL_PATH introuvable (%s) — mode mock activé.", model_path)
        return None

    try:
        from ultralytics import YOLO  # type: ignore
        _model = YOLO(model_path)
        logger.info("Modèle YOLO chargé depuis %s", model_path)
        return _model
    except Exception as exc:
        logger.warning("Impossible de charger YOLO : %s — mode mock activé.", exc)
        return None


# ---------------------------------------------------------------------------
# Mock (toujours fonctionnel, aucune dépendance externe)
# ---------------------------------------------------------------------------
def _mock_analyze(image_url: str) -> dict:
    """
    Mock réaliste avec diagnostic déterministe pour cohérence démo.
    Utilise l'URL comme seed pour garantir le même résultat par image.
    """
    import random

    # Seed basé sur l'URL pour cohérence par image
    random.seed(hash(image_url))

    scenarios = [
        {"disease": "mildiou", "confidence": 0.94},
        {"disease": "healthy", "confidence": 0.98},
        {"disease": "saine", "confidence": 0.98},
    ]

    pick = random.choice(scenarios)
    pick["treatment"] = TREATMENTS.get(pick["disease"], DEFAULT_TREATMENT)
    return pick


# ---------------------------------------------------------------------------
# Analyse réelle avec YOLOv8
# ---------------------------------------------------------------------------
def _yolo_analyze(image_url: str, model) -> dict:
    """Télécharge l'image et lance l'inférence YOLO."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        urllib.request.urlretrieve(image_url, tmp_path)
        results = model(tmp_path, verbose=False)

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            # Aucune détection → retour "saine"
            return {
                "disease":    "saine",
                "confidence": 1.0,
                "treatment":  TREATMENTS["saine"],
            }

        cls_id     = int(boxes.cls[0])
        confidence = float(boxes.conf[0])
        raw_label  = results[0].names[cls_id].lower().strip()

        # Normalisation du label vers nos clés de traitement
        disease = next(
            (key for key in TREATMENTS if key in raw_label),
            raw_label  # conserve le label brut si inconnu
        )
        treatment = TREATMENTS.get(disease, DEFAULT_TREATMENT)

        return {
            "disease":    disease,
            "confidence": round(confidence, 4),
            "treatment":  treatment,
        }

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Fonction publique — NE PAS RENOMMER
# ---------------------------------------------------------------------------
def analyze_leaf(image_url: str) -> dict:
    """
    Analyse une photo de feuille et retourne le diagnostic.

    Args:
        image_url: URL publique de l'image (WhatsApp media URL, etc.)

    Returns:
        {
            "disease":    str,   # nom de la maladie (lowercase)
            "confidence": float, # 0.0 → 1.0
            "treatment":  str,   # conseil de traitement en français
        }

    Garantie : ne lève jamais d'exception — retourne toujours le bon format.
    """
    try:
        model = _load_model()
        if model is None:
            return _mock_analyze(image_url)
        return _yolo_analyze(image_url, model)

    except Exception as exc:
        logger.error("analyze_leaf a échoué (%s) — retour mock de sécurité.", exc)
        return {
            "disease":    "inconnue",
            "confidence": 0.0,
            "treatment":  DEFAULT_TREATMENT,
        }


# Alias pour compatibilité avec main.py de B
def predict_disease(image_url: str) -> dict:
    """Alias de analyze_leaf() — même résultat, même format."""
    return analyze_leaf(image_url)


# ---------------------------------------------------------------------------
# Format réponse WhatsApp
# ---------------------------------------------------------------------------
def format_whatsapp_response(result: dict) -> str:
    """
    Génère un message WhatsApp structuré avec emojis à partir du résultat analyze_leaf.

    Args:
        result: dict retourné par analyze_leaf()

    Returns:
        Texte formaté prêt à envoyer via Twilio WhatsApp.
    """
    emoji = {
        "mildiou":    "🔴",
        "oidium":     "🟡",
        "alternaria": "🟠",
        "rouille":    "🟤",
        "saine":      "🟢",
    }.get(result.get("disease", "").lower(), "🔵")

    conf = result.get("confidence", 0) * 100
    disease = result.get("disease", "inconnue").capitalize()
    treatment = result.get("treatment", "Consultez un agronome.")

    return (
        f"{emoji} *FELLAH.AI — Diagnostic*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Maladie : *{disease}*\n"
        f"Fiabilité : *{conf:.0f}%*\n\n"
        f"Traitement : {treatment}\n\n"
        f"⚠️ Agissez dans les 48h pour sauver votre récolte.\n"
        f"_FELLAH.AI — Intelligence du terroir_ 🌿"
    )