"""
Punto de Entrada para la Interfaz TUI de Lizarbe Omarchy Theme.
Inicia el Splash Loader animado y la interfaz monolítica de 2 paneles.
"""

from __future__ import annotations
import sys
import argparse

from lizarbe_tui import __version__
from lizarbe_tui.ui.loader import StartupLoader
from lizarbe_tui.ui.tui import LizarbeTUI
from lizarbe_tui.i18n import tr, trf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lizarbe-tui",
        description=tr("Lizarbe Theme & Suite — Panel TUI interactivo para Omarchy & Hyprland"),
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--section",
        type=str,
        default="",
        help=tr("Sección inicial al abrir la TUI (theme, dotfiles, status, suites, apps_creative, apps_work, uninstall)"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    loader = StartupLoader(title="CENTRO LIZARBE")
    loader.start()
    try:
        app = LizarbeTUI(was_tiled=loader.was_tiled)
        if args.section:
            for idx, (_, sec_id, _, _, _) in enumerate(app.SECTIONS):
                if sec_id == args.section:
                    app.current_section_idx = idx
                    break
        loader.stop()
        app.run()
    except KeyboardInterrupt:
        loader.cleanup()
        sys.exit(0)
    except Exception:
        loader.cleanup()
        raise


if __name__ == "__main__":
    main()
