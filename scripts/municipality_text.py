"""Gezielte Reparatur bereits falsch interpretierter UTF-8-Namen.

Nicht pauschal Zeichen umkodieren: Nur typische UTF-8-als-Latin-1/CP1252
Mojibake-Muster reparieren. Amtliche ID und Geometrien bleiben unverändert.
"""
from __future__ import annotations


def readable_name(value: str) -> str:
    text = str(value)
    if not any(marker in text for marker in ("Ã", "Â", "â€", "â€“", "â€”")):
        return text
    for encoding in ("cp1252", "latin-1"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except (UnicodeError, ValueError):
            continue
        if repaired.count("Ã") + repaired.count("Â") < text.count("Ã") + text.count("Â"):
            return repaired
    return text
