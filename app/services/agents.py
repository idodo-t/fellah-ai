"""
FELLAH.AI — Multi-Agent Orchestration
══════════════════════════════════════
5 specialized sub-agents, each with a focused contract:

  VisionAgent   → image → disease diagnosis       (Gemini vision, tiny prompt)
  ProfitAgent   → crop/surface → profit numbers   (pure Python, zero latency)
  CropAgent     → profile → top 3 crops this month (pure Python, zero latency)
  DiseaseAgent  → text disease question → advice  (Gemini, focused prompt)
  GeneralAgent  → everything else + audio          (Gemini, full conversation)

Orchestrator detects intent with regex (no extra LLM call),
routes to the right agent, updates farmer profile + history, returns reply.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()

# ── Shared Gemini client ─────────────────────────────────────────────────────

def _client():
    from google import genai
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

def _types():
    from google.genai import types
    return types

# ── Language detection ───────────────────────────────────────────────────────

_DARIJA_LATIN = {
    "wach","dyali","kayn","machi","bghit","3end","nta","rani","dyal","aji",
    "sift","bach","ndir","kifach","daba","sahbi","zri3","fin","ghir","khouya",
    "nti","hna","kima","bzzaf","chhal","zwina","mzyan","chwiya","3la","fhamt",
}

def _lang(text: str) -> str:
    if not text:
        return "darija_arabic"
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    if arabic > len(text) * 0.15:
        return "darija_arabic"
    lowered = text.lower()
    if any(m in lowered.split() or f" {m} " in f" {lowered} " for m in _DARIJA_LATIN):
        return "darija_latin"
    return "french"

# ── Intent detection (regex, no LLM call) ───────────────────────────────────

_INTENTS = {
    "profit": re.compile(
        r"profit|revenu|calcul|rentab|gagner|ربح|حساب|combien.*gagne|kch7al.*trb7|nhseb|l7isab",
        re.I,
    ),
    "crop_rec": re.compile(
        r"quoi planter|what.*plant|quelle culture|ach nzra3|recommand|"
        r"meilleur.*culture|هذا الشهر|had sh-har|had char|ach nzra",
        re.I,
    ),
    "disease": re.compile(
        r"maladie|traitement|tache|bqe3|دواء|علاج|fongicide|pesticide|"
        r"oidium|mildiou|alternaria|rouille|mouche|puceron|insecte|champignon",
        re.I,
    ),
}

def _intent(text: str, has_image: bool, has_audio: bool) -> str:
    if has_image:
        return "vision"
    if has_audio:
        return "general"      # audio → GeneralAgent (Gemini handles audio natively)
    for name, pattern in _INTENTS.items():
        if pattern.search(text or ""):
            return name
    return "general"

# ── Crop name extractor (shared helper) ─────────────────────────────────────

_CROP_MAP = {
    "tomate":"tomate","طماطم":"tomate","ble":"ble","blé":"ble","قمح":"ble",
    "poivron":"poivron","فلفل":"poivron","oignon":"oignon","بصل":"oignon",
    "pomme de terre":"pomme_de_terre","patate":"pomme_de_terre","بطاطا":"pomme_de_terre",
    "olive":"olive","زيتون":"olive","orange":"orange","برتقال":"orange",
    "fraise":"fraise","فراولة":"fraise","haricot":"haricot_vert",
    "pasteque":"pasteque","pastèque":"pasteque","دلاح":"pasteque",
    "courgette":"courgette","كوسة":"courgette","betterave":"betterave",
}

def _crop(text: str) -> str | None:
    t = text.lower()
    for kw, name in _CROP_MAP.items():
        if kw in t:
            return name
    return None

# ════════════════════════════════════════════════════════════════════════════
# 1. VisionAgent — plant disease from image
#    Contract: (image_bytes, mime, text) → dict {disease, confidence, treatment}
# ════════════════════════════════════════════════════════════════════════════

_VISION_PROMPT = """You are FELLAH-Vision, a plant pathology expert AI.
Analyze the plant photo. Return ONLY valid JSON (no markdown, no extra text):
{"disease":"<value>","confidence":<0.0-1.0>,"treatment":"<specific dose>"}

Allowed disease values: mildiou | oidium | alternaria | rouille | saine | inconnue | hors_sujet

Rules:
- Not a plant image → disease:"hors_sujet", confidence:1.0
- Include exact treatment dose (g/L or ml/L AND total for 1 ha)
- Be confident — farmers need clear answers

Examples:
Tomato leaf, yellow patches, white fuzz under leaf
→ {"disease":"mildiou","confidence":0.91,"treatment":"Mandipropamide 250 SC: 1.2ml/L × 500L/ha = 0.6L/ha total"}

White powdery coating on zucchini leaves
→ {"disease":"oidium","confidence":0.88,"treatment":"Soufre mouillable 80%: 3g/L × 600L/ha = 1.8kg/ha total"}

Brown concentric rings on tomato/potato leaf
→ {"disease":"alternaria","confidence":0.85,"treatment":"Difénoconazole 250 EC: 0.5ml/L × 600L/ha = 0.3L/ha total"}

Orange-brown pustules on wheat/barley
→ {"disease":"rouille","confidence":0.87,"treatment":"Propiconazole 250 EC: 0.5ml/L × 500L/ha — 1 application suffit"}

Healthy green leaf, no visible symptoms
→ {"disease":"saine","confidence":0.95,"treatment":"Aucun traitement — surveillance régulière"}

Car / selfie / landscape / non-plant
→ {"disease":"hors_sujet","confidence":1.0,"treatment":"Envoyez une photo de feuille ou de culture"}"""


class VisionAgent:
    """Analyzes plant images. Returns a structured disease diagnosis dict."""

    @staticmethod
    def run(image_bytes: bytes, mime: str, text: str = "") -> dict:
        t = _types()
        parts = [
            t.Part.from_bytes(data=image_bytes, mime_type=mime),
            t.Part.from_text(text=text or "Analyse cette plante."),
        ]
        resp = _client().models.generate_content(
            model="gemini-2.0-flash",
            contents=[t.Content(role="user", parts=parts)],
            config=t.GenerateContentConfig(
                system_instruction=_VISION_PROMPT,
                temperature=0.1,
                max_output_tokens=200,
            ),
        )
        raw = resp.text.strip()
        # Strip markdown code fences properly (regex, not lstrip which strips chars)
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            result = {
                "disease": "inconnue",
                "confidence": 0.0,
                "treatment": "Impossible d'analyser la photo. Réessayez avec une image plus nette.",
            }
        result.setdefault("agent", "VisionAgent")
        return result

    @staticmethod
    def format(result: dict, lang: str, surface_ha: float = 1.0) -> str:
        disease = result.get("disease", "inconnue")
        conf    = result.get("confidence", 0) * 100
        treat   = result.get("treatment", "")

        if disease == "hors_sujet":
            msgs = {
                "darija_arabic": "📸 هاد الصورة ماشي نبتة. عطيني صورة لورقة أو زريعة باش نشخص ليك.",
                "darija_latin":  "📸 Had s-sura mashi nba. Sift sura d waraqa aw zri3a bach nshakhes lik.",
                "french":        "📸 Ce n'est pas une plante. Envoyez une photo de feuille ou de culture.",
            }
            return msgs.get(lang, msgs["french"])

        emoji = {"mildiou":"🔴","oidium":"🟡","alternaria":"🟠","rouille":"🟤","saine":"🟢"}.get(disease,"🔵")

        # Scale treatment dose to farmer's surface if we can parse a number
        dose_note = ""
        m = re.search(r"([\d.]+)\s*(L|kg)/ha", treat)
        if m and surface_ha != 1.0:
            qty   = float(m.group(1)) * surface_ha
            unit  = m.group(2)
            dose_note = f"\n📦 Pour tes {surface_ha} ha : {qty:.1f} {unit} total"

        if lang == "darija_arabic":
            return (
                f"{emoji} *تشخيص FELLAH.AI*\n━━━━━━━━━━━━━━━\n"
                f"🦠 المرض: *{disease.upper()}*\n"
                f"✅ الثقة: *{conf:.0f}%*\n\n"
                f"💊 العلاج: {treat}{dose_note}\n\n"
                f"⚠️ تصرف خلال 48 ساعة للحفاظ على محصولك."
            )
        elif lang == "darija_latin":
            return (
                f"{emoji} *Diagnostic FELLAH.AI*\n━━━━━━━━━━━━━━━\n"
                f"🦠 Mard: *{disease.upper()}*\n"
                f"✅ Thiqa: *{conf:.0f}%*\n\n"
                f"💊 3ilaj: {treat}{dose_note}\n\n"
                f"⚠️ Dir had ch-chi f 48h bach t7afed 3la l-m7sul."
            )
        else:
            return (
                f"{emoji} *Diagnostic FELLAH.AI*\n━━━━━━━━━━━━━━━\n"
                f"🦠 Maladie: *{disease.upper()}*\n"
                f"✅ Fiabilité: *{conf:.0f}%*\n\n"
                f"💊 Traitement: {treat}{dose_note}\n\n"
                f"⚠️ Agissez dans les 48h pour sauver votre récolte."
            )


# ════════════════════════════════════════════════════════════════════════════
# 2. ProfitAgent — financial calculation (pure Python, zero Gemini latency)
#    Contract: (text, profile) → formatted profit string
# ════════════════════════════════════════════════════════════════════════════

class ProfitAgent:
    """Calculates crop profit instantly from farmer profile + text. No LLM call."""

    @staticmethod
    def run(text: str, profile) -> dict:
        from .profit import calcul_profit

        crop     = _crop(text) or (profile.main_crop if profile else None)
        if not crop:
            return {"error": "crop_unknown"}

        m        = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:ha\b|hectares?)", text.lower())
        surface  = float(m.group(1).replace(",", ".")) if m else (getattr(profile, "surface_ha", None) or 1.0)
        region   = getattr(profile, "region",    None) or "haouz"
        soil     = getattr(profile, "soil_type", None) or "limoneux"
        irr      = getattr(profile, "irrigation", None) or "goutte_a_goutte"

        return calcul_profit(crop, surface, soil, region, irr)

    @staticmethod
    def format(data: dict, lang: str) -> str:
        if "error" in data:
            return {
                "darija_arabic": "أخبرني اسم الزريعة باش نحسب ليك الربح.",
                "darija_latin":  "Gouliya smiyat z-zri3a bach nhseb lik l-profit.",
                "french":        "Précisez la culture pour calculer le profit.",
            }.get(lang, "Précisez la culture.")

        p = data
        if lang == "darija_arabic":
            return (
                f"💰 *حساب الربح — {p['culture'].upper()} ({p['surface_ha']} هكتار)*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌾 الإنتاج المتوقع : {p['production_totale']:,.0f} كغ\n"
                f"💵 الدخل الإجمالي  : {p['revenu_brut']:,.0f} درهم\n"
                f"📉 المصاريف        : {p['cout_total']:,.0f} درهم\n"
                f"✨ *الربح الصافي   : {p['profit_net']:,.0f} درهم*\n"
                f"📊 العائد          : {p['roi_pct']}%\n"
                f"🗓️ أفضل وقت للبيع  : {p.get('meilleur_mois_vente','')}\n"
                f"💡 {p.get('conseil','')}"
            )
        elif lang == "darija_latin":
            return (
                f"💰 *L7isab — {p['culture'].upper()} ({p['surface_ha']} ha)*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌾 Production    : {p['production_totale']:,.0f} kg\n"
                f"💵 Revenu        : {p['revenu_brut']:,.0f} DH\n"
                f"📉 Coûts         : {p['cout_total']:,.0f} DH\n"
                f"✨ *Profit net   : {p['profit_net']:,.0f} DH*\n"
                f"📊 ROI           : {p['roi_pct']}%\n"
                f"🗓️ {p.get('meilleur_mois_vente','')}\n"
                f"💡 {p.get('conseil','')}"
            )
        else:
            return (
                f"💰 *Calcul profit — {p['culture'].upper()} ({p['surface_ha']} ha)*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌾 Production estimée : {p['production_totale']:,.0f} kg\n"
                f"💵 Revenu brut        : {p['revenu_brut']:,.0f} DH\n"
                f"📉 Coûts totaux       : {p['cout_total']:,.0f} DH\n"
                f"✨ *Profit net        : {p['profit_net']:,.0f} DH*\n"
                f"📊 ROI               : {p['roi_pct']}%\n"
                f"🗓️ Meilleur mois      : {p.get('meilleur_mois_vente','')}\n"
                f"💡 {p.get('conseil','')}"
            )


# ════════════════════════════════════════════════════════════════════════════
# 3. CropAgent — best crops to plant this month (pure Python, zero latency)
#    Contract: (profile) → formatted recommendation string
# ════════════════════════════════════════════════════════════════════════════

_EMOJI = {
    "tomate":"🍅","ble":"🌾","poivron":"🌶️","oignon":"🧅","pomme_de_terre":"🥔",
    "olive":"🫒","orange":"🍊","fraise":"🍓","haricot_vert":"🌿",
    "pasteque":"🍉","courgette":"🥒","betterave":"🌱",
}

class CropAgent:
    """Returns top crops to plant this month based on farmer profile. No LLM call."""

    @staticmethod
    def run(profile) -> list:
        from .recommender import recommend
        return recommend(
            region    = getattr(profile, "region",    None) or "haouz",
            surface_ha= getattr(profile, "surface_ha",None) or 1.0,
            soil_type = getattr(profile, "soil_type", None) or "limoneux",
            irrigation= getattr(profile, "irrigation",None) or "goutte_a_goutte",
        )

    @staticmethod
    def format(recs: list, lang: str, surface_ha: float = 1.0) -> str:
        month = datetime(2000, datetime.now().month, 1).strftime("%B")
        if not recs:
            return {
                "darija_arabic": f"ما كاينش زريعة مناسبة للزرع هذا الشهر ({month}).",
                "darija_latin":  f"Ma kayn chi zri3a bach tzra3 had ch-har ({month}).",
                "french":        f"Aucune culture recommandée ce mois-ci ({month}).",
            }.get(lang, f"Aucune culture recommandée ({month}).")

        headers = {
            "darija_arabic": f"🌱 *أفضل زريعة للزرع هذا الشهر ({month}) — {surface_ha} هكتار:*",
            "darija_latin":  f"🌱 *Top cultures bach tzra3 had ch-har ({month}) — {surface_ha}ha:*",
            "french":        f"🌱 *Top cultures à planter ce mois ({month}) — {surface_ha} ha:*",
        }
        footers = {
            "darija_arabic": "\nاختار واحدة وسولني التفاصيل 👇",
            "darija_latin":  "\nKhtari wa7da w swa2elni 3la t-tafasil 👇",
            "french":        "\nChoisissez une culture et demandez les détails 👇",
        }

        lines = [headers.get(lang, headers["french"]), "━━━━━━━━━━━━━━━"]
        for i, r in enumerate(recs, 1):
            lines.append(
                f"{i}. {_EMOJI.get(r['crop'],'🌱')} *{r['crop'].upper()}* "
                f"→ Profit: {r['profit_net']:,.0f} DH | ROI: {r['roi_pct']}%"
            )
        lines.append(footers.get(lang, footers["french"]))
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# 4. DiseaseAgent — text disease/treatment questions
#    Contract: (text, profile, history) → response string
#    Focused prompt → fast Gemini call
# ════════════════════════════════════════════════════════════════════════════

_DISEASE_PROMPT = """Tu es FELLAH-Disease, expert phytopathologie marocaine.
Réponds UNIQUEMENT aux questions maladies, traitements, ravageurs, pesticides.
- Tag [LANG:X] → réponds dans la bonne langue (darija_arabic/darija_latin/french)
- Doses TOUJOURS: g/L ou ml/L ET quantité totale pour la surface indiquée
- Max 4 phrases. 1 action concrète à la fin.
- Hors-sujet → redirige vers agriculture poliment

Traitements clés Maroc:
Mildiou     → Mandipropamide 0.6L/ha | Fosetyl-Al 2.5kg/ha | intervalle 7-10j
Oïdium      → Soufre mouillable 3kg/ha | Tébuconazole 0.5L/ha | intervalle 10-14j
Alternaria  → Difénoconazole 0.5L/ha | Chlorothalonil 2L/ha | toutes 2 semaines
Rouille     → Propiconazole 0.5L/ha (1 seule application curative)
Mouche blanche → Imidaclopride 80g/ha | Spirotetramat 0.8L/ha
Botrytis    → Iprodione 1.5kg/ha | Fenhexamide 1.5kg/ha"""

class DiseaseAgent:
    """Answers plant disease/treatment questions. Focused Gemini call."""

    @staticmethod
    def run(text: str, profile, history: list) -> str:
        t = _types()
        lang = _lang(text)

        profile_note = ""
        if profile and profile.surface_ha:
            profile_note = f"\nFarmer: {profile.surface_ha}ha, {profile.region or '?'}, {profile.irrigation or '?'}."

        # Last 4 messages for context
        contents = []
        for msg in history[-4:]:
            role = "model" if msg.get("role") in ("model", "assistant") else "user"
            contents.append(t.Content(role=role, parts=[t.Part.from_text(text=msg.get("content") or "")]))

        contents.append(t.Content(
            role="user",
            parts=[t.Part.from_text(text=f"[LANG:{lang}]{profile_note}\n{text}")],
        ))

        resp = _client().models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=t.GenerateContentConfig(
                system_instruction=_DISEASE_PROMPT,
                temperature=0.2,
                max_output_tokens=400,
            ),
        )
        return resp.text.strip()


# ════════════════════════════════════════════════════════════════════════════
# 5. GeneralAgent — conversational fallback + audio handling
#    Contract: (text, history, profile, audio_bytes?) → response string
# ════════════════════════════════════════════════════════════════════════════

_GENERAL_PROMPT = """Tu es FELLAH, assistant agricole marocain expert — chaleureux, direct, précis.

LANGUE : Tag [LANG:X] → réponds en darija_arabic / darija_latin / french. Ne change jamais de langue.
DOMAINE : Agriculture UNIQUEMENT. Hors-sujet → redirige poliment dans la langue du message.
CHIFFRES : Toujours des doses précises (g/L + total/ha), prix en DH, rendements en kg/ha.
FORMAT : Max 5 phrases. Toujours 1 action concrète à la fin.
AUDIO : Transcris et réponds dans la même langue parlée.
TON : Ami expert au souk — "khouya", "sahbi", "mon ami" selon langue."""

class GeneralAgent:
    """Full conversational agent with history. Handles audio + general questions."""

    @staticmethod
    def run(
        text: str,
        history: list,
        profile,
        profile_ctx: str = "",
        recs_ctx: str = "",
        audio_bytes: bytes | None = None,
        audio_mime: str | None = None,
    ) -> str:
        t = _types()
        lang = _lang(text)
        system = _GENERAL_PROMPT + profile_ctx + recs_ctx

        contents = []
        for msg in history:
            role = "model" if msg.get("role") in ("model", "assistant") else "user"
            contents.append(t.Content(role=role, parts=[t.Part.from_text(text=msg["content"])]))

        parts = []
        if audio_bytes:
            parts.append(t.Part.from_bytes(data=audio_bytes, mime_type=audio_mime or "audio/ogg"))
        parts.append(t.Part.from_text(text=f"[LANG:{lang}] {text}" if text else f"[LANG:{lang}]"))
        contents.append(t.Content(role="user", parts=parts))

        resp = _client().models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=t.GenerateContentConfig(
                system_instruction=system,
                temperature=0.35,
                max_output_tokens=500,
            ),
        )
        return resp.text.strip()


# ════════════════════════════════════════════════════════════════════════════
# 6. LocationWeatherAgent — GPS location + live weather + disease risk alert
#    Contract: (lat, lon, profile, lang) → formatted response string
#    Uses Open-Meteo (free, no API key)
# ════════════════════════════════════════════════════════════════════════════

# WMO weather code → simple description
_WMO = {
    0: "ensoleillé", 1: "peu nuageux", 2: "nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine", 55: "bruine forte",
    61: "pluie légère", 63: "pluie", 65: "pluie forte",
    71: "neige légère", 73: "neige", 75: "neige forte",
    80: "averses légères", 81: "averses", 82: "averses fortes",
    95: "orage", 96: "orage avec grêle",
}

_REGION_NAMES = {
    "souss": "Souss-Massa", "gharb": "Gharb", "tadla": "Tadla",
    "loukkos": "Loukkos", "doukkala": "Doukkala", "haouz": "Haouz",
    "moulouya": "Moulouya", "rif": "Rif",
}


class LocationWeatherAgent:
    """Fetches live weather from Open-Meteo and generates disease risk alert."""

    @staticmethod
    def fetch_weather(lat: float, lon: float) -> dict | None:
        """Calls Open-Meteo API (free, no key). Returns weather dict or None."""
        try:
            import urllib.request as _req
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,"
                f"precipitation,weather_code,wind_speed_10m"
                f"&forecast_days=1"
            )
            with _req.urlopen(url, timeout=5) as r:
                data = json.loads(r.read())
            c = data["current"]
            return {
                "temp":     round(c["temperature_2m"], 1),
                "humidity": round(c["relative_humidity_2m"]),
                "precip":   round(c["precipitation"], 1),
                "wind":     round(c["wind_speed_10m"]),
                "desc":     _WMO.get(int(c["weather_code"]), "variable"),
            }
        except Exception:
            return None

    @staticmethod
    def disease_risk(weather: dict, main_crop: str | None) -> str:
        """Simple rule-based disease risk from weather conditions."""
        if weather is None:
            return ""
        h   = weather["humidity"]
        t   = weather["temp"]
        p   = weather["precip"]
        risks = []
        if h >= 75 and 12 <= t <= 26:
            risks.append("⚠️ Risque MILDIOU élevé (humidité {}%) — traitez avant la pluie.".format(h))
        if h <= 45 and t >= 25:
            risks.append("⚠️ Risque OÏDIUM (sec + chaud) — surveillez les feuilles.")
        if p > 5:
            risks.append("🌧️ Pluie détectée — appliquez un fongicide préventif dans les 24h.")
        if not risks:
            risks.append("✅ Conditions météo favorables — pas d'alerte phytosanitaire.")
        return "\n".join(risks)

    @staticmethod
    def format(lat: float, lon: float, region: str | None, weather: dict | None,
               main_crop: str | None, lang: str) -> str:
        region_label = _REGION_NAMES.get(region or "", region or "Maroc")

        if weather is None:
            # Location saved but weather unavailable
            msgs = {
                "darija_arabic": (
                    f"📍 *موقعك مسجل* — {region_label}\n"
                    "تعذر جلب بيانات الطقس الآن. سنستخدم موقعك لتحسين توصياتنا."
                ),
                "darija_latin": (
                    f"📍 *Localisation enregistrée* — {region_label}\n"
                    "Ma qderch njib t-taqes daba. Ghadi nsta3mel mawqi3k bach n7ssen lik n-nasayeh."
                ),
                "french": (
                    f"📍 *Localisation enregistrée* — {region_label}\n"
                    "Météo indisponible pour l'instant. Votre position sera utilisée pour améliorer les recommandations."
                ),
            }
            return msgs.get(lang, msgs["french"])

        risk = LocationWeatherAgent.disease_risk(weather, main_crop)

        if lang == "darija_arabic":
            return (
                f"📍 *موقعك: {region_label}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌡️ الحرارة : {weather['temp']}°C — {weather['desc']}\n"
                f"💧 الرطوبة : {weather['humidity']}%\n"
                f"🌬️ الريح   : {weather['wind']} كم/ساعة\n\n"
                f"{risk}\n\n"
                f"_موقعك محفوظ — سنستخدمه لتحسين توصيات الزريعة والأسعار._"
            )
        elif lang == "darija_latin":
            return (
                f"📍 *Mawqi3k: {region_label}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌡️ S-skhana : {weather['temp']}°C — {weather['desc']}\n"
                f"💧 R-rtuba  : {weather['humidity']}%\n"
                f"🌬️ R-rih    : {weather['wind']} km/h\n\n"
                f"{risk}\n\n"
                f"_Mawqi3k mhfud — ghadi nsta3mlu bach n7ssen lik t-tawsiyat._"
            )
        else:
            return (
                f"📍 *Votre localisation: {region_label}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🌡️ Température : {weather['temp']}°C — {weather['desc']}\n"
                f"💧 Humidité    : {weather['humidity']}%\n"
                f"🌬️ Vent        : {weather['wind']} km/h\n\n"
                f"{risk}\n\n"
                f"_Localisation enregistrée — utilisée pour améliorer vos recommandations._"
            )


# ════════════════════════════════════════════════════════════════════════════
# Session helpers
# ════════════════════════════════════════════════════════════════════════════

_MAX_HISTORY  = 12
_SESSION_TTL  = 2   # hours

def _get_session(phone: str, db):
    from ..database import ConversationSession
    s = db.query(ConversationSession).filter_by(phone=phone).first()
    if s is None:
        s = ConversationSession(phone=phone, history_json="[]")
        db.add(s)
        db.flush()
    return s

def _load_history(s) -> list:
    if s.last_active:
        t = s.last_active
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - t > timedelta(hours=_SESSION_TTL):
            return []
    try:
        return json.loads(s.history_json or "[]")
    except Exception:
        return []

def _save_history(s, history: list, db):
    s.history_json = json.dumps(history[-_MAX_HISTORY:], ensure_ascii=False)
    s.last_active  = datetime.now(timezone.utc)
    db.commit()


# ════════════════════════════════════════════════════════════════════════════
# Orchestrator — public API (single entry point from main.py)
# ════════════════════════════════════════════════════════════════════════════

def process_message(
    phone: str,
    text: str,
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
    db=None,
) -> str:
    """
    Route incoming WhatsApp message to the correct sub-agent.
    Updates farmer profile and conversation history in DB.
    Returns the final response string.
    """
    try:
        # ── Load / update farmer profile ─────────────────────────────────────
        profile = None
        if db and (text or "").strip():
            from .profile import update_from_text, get_or_create
            profile = update_from_text(text, phone, db)
        elif db:
            from .profile import get_or_create
            profile = get_or_create(phone, db)

        # ── Load conversation history ─────────────────────────────────────────
        session = history = None
        if db:
            session = _get_session(phone, db)
            history = _load_history(session)
        history = history or []

        # ── Detect intent & route ─────────────────────────────────────────────
        intent   = _intent(text or "", bool(image_bytes), bool(audio_bytes))
        lang     = _lang(text or "")
        surface  = getattr(profile, "surface_ha", None) or 1.0
        response = ""

        if intent == "vision":
            # ── VisionAgent ───────────────────────────────────────────────────
            result   = VisionAgent.run(image_bytes, image_mime or "image/jpeg", text or "")
            response = VisionAgent.format(result, lang, surface)
            # Store disease name in history for product recommendation in main.py
            history.append({"role": "user",  "content": f"[Photo] {text or ''}"})
            history.append({"role": "model", "content": response})

        elif intent == "profit":
            # ── ProfitAgent (pure Python) ─────────────────────────────────────
            data     = ProfitAgent.run(text, profile)
            response = ProfitAgent.format(data, lang)
            # If crop unknown, fall through to GeneralAgent to ask for it
            if "error" in data:
                response = GeneralAgent.run(text, history, profile)
            history.append({"role": "user",  "content": text})
            history.append({"role": "model", "content": response})

        elif intent == "crop_rec":
            # ── CropAgent (pure Python) ───────────────────────────────────────
            recs     = CropAgent.run(profile)
            response = CropAgent.format(recs, lang, surface)
            history.append({"role": "user",  "content": text})
            history.append({"role": "model", "content": response})

        elif intent == "disease":
            # ── DiseaseAgent (focused Gemini) ─────────────────────────────────
            response = DiseaseAgent.run(text, profile, history)
            history.append({"role": "user",  "content": text})
            history.append({"role": "model", "content": response})

        else:
            # ── GeneralAgent (full conversation + audio) ──────────────────────
            from .profile import to_prompt_context
            from .recommender import to_prompt_context as recs_ctx_fn
            p_ctx = to_prompt_context(profile) if profile else ""
            r_ctx = ""
            if profile and profile.region and profile.surface_ha:
                r_ctx = recs_ctx_fn(
                    region    = profile.region,
                    surface_ha= profile.surface_ha,
                    soil_type = getattr(profile, "soil_type",  None) or "limoneux",
                    irrigation= getattr(profile, "irrigation", None) or "goutte_a_goutte",
                )
            response = GeneralAgent.run(
                text, history, profile, p_ctx, r_ctx, audio_bytes, audio_mime
            )
            user_content = "[Message vocal]" if audio_bytes and not text else (text or "")
            history.append({"role": "user",  "content": user_content})
            history.append({"role": "model", "content": response})

        # ── Persist history ───────────────────────────────────────────────────
        if db and session is not None:
            _save_history(session, history, db)

        return response

    except Exception as exc:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        return (
            "عفواً صاحبي، كاين مشكل تقني دغية 🙏 "
            "عاود جرب من بعد شوية."
        )
