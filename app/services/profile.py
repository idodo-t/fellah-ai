"""
FELLAH.AI — Farmer Profile Service
Extracts and persists farmer info from conversation text.
Once saved, FELLAH never asks for it again.
"""

import re

# ─── Moroccan region bounding boxes (lat_min, lat_max, lon_min, lon_max) ────
# Most-specific first so first match wins
_REGION_BOXES = [
    ("souss",    29.0, 31.5, -9.8, -7.5),
    ("loukkos",  34.8, 35.5, -6.2, -5.3),
    ("gharb",    33.8, 34.9, -6.5, -5.0),
    ("tadla",    31.8, 33.0, -7.0, -5.5),
    ("doukkala", 32.5, 33.5, -9.0, -7.0),
    ("haouz",    30.5, 32.5, -9.5, -6.5),
    ("moulouya", 33.5, 35.5, -3.5, -1.0),
    ("rif",      34.5, 35.9, -5.5, -2.5),
]


def region_from_coords(lat: float, lon: float) -> str | None:
    """Maps GPS coordinates to a Moroccan agricultural region key."""
    for name, lat_min, lat_max, lon_min, lon_max in _REGION_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    # Inside Morocco but no specific region matched
    if 27.5 <= lat <= 36.0 and -13.5 <= lon <= -1.0:
        return "haouz"
    return None


def update_from_location(lat: float, lon: float, phone: str, db) -> tuple:
    """
    Saves GPS coordinates and derived region to farmer profile.
    Returns (profile, region_name).
    """
    region  = region_from_coords(lat, lon)
    profile = get_or_create(phone, db)
    changed = False
    if profile.latitude is None:
        profile.latitude  = lat
        profile.longitude = lon
        changed = True
    if region and profile.region is None:
        profile.region = region
        changed = True
    if changed:
        db.commit()
        db.refresh(profile)
    return profile, region


# ─── Known values for each field ────────────────────────────────────────────

_REGIONS = {
    "souss": "souss", "agadir": "souss", "inezgane": "souss", "taroudant": "souss",
    "gharb": "gharb", "kenitra": "gharb", "sidi slimane": "gharb", "sidi kacem": "gharb",
    "tadla": "tadla", "beni mellal": "tadla", "fkih ben salah": "tadla",
    "loukkos": "loukkos", "larache": "loukkos",
    "doukkala": "doukkala", "el jadida": "doukkala", "safi": "doukkala",
    "haouz": "haouz", "marrakech": "haouz", "chichaoua": "haouz",
    "moulouya": "moulouya", "berkane": "moulouya", "oujda": "moulouya",
    "oriental": "moulouya", "rif": "rif", "al hoceima": "rif", "nador": "rif",
}

_IRRIGATIONS = {
    "goutte":        "goutte_a_goutte",
    "drip":          "goutte_a_goutte",
    "trickle":       "goutte_a_goutte",
    "aspersion":     "aspersion",
    "sprinkler":     "aspersion",
    "gravitaire":    "gravitaire",
    "submersion":    "gravitaire",
    "inondation":    "gravitaire",
    "bour":          "bour",
    "pluvial":       "bour",
    "sequentiel":    "bour",
    "sans irrigation": "bour",
}

_SOILS = {
    "limoneux":     "limoneux",
    "argileux":     "argileux",
    "argilo":       "argileux",
    "sableux":      "sableux",
    "sable":        "sableux",
    "calcaire":     "calcaire",
    "argilo_limon": "argilo_limon",
    "argilo-limon": "argilo_limon",
}

_CROPS = {
    "tomate": "tomate", "طماطم": "tomate",
    "ble": "ble", "blé": "ble", "قمح": "ble",
    "poivron": "poivron", "فلفل": "poivron",
    "oignon": "oignon", "بصل": "oignon",
    "pomme de terre": "pomme_de_terre", "pomme_de_terre": "pomme_de_terre", "patate": "pomme_de_terre", "بطاطا": "pomme_de_terre",
    "olive": "olive", "زيتون": "olive",
    "orange": "orange", "agrume": "orange", "برتقال": "orange",
    "fraise": "fraise", "فراولة": "fraise",
    "haricot": "haricot_vert", "haricot vert": "haricot_vert",
    "pasteque": "pasteque", "pastèque": "pasteque", "دلاح": "pasteque",
    "courgette": "courgette", "كوسة": "courgette",
    "betterave": "betterave",
}


def extract_updates(text: str) -> dict:
    """
    Scan a text message for any farmer profile info.
    Returns a dict of fields to update (only non-empty findings).
    """
    updates = {}
    text_lower = text.lower().strip()

    # Surface in hectares
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:ha\b|hectares?)", text_lower)
    if m:
        updates["surface_ha"] = float(m.group(1).replace(",", "."))

    # Region
    for keyword, value in _REGIONS.items():
        if keyword in text_lower:
            updates["region"] = value
            break

    # Irrigation
    for keyword, value in _IRRIGATIONS.items():
        if keyword in text_lower:
            updates["irrigation"] = value
            break

    # Soil type
    for keyword, value in _SOILS.items():
        if keyword in text_lower:
            updates["soil_type"] = value
            break

    # Main crop
    for keyword, value in _CROPS.items():
        if keyword in text_lower:
            updates["main_crop"] = value
            break

    return updates


def get_or_create(phone: str, db):
    """Load existing profile or create an empty one."""
    from ..database import FarmerProfile
    profile = db.query(FarmerProfile).filter_by(phone=phone).first()
    if profile is None:
        profile = FarmerProfile(phone=phone)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_from_text(text: str, phone: str, db):
    """Extract profile info from text and persist any new findings."""
    updates = extract_updates(text)
    if not updates:
        return get_or_create(phone, db)

    profile = get_or_create(phone, db)
    changed = False
    for field, value in updates.items():
        if getattr(profile, field, None) is None:   # only fill blanks
            setattr(profile, field, value)
            changed = True
    if changed:
        db.commit()
        db.refresh(profile)
    return profile


def to_prompt_context(profile) -> str:
    """
    Formats the known profile as a compact string for the Gemini system prompt.
    Returns empty string if profile has no data yet.
    """
    if profile is None:
        return ""

    parts = []
    if profile.region:
        parts.append(f"région={profile.region}")
    if profile.surface_ha:
        parts.append(f"surface={profile.surface_ha}ha")
    if profile.irrigation:
        parts.append(f"irrigation={profile.irrigation}")
    if profile.soil_type:
        parts.append(f"sol={profile.soil_type}")
    if profile.main_crop:
        parts.append(f"culture_principale={profile.main_crop}")

    if not parts:
        return ""

    return (
        "\n═══ PROFIL AGRICULTEUR (DÉJÀ ENREGISTRÉ — NE PAS REDEMANDER) ═══\n"
        + ", ".join(parts)
        + "\nUtilise ces données directement dans tes calculs sans les reposer.\n"
    )


def missing_fields(profile) -> list:
    """Returns list of profile fields still unknown."""
    fields = []
    if not profile or not profile.region:
        fields.append("region")
    if not profile or not profile.surface_ha:
        fields.append("surface_ha")
    if not profile or not profile.irrigation:
        fields.append("irrigation")
    if not profile or not profile.soil_type:
        fields.append("soil_type")
    return fields
