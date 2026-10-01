"""
Módulo de Motor de Temas y Estilos ANSI Truecolor para Lizarbe TUI.
Detecta el tema activo de Omarchy, lee colors.toml, genera colores derivados suaves
(soft_hover, soft_selection, soft_muted) y gestiona el cambio de tema y fondos de pantalla.
"""

from __future__ import annotations
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Dict, Any, List, Optional


class ThemeEngine:
    def __init__(self, repo_dir: Optional[Path] = None):
        self.repo_dir = repo_dir or Path(__file__).resolve().parent.parent.parent
        self.user_themes_dir = Path.home() / ".config" / "omarchy" / "themes"
        self.system_themes_dir = Path("/usr/share/omarchy/themes")
        self.repo_themes_dir = self.repo_dir / "config" / "omarchy" / "themes"
        self.current_theme_dir = Path.home() / ".config" / "omarchy" / "current" / "theme"
        self.state_theme_dir = Path.home() / ".local" / "state" / "omarchy" / "current" / "theme"
        self._current_theme_name: Optional[str] = None
        self._colors: Dict[str, str] = {}
        self._mode: str = "dark"
        self._icon_theme: str = "Lizarbe-Red"
        self.reload()

    def get_current_theme_name(self) -> str:
        """Obtiene el nombre del tema activo a través de Omarchy."""
        state_name_file = Path.home() / ".local" / "state" / "omarchy" / "current" / "theme.name"
        if state_name_file.exists():
            try:
                name = state_name_file.read_text(encoding="utf-8").strip()
                if name:
                    return name
            except Exception:
                pass

        try:
            res = subprocess.run(
                ["omarchy", "theme", "current"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

        if self.current_theme_dir.exists() and self.current_theme_dir.is_symlink():
            target = os.readlink(self.current_theme_dir)
            return Path(target).name

        return "lizarbe"

    def normalize_theme_slug(self, theme_name: str) -> str:
        """Normaliza el nombre del tema al formato de carpeta de Omarchy."""
        return theme_name.strip().lower().replace(" ", "-")

    def list_available_themes(self) -> List[str]:
        """Lista todos los temas disponibles en el sistema, usuario y repositorio Lizarbe."""
        themes = {"lizarbe", "lizarbe-light"}
        for d in [self.user_themes_dir, self.system_themes_dir, self.repo_themes_dir]:
            if d.exists() and d.is_dir():
                for item in d.iterdir():
                    if item.is_dir() and ((item / "colors.toml").exists() or (item / "alacritty.toml").exists()):
                        themes.add(item.name)
        # Poner lizarbe y lizarbe-light primero en la lista
        rest = sorted([t for t in themes if t not in ("lizarbe", "lizarbe-light")])
        return ["lizarbe", "lizarbe-light"] + rest

    def _find_theme_dir(self, theme_name: str) -> Optional[Path]:
        """Localiza el directorio del tema indicado."""
        slug = self.normalize_theme_slug(theme_name)
        for base in [self.user_themes_dir, self.system_themes_dir, self.repo_themes_dir]:
            for cand in (base / slug, base / theme_name):
                if cand.exists() and cand.is_dir():
                    return cand
        if self.state_theme_dir.exists():
            return self.state_theme_dir
        if self.current_theme_dir.exists():
            return self.current_theme_dir
        return None

    def reload(self) -> None:
        """Recarga la configuración de colores del tema actual."""
        self._current_theme_name = self.get_current_theme_name()
        theme_dir = self._find_theme_dir(self._current_theme_name)

        default_colors = {
            "accent": "#E31B23",
            "selection": "#45475a",
            "background": "#08080B",
            "foreground": "#d8d8d8",
            "muted": "#444444",
            "red": "#E31B23",
            "green": "#2DB872",
            "yellow": "#E5A83B",
            "blue": "#5A7DA8",
            "cyan": "#45A0B5",
            "bright_foreground": "#ffffff",
        }
        self._mode = "dark"
        self._icon_theme = "Lizarbe-Red"

        search_dirs = []
        if self.state_theme_dir.exists():
            search_dirs.append(self.state_theme_dir)
        if theme_dir and theme_dir not in search_dirs:
            search_dirs.append(theme_dir)
        if self.current_theme_dir.exists() and self.current_theme_dir not in search_dirs:
            search_dirs.append(self.current_theme_dir)

        data: Dict[str, Any] = {}
        for d in search_dirs:
            colors_file = d / "colors.toml"
            if colors_file.exists():
                try:
                    with open(colors_file, "rb") as f:
                        data = tomllib.load(f)
                        if "mode" in data and isinstance(data["mode"], str):
                            self._mode = data["mode"]
                        for k, v in data.items():
                            if isinstance(v, str) and v.startswith("#"):
                                default_colors[k] = v
                    break
                except Exception:
                    pass

        for d in search_dirs:
            icons_file = d / "icons.theme"
            if icons_file.exists():
                try:
                    icon_txt = icons_file.read_text(encoding="utf-8").strip()
                    if icon_txt:
                        self._icon_theme = icon_txt
                    break
                except Exception:
                    pass

        if self._mode == "light" and "bright_foreground" not in data:
            default_colors["bright_foreground"] = default_colors.get("foreground", "#000000")

        self._colors = default_colors
        self.update_derived_colors()

    @classmethod
    def blend_hex(cls, hex_base: str, hex_tint: str, ratio: float) -> str:
        """Mezcla dos colores hexadecimales con proporción 'ratio' (0.0 = base, 1.0 = tint)."""
        ratio = max(0.0, min(1.0, ratio))
        r1, g1, b1 = cls.hex_to_rgb(hex_base)
        r2, g2, b2 = cls.hex_to_rgb(hex_tint)
        r = int(r1 * (1.0 - ratio) + r2 * ratio)
        g = int(g1 * (1.0 - ratio) + g2 * ratio)
        b = int(b1 * (1.0 - ratio) + b2 * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_derived_colors(self) -> None:
        """Calcula colores derivados suaves (soft_hover, soft_selection, soft_muted)."""
        bg = self._colors.get("background", "#08080B")
        accent = self._colors.get("accent", "#E31B23")
        sel = self._colors.get("selection", "#45475a")
        muted = self._colors.get("muted", "#585b70")

        if self._mode == "light":
            self._colors["soft_hover"] = self.blend_hex(bg, accent, 0.16)
            self._colors["soft_selection"] = self.blend_hex(bg, sel, 0.45)
            self._colors["soft_muted"] = self.blend_hex(bg, muted, 0.22)
        else:
            self._colors["soft_hover"] = self.blend_hex(bg, accent, 0.22)
            sr, sg, sb = self.hex_to_rgb(sel)
            sel_lum = 0.299 * sr + 0.587 * sg + 0.114 * sb
            sel_ratio = 0.24 if sel_lum > 85 else 0.65
            self._colors["soft_selection"] = self.blend_hex(bg, sel, sel_ratio)
            self._colors["soft_muted"] = self.blend_hex(bg, muted, 0.38)

    @property
    def current_theme(self) -> str:
        return self._current_theme_name or "lizarbe"

    @property
    def colors(self) -> Dict[str, str]:
        return self._colors

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def icon_theme(self) -> str:
        return self._icon_theme

    @staticmethod
    def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
        hex_clean = hex_str.lstrip("#")
        if len(hex_clean) == 3:
            hex_clean = "".join(c * 2 for c in hex_clean)
        if len(hex_clean) >= 6:
            try:
                return (
                    int(hex_clean[0:2], 16),
                    int(hex_clean[2:4], 16),
                    int(hex_clean[4:6], 16),
                )
            except ValueError:
                pass
        return (255, 255, 255)

    def fg(self, color_key: str, text: str) -> str:
        """Devuelve el texto coloreado con truecolor ANSI (primer plano)."""
        hex_val = self._colors.get(color_key, "#ffffff")
        r, g, b = self.hex_to_rgb(hex_val)
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

    def bg(self, color_key: str, text: str) -> str:
        """Devuelve el texto coloreado con truecolor ANSI (fondo)."""
        hex_val = self._colors.get(color_key, "#000000")
        r, g, b = self.hex_to_rgb(hex_val)
        return f"\033[48;2;{r};{g};{b}m{text}\033[0m"

    def style(self, fg_key: str, bg_key: Optional[str], text: str, bold: bool = False) -> str:
        """Aplica estilos combinados de primer plano, fondo y negrita."""
        prefix = "\033[1m" if bold else ""
        fg_hex = self._colors.get(fg_key, "#ffffff")
        fr, fg_val, fb = self.hex_to_rgb(fg_hex)
        prefix += f"\033[38;2;{fr};{fg_val};{fb}m"

        if bg_key:
            bg_hex = self._colors.get(bg_key, "#000000")
            br, bg_val, bb = self.hex_to_rgb(bg_hex)
            prefix += f"\033[48;2;{br};{bg_val};{bb}m"

        return f"{prefix}{text}\033[0m"

    def get_theme_info(self, theme_name: str) -> Dict[str, Any]:
        """Obtiene la información (modo, colores, iconos) de cualquier tema Omarchy."""
        slug = self.normalize_theme_slug(theme_name)
        target_dir = self._find_theme_dir(slug)

        info: Dict[str, Any] = {
            "name": slug,
            "mode": "light" if "light" in slug else "dark",
            "accent": "#E31B23",
            "background": "#F4F6F8" if "light" in slug else "#08080B",
            "foreground": "#1A1A1E" if "light" in slug else "#d8d8d8",
            "selection": "#FADBD8" if "light" in slug else "#E31B23",
            "icons": "Lizarbe-Red",
            "icon_theme": "Lizarbe-Red",
        }
        if target_dir and target_dir.exists():
            c_file = target_dir / "colors.toml"
            if c_file.exists():
                try:
                    with open(c_file, "rb") as f:
                        data = tomllib.load(f)
                        for k in ("mode", "accent", "background", "foreground", "selection"):
                            if k in data and isinstance(data[k], str):
                                info[k] = data[k]
                except Exception:
                    pass
            i_file = target_dir / "icons.theme"
            if i_file.exists():
                try:
                    ic = i_file.read_text(encoding="utf-8").strip()
                    if ic:
                        info["icons"] = ic
                        info["icon_theme"] = ic
                except Exception:
                    pass
        return info

    def set_theme(self, theme_name: str) -> bool:
        """Activa el tema en Omarchy en tiempo real y recarga los colores de la interfaz."""
        slug = self.normalize_theme_slug(theme_name)
        # Si es lizarbe o lizarbe-light y no existe en ~/.config/omarchy/themes ni /usr/share/omarchy/themes, enlazar desde repo
        if slug in ("lizarbe", "lizarbe-light"):
            sys_t = self.system_themes_dir / slug
            usr_t = self.user_themes_dir / slug
            repo_t = self.repo_themes_dir / slug
            if not sys_t.exists() and not usr_t.exists() and repo_t.exists():
                try:
                    self.user_themes_dir.mkdir(parents=True, exist_ok=True)
                    usr_t.symlink_to(repo_t)
                except Exception:
                    pass

        for cmd in (["omarchy-theme-set", slug], ["omarchy", "theme", "set", slug]):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
                if res.returncode == 0:
                    self.reload()
                    return True
            except Exception:
                continue

        self.reload()
        return False

    def list_wallpapers_for_theme(self, theme_name: Optional[str] = None) -> List[str]:
        """Lista los nombres de los fondos de pantalla disponibles para el tema indicado."""
        t_name = theme_name or self.current_theme
        slug = self.normalize_theme_slug(t_name)
        dirs_to_check = [
            Path.home() / ".local" / "state" / "omarchy" / "current" / "theme" / "backgrounds",
            Path.home() / ".config" / "omarchy" / "backgrounds" / slug,
        ]
        t_dir = self._find_theme_dir(slug)
        if t_dir:
            dirs_to_check.insert(0, t_dir / "backgrounds")
        if (self.repo_themes_dir / slug / "backgrounds").exists():
            dirs_to_check.append(self.repo_themes_dir / slug / "backgrounds")

        names: List[str] = []
        for d in dirs_to_check:
            if d.exists() and d.is_dir():
                for f in sorted(d.iterdir()):
                    if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        if f.name not in names:
                            names.append(f.name)
        return names if names else ["predeterminado"]

    def get_current_wallpaper_name(self) -> str:
        """Obtiene el nombre del archivo de fondo actualmente activo en Omarchy."""
        bg_link = Path.home() / ".local" / "state" / "omarchy" / "current" / "background"
        if bg_link.exists() or bg_link.is_symlink():
            try:
                target = os.readlink(bg_link)
                return Path(target).name
            except Exception:
                pass
        wps = self.list_wallpapers_for_theme()
        return wps[0] if wps else "predeterminado"

    def set_wallpaper(self, filename: str, theme_name: Optional[str] = None) -> bool:
        """Aplica un fondo de pantalla específico mediante omarchy-theme-bg-set."""
        t_name = theme_name or self.current_theme
        slug = self.normalize_theme_slug(t_name)
        search_dirs = [
            Path.home() / ".local" / "state" / "omarchy" / "current" / "theme" / "backgrounds",
            Path.home() / ".config" / "omarchy" / "backgrounds" / slug,
        ]
        t_dir = self._find_theme_dir(slug)
        if t_dir:
            search_dirs.insert(0, t_dir / "backgrounds")
        if (self.repo_themes_dir / slug / "backgrounds").exists():
            search_dirs.append(self.repo_themes_dir / slug / "backgrounds")

        target_path: Optional[Path] = None
        for d in search_dirs:
            cand = d / filename
            if cand.exists() and cand.is_file():
                target_path = cand
                break

        if not target_path:
            return False

        try:
            res = subprocess.run(
                ["omarchy-theme-bg-set", str(target_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            return False
