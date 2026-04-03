"""
FELLAH.AI — Text-to-Speech Service
Converts text to MP3 using gTTS (Google TTS, free).
Used to send audio replies to illiterate/voice-preference farmers.
"""

import os
import uuid
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "/tmp/fellah_audio"))

# Language code mapping
_LANG_CODE = {
    "darija_arabic": "ar",
    "darija_latin":  "ar",   # spoken Arabic even if written in latin letters
    "french":        "fr",
}


def speak(text: str, lang: str) -> str | None:
    """
    Generate an MP3 file from text.

    Args:
        text: The response text to convert.
        lang: One of darija_arabic | darija_latin | french

    Returns:
        Filename (not full path) of the generated MP3, or None if failed.
    """
    try:
        from gtts import gTTS
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        lang_code = _LANG_CODE.get(lang, "ar")
        filename  = f"fellah_{uuid.uuid4().hex[:12]}.mp3"
        filepath  = AUDIO_DIR / filename
        gTTS(text=text, lang=lang_code, slow=False).save(str(filepath))
        logger.info("TTS generated: %s (%s)", filename, lang_code)
        return filename
    except Exception as exc:
        logger.warning("TTS failed: %s", exc)
        return None


def audio_path(filename: str) -> Path:
    """Returns the full path for a given audio filename."""
    return AUDIO_DIR / filename
