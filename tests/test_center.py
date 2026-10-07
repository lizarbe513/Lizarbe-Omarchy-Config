"""Pruebas del Centro Lizarbe: traducciones y lectura del repositorio de paquetes."""

import io
import json
import re
import tarfile
import unittest
from pathlib import Path

from lizarbe_tui.core.system_manager import SystemManager

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "lizarbe_tui"


def literal_keys() -> set:
    """Textos `tr("…")` / `trf("…")` escritos en el código."""
    keys = set()
    pattern = re.compile(r"""\btrf?\(\s*(["'])((?:\\.|(?!\1).)*)\1""")
    for py in PKG.rglob("*.py"):
        if py.name == "i18n.py":
            continue
        for m in pattern.finditer(py.read_text(encoding="utf-8")):
            raw = m.group(2).encode().decode("unicode_escape").encode("latin-1").decode("utf-8")
            keys.add(normalize(raw))
    return keys


def normalize(text: str) -> str:
    """La clave que busca `tr`: sin espacios de relleno ni icono delante."""
    core = text.strip()
    while core and (ord(core[0]) >= 0xE000 or core[0] in " \t"):
        core = core[1:]
    return core


class Translations(unittest.TestCase):
    def test_every_text_has_an_english_version(self):
        en = json.loads((PKG / "i18n" / "en.json").read_text(encoding="utf-8"))
        missing = sorted(k for k in literal_keys() if k.strip() and k not in en)
        self.assertEqual(missing, [], "textos sin traducir al inglés")

    def test_english_file_is_valid_and_not_empty(self):
        en = json.loads((PKG / "i18n" / "en.json").read_text(encoding="utf-8"))
        self.assertTrue(en)
        self.assertTrue(all(isinstance(v, str) and v for v in en.values()))


def fake_db(entries: dict) -> bytes:
    """Base de datos de pacman mínima: una carpeta `nombre-versión/` con su `desc`."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, ver in entries.items():
            d = tarfile.TarInfo(f"{name}-{ver}")
            d.type = tarfile.DIRTYPE
            tf.addfile(d)
            body = f"%NAME%\n{name}\n\n%VERSION%\n{ver}\n".encode()
            f = tarfile.TarInfo(f"{name}-{ver}/desc")
            f.size = len(body)
            tf.addfile(f, io.BytesIO(body))
    return buf.getvalue()


class RepoDatabase(unittest.TestCase):
    def test_reads_names_and_versions(self):
        data = fake_db({"lizarbe-menu": "0.7.0-1", "lizarbe-ajustes": "0.7.0-1", "lizarbe": "1-2"})
        self.assertEqual(
            SystemManager.parse_repo_db(data),
            {"lizarbe-menu": "0.7.0-1", "lizarbe-ajustes": "0.7.0-1", "lizarbe": "1-2"},
        )


if __name__ == "__main__":
    unittest.main()
