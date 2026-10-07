"""Idioma del Centro Lizarbe (es/en).

Los textos del código están escritos en español y sirven de clave: `tr("texto")`
devuelve la traducción de `i18n/en.json` cuando el idioma es inglés (si falta,
queda el español). `trf("Hola {nombre}", nombre=x)` hace lo mismo con valores.
El idioma es el mismo que usan Escritorio y Widgets (`lang` en
~/.config/lizarbe/ajustes.toml), y se puede forzar con LIZARBE_LANG=es|en.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

_DIR = Path(__file__).resolve().parent / "i18n"
_cache: Dict[str, Dict[str, str]] = {}
_lang = ""


def detect_lang() -> str:
    forced = os.environ.get("LIZARBE_LANG", "").lower()
    if forced in ("es", "en"):
        return forced
    cfg = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    try:
        import tomllib

        with open(cfg / "lizarbe" / "ajustes.toml", "rb") as f:
            lang = str(tomllib.load(f).get("lang", "")).lower()
        if lang in ("es", "en"):
            return lang
    except (OSError, ValueError, ImportError):
        pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v and v not in ("C", "POSIX"):
            return "es" if v.lower().startswith("es") else "en"
    return "en"


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in ("es", "en") else "es"


def lang() -> str:
    global _lang
    if not _lang:
        _lang = detect_lang()
    return _lang


def _table(code: str) -> Dict[str, str]:
    if code not in _cache:
        try:
            with open(_DIR / f"{code}.json", encoding="utf-8") as f:
                _cache[code] = json.load(f)
        except (OSError, ValueError):
            _cache[code] = {}
    return _cache[code]


def tr(text: str) -> str:
    """Traduce `text` (español) al idioma actual, conservando espacios de relleno."""
    if lang() == "es":
        return text
    core = text.strip()
    if not core:
        return text
    table = _table(lang())
    out = table.get(core)
    if out is None:
        # Icono (Nerd Font) delante del texto: se traduce solo el texto.
        icon = ""
        rest = core
        while rest and (ord(rest[0]) >= 0xE000 or rest[0] in " \t"):
            icon += rest[0]
            rest = rest[1:]
        if icon and rest and rest in table:
            out = icon + table[rest]
        else:
            return text
    start = len(text) - len(text.lstrip())
    end = len(text) - len(text.rstrip())
    return text[:start] + out + (text[len(text) - end:] if end else "")


def trf(template: str, **values) -> str:
    """Como `tr`, con valores: la plantilla usa {nombre}."""
    out = tr(template)
    try:
        return out.format(**values)
    except (KeyError, IndexError, ValueError):
        return template.format(**values)
