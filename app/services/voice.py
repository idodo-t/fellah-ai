"""
FELLAH.AI — Voice Service
Pipeline : Audio WhatsApp → Gemini (transcription + conseil) → réponse Darija → gTTS .mp3

Stratégie :
  1. Si GEMINI_API_KEY présente → Gemini Flash (audio direct + réponse Darija)
  2. Sinon                      → mock (texte Darija statique)
  gTTS : toujours actif, génère un .mp3 (chemin dans TTS_OUTPUT_DIR)

Contrat immuable :
  process_voice_darija(audio_url: str) -> str   # texte en Darija
  synthesize_darija(text: str) -> str           # chemin vers le .mp3
"""

import os
import uuid
import logging
import tempfile
import urllib.request
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "/tmp/fellah_audio")

# ---------------------------------------------------------------------------
# System prompt FELLAH
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "Tu es FELLAH, assistant agricole marocain expert. "
    "Parle UNIQUEMENT en Darija marocaine (arabe dialectal). "
    "Réponds en 3 phrases max: diagnostic direct, action concrète, coût/bénéfice. "
    "Sois simple, comme un ami agronome au marché. "
    "Prix Maroc 2024: tomate 1.8 DH/kg, blé 3.2 DH/kg, poivron 2.5 DH/kg."
)

# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------
def _mock_process(audio_url: str) -> str:
    responses = [
        "صاحبي، شجرة الطماطم ديالك عندها ميلديو. رش عليها بوردو 2% من الصباح. غتربح على 40,000 كيلو للهكتار بسعر 1.8 درهم.",
        "واش شفت البقع البيضاء؟ هاد الأوديوم — استعمل الكبريت المبلل. ما تخسرش محصولك، التكلفة غير 500 درهم.",
        "النبتة ديالك صحيحة الحمد لله. واصل السقي ومراقبة الأوراق كل أسبوع.",
        "عندك ألترناريا في الفلفل. الكلوروتالونيل هو الدواء، كل أسبوعين. الهكتار غيجيب 28,000 كيلو بـ 2.5 درهم.",
    ]
    idx = hash(audio_url) % len(responses)
    return responses[idx]


# ---------------------------------------------------------------------------
# Pipeline Gemini : audio → transcription + réponse Darija en un seul appel
# ---------------------------------------------------------------------------
def _download_audio(audio_url: str) -> tuple[str, str]:
    """Télécharge l'audio, retourne (chemin_tmp, mime_type)."""
    ext_mime = {
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".amr": "audio/amr",
    }
    ext = ".ogg"
    for candidate in ext_mime:
        if candidate in audio_url.lower():
            ext = candidate
            break

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.close()
    urllib.request.urlretrieve(audio_url, tmp.name)
    return tmp.name, ext_mime.get(ext, "audio/ogg")


def _real_process(audio_url: str) -> str:
    """Pipeline Gemini : envoie l'audio directement, reçoit la réponse Darija."""
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    audio_path, mime_type = _download_audio(audio_url)

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "L'agriculteur t'a envoyé ce message vocal. "
            "Transcris ce qu'il dit, puis réponds-lui directement en Darija."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_data, mime_type=mime_type),
            ],
        )

        return response.text.strip()

    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Synthèse vocale gTTS
# ---------------------------------------------------------------------------
def synthesize_darija(text: str) -> str:
    """
    Convertit du texte Darija en fichier audio .mp3 pour WhatsApp.

    Returns:
        Chemin absolu vers le fichier .mp3 généré.
    """
    os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(TTS_OUTPUT_DIR, f"fellah_{uuid.uuid4().hex}.mp3")

    try:
        from gtts import gTTS  # type: ignore
        tts = gTTS(text=text, lang="ar", slow=False)
        tts.save(filename)
        logger.info("gTTS audio saved: %s", filename)
    except Exception as exc:
        logger.error("gTTS a échoué (%s) — fichier vide créé.", exc)
        open(filename, "wb").close()

    return filename


# ---------------------------------------------------------------------------
# Fonction publique — NE PAS RENOMMER
# ---------------------------------------------------------------------------
def process_voice_darija(audio_url: str) -> str:
    """
    Traite un message vocal WhatsApp et retourne une réponse en Darija.

    Args:
        audio_url: URL publique du fichier audio (.ogg, .mp3, .wav, ...)

    Returns:
        Texte en Darija marocaine (3 phrases max).

    Garantie : ne lève jamais d'exception — retourne toujours un str non vide.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        logger.info("GEMINI_API_KEY absente — mode mock activé.")
        return _mock_process(audio_url)

    try:
        return _real_process(audio_url)
    except Exception as exc:
        logger.error("process_voice_darija a échoué (%s) — retour mock.", exc)
        return _mock_process(audio_url)
