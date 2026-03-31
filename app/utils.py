"""
FELLAH.AI — Utils
Fonctions utilitaires partagées.
"""

import hashlib


def hash_phone(phone_number: str) -> str:
    """
    Hash SHA-256 d'un numéro de téléphone pour anonymisation.

    Args:
        phone_number: Numéro au format E.164 (ex: +212612345678)

    Returns:
        Hash SHA-256 hexadécimal (64 caractères).
    """
    return hashlib.sha256(phone_number.strip().encode()).hexdigest()
