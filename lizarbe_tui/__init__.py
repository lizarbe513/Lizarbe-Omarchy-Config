"""
Centro Lizarbe — panel TUI de identidad, software y actualizaciones para Omarchy.
"""

import subprocess

# Versión del código; si está instalado el paquete, manda la del paquete.
_SOURCE_VERSION = "0.4.3"


def _package_version() -> str:
    try:
        res = subprocess.run(
            ["pacman", "-Q", "lizarbe-centro"], capture_output=True, text=True, timeout=3
        )
        parts = res.stdout.split()
        if res.returncode == 0 and len(parts) == 2:
            return parts[1].split("-")[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return _SOURCE_VERSION


__version__ = _package_version()
