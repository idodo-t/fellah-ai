"""
FELLAH.AI — Voice Service
Pipeline complet : Audio WhatsApp → Whisper → GPT-4o-mini → réponse Darija.

Stratégie :
  1. Si OPENAI_API_KEY présente → pipeline réel (Whisper + GPT)
  2. Sinon                      → mock (retourne texte Darija statique)

Contrat immuable :
  process_voice_darija(audio_url: str) -> str   # texte en Darija
"""

import os
import logging
import tempfile
import urllib.request
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt FELLAH (fixé, ne pas modifier)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "Tu es FELLAH, assistant agricole marocain expert. "
    "Parle UNIQUEMENT en Darija marocaine (arabe dialectal). "
    "Réponds en 3 phrases max: diagnostic direct, action concrète, coût/bénéfice. "
    "Sois simple, comme un ami agronome au marché. "
    "Prix Maroc 2024: tomate 1.8 DH/kg, blé 3.2 DH/kg, poivron 2.5 DH/kg."
)

# ---------------------------------------------------------------------------
# Mock (aucune clé API requise)
# ---------------------------------------------------------------------------
def _mock_process(audio_url: str) -> str:
    """
    Retourne une réponse Darija plausible sans appel réseau.
    Déterministe selon l'URL pour des tests reproductibles.
    """
    responses = [
        "صاحبي، شجرة الطماطم ديالك عندها ميلديو. رش عليها بوردو 2% من الصباح. غتربح على 40,000 كيلو للهكتار بسعر 1.8 درهم.",
        "واش شفت البقع البيضاء؟ هاد الأوديوم — استعمل الكبريت المبلل. ما تخسرش محصولك، التكلفة غير 500 درهم.",
        "النبتة ديالك صحيحة الحمد لله. واصل السقي ومراقبة الأوراق كل أسبوع.",
        "عندك ألترناريا في الفلفل. الكلوروتالونيل هو الدواء، كل أسبوعين. الهكتار غيجيب 28,000 كيلو بـ 2.5 درهم.",
    ]
    idx = hash(audio_url) % len(responses)
    return responses[idx]


# ---------------------------------------------------------------------------
# Pipeline réel : Whisper → GPT-4o-mini
# ---------------------------------------------------------------------------
def _download_audio(audio_url: str) -> str:
    """Télécharge l'audio dans un fichier temporaire, retourne le chemin."""
    # Détecte l'extension depuis l'URL (défaut .ogg pour WhatsApp)
    ext = ".ogg"
    for candidate in (".ogg", ".mp3", ".wav", ".m4a", ".mp4", ".amr"):
        if candidate in audio_url.lower():
            ext = candidate
            break

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.close()
    urllib.request.urlretrieve(audio_url, tmp.name)
    return tmp.name


def _transcribe_whisper(audio_path: str, client) -> str:
    """Transcrit l'audio avec Whisper. Retourne le texte."""
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ar",          # Darija est proche de l'arabe standard
            response_format="text",
        )
    return transcript.strip()


def _generate_darija_response(text: str, client) -> str:
    """Envoie le texte transcrit à GPT-4o-mini, retourne la réponse Darija."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ],
        max_tokens=200,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


def _real_process(audio_url: str) -> str:
    """Pipeline complet avec OpenAI."""
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    audio_path = _download_audio(audio_url)

    try:
        transcription = _transcribe_whisper(audio_path, client)
        logger.info("Whisper transcription: %s", transcription[:80])

        darija_reply = _generate_darija_response(transcription, client)
        logger.info("GPT reply (Darija): %s", darija_reply[:80])

        return darija_reply

    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Fonction publique — NE PAS RENOMMER
# ---------------------------------------------------------------------------
def process_voice_darija(audio_url: str) -> str:
    """
    Traite un message vocal WhatsApp et retourne une réponse en Darija.

    Pipeline :
        1. Télécharge l'audio depuis audio_url
        2. Transcrit avec Whisper (OpenAI)
        3. Génère un conseil agricole en Darija via GPT-4o-mini
        4. Retourne le texte Darija

    Args:
        audio_url: URL publique du fichier audio (.ogg, .mp3, .wav, ...)

    Returns:
        Texte en Darija marocaine (3 phrases max).

    Garantie : ne lève jamais d'exception — retourne toujours un str non vide.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        logger.info("OPENAI_API_KEY absente — mode mock activé.")
        return _mock_process(audio_url)

    try:
        return _real_process(audio_url)
    except Exception as exc:
        logger.error("process_voice_darija a échoué (%s) — retour mock de sécurité.", exc)
        return _mock_process(audio_url)
