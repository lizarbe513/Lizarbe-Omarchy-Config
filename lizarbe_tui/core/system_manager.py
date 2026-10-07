"""
Módulo de Gestión de Sistema, Dotfiles, Suites y Paquetes para Lizarbe Omarchy Theme.
Centraliza todas las funciones de lizarbe, lizarbe-apply-user, install.sh y uninstall.sh.
"""

from __future__ import annotations
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from lizarbe_tui.i18n import tr, trf


class SystemManager:
    OFFICIAL_REPO_URL = "https://lizarbe513.github.io/lizarbe-repo"

    # Definición de las 7 suites modulares de Lizarbe
    SUITES_SPEC: List[Tuple[str, str, str, str, str]] = [
        ("core", tr("Base & Tema Lizarbe"), tr("Tema, Iconos, GTK Darky, Zen, Fastfetch"), "pkgs-core.txt", "install-core.sh"),
        ("2d", tr("Suite Creativa 2D"), "Krita, LibreSprite, Inkscape, Pinta", "pkgs-2d.txt", "install-2d.sh"),
        ("3d", tr("Suite Creativa 3D & CAD"), tr("Blender, FreeCAD, Godot, Blockbench"), "pkgs-3d.txt", "install-3d.sh"),
        ("dev", tr("Suite de Desarrollo"), "VS Code, Git, Lazygit, Docker, Lazydocker", "pkgs-dev.txt", "install-dev.sh"),
        ("office", tr("Suite Ofimatica & Notas"), "genOffice, ONLYOFFICE, LibreOffice, Obsidian", "pkgs-office.txt", "install-office.sh"),
        ("multimedia", tr("Suite Multimedia"), "Kdenlive, Shotcut, OBS Studio, Audacity", "pkgs-multimedia.txt", "install-multimedia.sh"),
        ("webapps", tr("Webapps Omarchy"), tr("WhatsApp Web y YouTube"), "", "install-webapps.sh"),
    ]

    # Catálogo detallado de paquetes creativos (Sección Apps Creativas)
    CREATIVE_PKGS: List[Tuple[str, str, str, str]] = [
        # (categoria, pkg_name, nombre_visible, descripcion)
        (tr("SUITE CREATIVA 2D"), "krita", "Krita", tr("Pintura digital e ilustracion")),
        (tr("SUITE CREATIVA 2D"), "libresprite", "LibreSprite", tr("Animacion y pixel art")),
        (tr("SUITE CREATIVA 2D"), "inkscape", "Inkscape", tr("Diseño y graficos vectoriales")),
        (tr("SUITE CREATIVA 2D"), "pinta", "Pinta", tr("Retoque rapido de imagen")),
        (tr("SUITE CREATIVA 3D & CAD"), "blender", "Blender", tr("Modelado 3D, escultura y render")),
        (tr("SUITE CREATIVA 3D & CAD"), "freecad", "FreeCAD", tr("Diseño parametrico 3D y CAD")),
        (tr("SUITE CREATIVA 3D & CAD"), "godot", "Godot Engine", tr("Motor de videojuegos 2D y 3D")),
        (tr("SUITE CREATIVA 3D & CAD"), "blockbench-bin", "Blockbench", tr("Modelado 3D low-poly y voxeles")),
        (tr("SUITE MULTIMEDIA"), "kdenlive", "Kdenlive", tr("Edicion de video multipista")),
        (tr("SUITE MULTIMEDIA"), "shotcut", "Shotcut", tr("Editor de video rapido y ligero")),
        (tr("SUITE MULTIMEDIA"), "obs-studio", "OBS Studio", tr("Grabacion y streaming")),
        (tr("SUITE MULTIMEDIA"), "audacity", "Audacity", tr("Edicion de audio multipista")),
    ]

    # Catálogo detallado de paquetes de desarrollo, ofimática y base (Sección Apps Dev y Office)
    WORK_PKGS: List[Tuple[str, str, str, str]] = [
        (tr("DESARROLLO & CODIGO"), "visual-studio-code-bin", "Visual Studio Code", tr("Editor de codigo principal")),
        (tr("DESARROLLO & CODIGO"), "git", "Git", tr("Control de versiones distribuido")),
        (tr("DESARROLLO & CODIGO"), "lazygit", "Lazygit", tr("Cliente Git TUI interactivo")),
        (tr("DESARROLLO & CODIGO"), "docker", "Docker", tr("Motor de contenedores")),
        (tr("DESARROLLO & CODIGO"), "docker-compose", "Docker Compose", tr("Orquestacion multicontenedor")),
        (tr("DESARROLLO & CODIGO"), "lazydocker", "Lazydocker", tr("Panel TUI para contenedores Docker")),
        (tr("OFIMATICA & NOTAS"), "genoffice-bin", "genOffice", tr("Suite ofimatica moderna con IA")),
        (tr("OFIMATICA & NOTAS"), "onlyoffice-bin", "ONLYOFFICE Desktop", tr("Documentos, hojas y presentaciones")),
        (tr("OFIMATICA & NOTAS"), "libreoffice-fresh", "LibreOffice", tr("Suite ofimatica offline")),
        (tr("OFIMATICA & NOTAS"), "obsidian", "Obsidian", tr("Notas y proyectos en Markdown")),
        (tr("OFIMATICA & NOTAS"), "xournalpp", "Xournal++", tr("Notas manuscritas y PDF")),
    ]

    # Catálogo detallado de utilidades y herramientas (Sección Utilidades)
    UTIL_PKGS: List[Tuple[str, str, str, str]] = [
        (tr("NAVEGACION & WEB"), "zen-browser-bin", "Zen Browser", tr("Navegador web moderno, enfocado en rendimiento y privacidad")),
        (tr("PERSONALIZACION & GTK"), "nwg-look", "nwg-look", tr("Gestor y configurador visual de temas GTK e iconos")),
        (tr("TERMINAL & INFO"), "fastfetch", "Fastfetch", tr("Información del sistema con logo ASCII Lizarbe oficial")),
        (tr("MONITOREO DEL SISTEMA"), "htop", "htop", tr("Monitor interactivo de procesos y consumo de CPU/RAM")),
        (tr("MONITOREO DEL SISTEMA"), "btop", "btop", tr("Monitor de recursos con interfaz gráfica moderna y sensores")),
        (tr("TERMINALES"), "alacritty", "Alacritty", tr("Emulador de terminal acelerado por GPU y ultrarrápido")),
        (tr("TERMINALES"), "ghostty", "Ghostty", tr("Terminal nativa Wayland moderna con fuentes enriquecidas")),
        (tr("TRANSFERENCIA & RED"), "localsend-bin", "LocalSend", tr("Compartir archivos y fotos en red local sin internet")),
        (tr("LIMPIEZA & ESPACIO"), "bleachbit", "BleachBit", tr("Limpiador de archivos temporales, caché y espacio libre")),
        (tr("APARIENCIA COMPLEMENTARIA"), "yaru-icon-theme", "Yaru Icons", tr("Paquete de iconos complementarios de alta compatibilidad")),
    ]

    WEBAPPS_SPEC: List[Tuple[str, str, str, str]] = [
        # (id, nombre_visible, url, icon_name)
        ("WhatsApp", "WhatsApp Web", "https://web.whatsapp.com/", "whatsapp"),
        ("YouTube", "YouTube", "https://youtube.com/", "youtube"),
    ]

    def __init__(self, repo_dir: Optional[Path] = None):
        self.repo_dir = self._resolve_repo_dir(repo_dir)
        self.installed_pkgs: Set[str] = set()
        self.remote_hash_cache: str = tr("Pulsa Comprobar")
        self.sync_state_cache: str = tr("Verificacion bajo demanda")
        self._kdeconnect_devices_cache: List[Dict[str, Any]] = []
        self._kdeconnect_last_check: float = 0.0
        self.ensure_desktop_entry()
        self.refresh_installed_packages()

    @staticmethod
    def _resolve_repo_dir(explicit_dir: Optional[Path] = None) -> Path:
        if explicit_dir and explicit_dir.exists():
            return explicit_dir
        here = Path(__file__).resolve().parent.parent.parent
        if (here / "install.sh").exists():
            return here
        pkg_dir = Path("/usr/lib/lizarbe-centro")
        if (pkg_dir / "install.sh").exists():
            return pkg_dir
        return here

    def refresh_installed_packages(self) -> Set[str]:
        """Obtiene todos los paquetes instalados en el sistema en una sola llamada rápida a pacman."""
        try:
            res = subprocess.run(
                ["pacman", "-Qq"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                self.installed_pkgs = {line.strip() for line in res.stdout.splitlines() if line.strip()}
        except Exception:
            pass
        return self.installed_pkgs

    def is_package_installed(self, pkg_name: str) -> bool:
        """Verifica si un paquete de pacman/AUR está instalado."""
        if pkg_name in self.installed_pkgs:
            return True
        # Comprobar variantes sin -bin o con -bin por si el usuario instaló otra variante
        alt = pkg_name[:-4] if pkg_name.endswith("-bin") else f"{pkg_name}-bin"
        if alt in self.installed_pkgs:
            return True
        return False

    def is_webapp_installed(self, webapp_id: str) -> bool:
        """Verifica si una webapp de Omarchy existe en ~/.local/share/applications/."""
        app_dir = Path.home() / ".local" / "share" / "applications"
        candidates = [
            app_dir / f"{webapp_id}.desktop",
            app_dir / f"{webapp_id.lower()}.desktop",
            app_dir / f"omarchy-{webapp_id.lower()}.desktop",
        ]
        if any(c.exists() for c in candidates):
            return True
        if app_dir.exists():
            for f in app_dir.glob("*.desktop"):
                if webapp_id.lower() in f.name.lower():
                    return True
        return False

    def get_suite_packages(self, suite_id: str) -> List[str]:
        """Lee la lista de paquetes asociada a una suite desde packages/pkgs-<id>.txt."""
        for s_id, _, _, pkg_file, _ in self.SUITES_SPEC:
            if s_id == suite_id and pkg_file:
                p_path = self.repo_dir / "packages" / pkg_file
                if p_path.exists():
                    pkgs: List[str] = []
                    for line in p_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                        clean = line.split("#", 1)[0].strip()
                        if clean:
                            pkgs.append(clean)
                    return pkgs
        return []

    def get_suite_status(self, suite_id: str) -> Tuple[bool, int, int]:
        """
        Devuelve (is_active, installed_count, total_count) para una suite.
        Se considera activa si al menos la mitad o todos los paquetes principales están instalados.
        """
        if suite_id == "webapps":
            total = len(self.WEBAPPS_SPEC)
            inst = sum(1 for w_id, _, _, _ in self.WEBAPPS_SPEC if self.is_webapp_installed(w_id))
            return (inst == total and total > 0), inst, total

        pkgs = self.get_suite_packages(suite_id)
        if not pkgs:
            return False, 0, 0
        inst = sum(1 for p in pkgs if self.is_package_installed(p))
        total = len(pkgs)
        if suite_id == "core":
            core_ok = self.is_lizarbe_theme_installed() and self.is_icons_installed()
            return (core_ok and inst >= max(1, total - 1)), inst, total
        return (inst == total and total > 0), inst, total

    # =========================================================================
    # COMPROBACIONES DE ESTADO DE DOTFILES Y TEMA
    # =========================================================================

    def is_lizarbe_theme_installed(self) -> bool:
        return (
            (Path("/usr/share/omarchy/themes/lizarbe").exists())
            or (Path.home() / ".config" / "omarchy" / "themes" / "lizarbe").exists()
        )

    def is_icons_installed(self) -> bool:
        return (
            (Path.home() / ".local" / "share" / "icons" / "Lizarbe-Red").exists()
            or Path("/usr/share/icons/Lizarbe-Red").exists()
        )

    def is_gtk_darky_installed(self) -> bool:
        return (
            (Path.home() / ".local" / "share" / "themes" / "Darky").exists()
            or Path("/usr/share/themes/Darky").exists()
        )

    def is_fastfetch_configured(self) -> bool:
        logo_f = Path.home() / ".config" / "fastfetch" / "logo.txt"
        cfg_f = Path.home() / ".config" / "fastfetch" / "config.jsonc"
        return logo_f.exists() and cfg_f.exists()

    def is_starship_configured(self) -> bool:
        st_f = Path.home() / ".config" / "starship.toml"
        return st_f.exists()

    def is_branding_configured(self) -> bool:
        br_dir = Path.home() / ".config" / "omarchy" / "branding"
        return (br_dir / "about.txt").exists() or (br_dir / "screensaver.txt").exists()

    def is_desktop_entry_installed(self) -> bool:
        return (
            (Path.home() / ".local" / "share" / "applications" / "lizarbe.desktop").exists()
            or Path("/usr/share/applications/lizarbe.desktop").exists()
        )

    REPO_DB_URL = "https://lizarbe513.github.io/lizarbe-repo/x86_64/lizarbe.db"

    def get_local_git_hash(self) -> str:
        """Versión instalada del paquete `lizarbe` (el nombre se conserva por compatibilidad)."""
        try:
            res = subprocess.run(["pacman", "-Q", "lizarbe"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.split():
                return res.stdout.split()[1]
        except Exception:
            pass
        return tr("sin paquete")

    def _fetch_repo_versions(self) -> Dict[str, str]:
        """Versiones publicadas en el repositorio de Lizarbe (lee lizarbe.db en línea)."""
        import io
        import tarfile
        import urllib.request

        with urllib.request.urlopen(self.REPO_DB_URL, timeout=5) as r:
            data = r.read()
        out: Dict[str, str] = {}
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for name in tf.getnames():
                if "/" in name:
                    continue
                m = re.match(r"^(.+)-([^-]+-[^-]+)$", name)
                if m:
                    out[m.group(1)] = m.group(2)
        return out

    def check_remote_version(self) -> Tuple[bool, str, str]:
        """Compara los paquetes lizarbe-* instalados con los del repositorio en línea."""
        try:
            published = self._fetch_repo_versions()
            res = subprocess.run(["pacman", "-Q"], capture_output=True, text=True, timeout=3)
            installed = dict(
                line.split()[:2] for line in res.stdout.splitlines() if line.split() and line.split()[0] in published
            )
            pending = [n for n, v in installed.items() if v != published[n]]
            self.remote_hash_cache = published.get("lizarbe", "?")
            if pending:
                self.sync_state_cache = trf("Update disponible ({names})", names=", ".join(sorted(pending)))
            else:
                self.sync_state_cache = trf("Al dia ({remote_hash_cache})", remote_hash_cache=self.remote_hash_cache)
            return True, self.remote_hash_cache, self.sync_state_cache
        except Exception:
            pass
        self.remote_hash_cache = tr("Sin conexion")
        self.sync_state_cache = tr("Sin conexion al repositorio de Lizarbe")
        return False, self.remote_hash_cache, self.sync_state_cache

    def load_settings_dict(self, current_theme: str, current_wallpaper: str) -> Dict[str, Any]:
        """Carga el estado completo del sistema y las suites en un diccionario para el TUI."""
        self.refresh_installed_packages()
        s: Dict[str, Any] = {
            "active_theme": current_theme,
            "wallpaper": current_wallpaper,
            "icons_lizarbe": self.is_icons_installed(),
            "gtk_darky": self.is_gtk_darky_installed(),
            "fastfetch": self.is_fastfetch_configured(),
            "starship": self.is_starship_configured(),
            "branding": self.is_branding_configured(),
            "zen_default": self.is_package_installed("zen-browser-bin"),
            "desktop_entry": self.is_desktop_entry_installed(),
        }
        for s_id, _, _, _, _ in self.SUITES_SPEC:
            is_on, _, _ = self.get_suite_status(s_id)
            s[f"suite:{s_id}"] = is_on

        for _, pkg, _, _ in self.CREATIVE_PKGS + self.WORK_PKGS:
            s[f"pkg:{pkg}"] = self.is_package_installed(pkg)

        for w_id, _, _, _ in self.WEBAPPS_SPEC:
            s[f"webapp:{w_id}"] = self.is_webapp_installed(w_id)

        return s

    # =========================================================================
    # ACCIONES DE CONFIGURACIÓN DE USUARIO Y DOTFILES (SIN SUDO)
    # =========================================================================

    @staticmethod
    def _asset(dev: Path, system: Path) -> Path:
        """Ruta de un recurso: la del código fuente si existe, si no la del paquete lizarbe-tema."""
        return dev if dev.exists() else system

    def apply_icons_user(self, enable: bool = True) -> bool:
        """Enlaza o desenlaza el pack de iconos Lizarbe-Red en el directorio del usuario."""
        user_icons = Path.home() / ".local" / "share" / "icons" / "Lizarbe-Red"
        dot_icons = Path.home() / ".icons" / "Lizarbe-Red"
        try:
            if enable:
                src = self.repo_dir / "icons" / "Lizarbe-Red"
                if not src.exists():
                    src = Path("/usr/share/icons/Lizarbe-Red")
                if not src.exists():
                    return False
                user_icons.parent.mkdir(parents=True, exist_ok=True)
                dot_icons.parent.mkdir(parents=True, exist_ok=True)
                if user_icons.exists() or user_icons.is_symlink():
                    if user_icons.is_symlink() or user_icons.is_file():
                        user_icons.unlink()
                    else:
                        shutil.rmtree(user_icons)
                if dot_icons.exists() or dot_icons.is_symlink():
                    if dot_icons.is_symlink() or dot_icons.is_file():
                        dot_icons.unlink()
                    else:
                        shutil.rmtree(dot_icons)
                user_icons.symlink_to(src)
                dot_icons.symlink_to(src)
                proj_dir = Path.home() / "Projects"
                if proj_dir.exists() and shutil.which("gio"):
                    subprocess.run(
                        ["gio", "set", "-t", "string", str(proj_dir), "metadata::custom-icon-name", "folder-projects"],
                        capture_output=True,
                        timeout=3,
                    )
            else:
                for p in (user_icons, dot_icons):
                    if p.is_symlink() or p.is_file():
                        p.unlink()
            return True
        except Exception:
            return False

    def apply_gtk_darky_user(self, enable: bool = True) -> bool:
        """Enlaza o desenlaza el tema GTK Darky en ~/.local/share/themes."""
        user_darky = Path.home() / ".local" / "share" / "themes" / "Darky"
        try:
            if enable:
                src = Path("/usr/share/themes/Darky")
                if not src.exists():
                    src = self.repo_dir / "themes" / "Darky"
                if not src.exists():
                    return False
                user_darky.parent.mkdir(parents=True, exist_ok=True)
                if user_darky.exists() or user_darky.is_symlink():
                    if user_darky.is_symlink() or user_darky.is_file():
                        user_darky.unlink()
                    else:
                        shutil.rmtree(user_darky)
                user_darky.symlink_to(src)
                # Limpiar enlaces estáticos en gtk-4.0
                gtk4_dir = Path.home() / ".config" / "gtk-4.0"
                for name in ("gtk.css", "gtk-dark.css", "assets"):
                    f = gtk4_dir / name
                    if f.is_symlink() and "Darky" in str(f.resolve()):
                        f.unlink()
            else:
                if user_darky.is_symlink() or user_darky.is_file():
                    user_darky.unlink()
            return True
        except Exception:
            return False

    def apply_fastfetch_user(self, enable: bool = True) -> bool:
        """Copia o remueve la configuración de Fastfetch con el logo ASCII de Lizarbe."""
        ff_dir = Path.home() / ".config" / "fastfetch"
        src_dir = self._asset(self.repo_dir / "config" / "fastfetch", Path("/etc/xdg/fastfetch"))
        try:
            if enable:
                ff_dir.mkdir(parents=True, exist_ok=True)
                if src_dir.exists():
                    for f in src_dir.iterdir():
                        if f.is_file():
                            shutil.copy2(f, ff_dir / f.name)
                return True
            else:
                logo_f = ff_dir / "logo.txt"
                if logo_f.exists():
                    logo_f.unlink()
                return True
        except Exception:
            return False

    def apply_starship_user(self, enable: bool = True) -> bool:
        """Copia la configuración de Starship en ~/.config/starship.toml."""
        st_dest = Path.home() / ".config" / "starship.toml"
        st_src = self._asset(self.repo_dir / "config" / "starship.toml", Path("/etc/starship.toml"))
        try:
            if enable and st_src.exists():
                st_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(st_src, st_dest)
            return True
        except Exception:
            return False

    def apply_branding_user(self, enable: bool = True) -> bool:
        """Copia o remueve el branding de Omarchy en ~/.config/omarchy/branding."""
        br_dest = Path.home() / ".config" / "omarchy" / "branding"
        br_src = self._asset(self.repo_dir / "config" / "omarchy" / "branding", Path("/usr/share/omarchy/branding"))
        try:
            if enable:
                br_dest.mkdir(parents=True, exist_ok=True)
                if br_src.exists():
                    for f in br_src.iterdir():
                        if f.is_file():
                            shutil.copy2(f, br_dest / f.name)
            else:
                for name in ("about.txt", "logo.png", "screensaver.txt"):
                    f = br_dest / name
                    if f.exists():
                        f.unlink()
            return True
        except Exception:
            return False

    def ensure_desktop_entry(self) -> bool:
        """En desarrollo (sin paquete) registra lizarbe.desktop y lizarbe-tui en el usuario."""
        if Path("/usr/share/applications/lizarbe.desktop").exists() and Path("/usr/bin/lizarbe-tui").exists():
            return True
        app_dir = Path.home() / ".local" / "share" / "applications"
        bin_dir = Path.home() / ".local" / "bin"
        dest = app_dir / "lizarbe.desktop"
        src = self.repo_dir / "lizarbe.desktop"
        lizarbe_script = self.repo_dir / "lizarbe"
        try:
            bin_dir.mkdir(parents=True, exist_ok=True)
            if lizarbe_script.exists():
                for b_name in ("lizarbe", "lizarbe-tui"):
                    b_target = bin_dir / b_name
                    if not b_target.exists() or b_target.is_symlink():
                        if b_target.exists() or b_target.is_symlink():
                            b_target.unlink()
                        b_target.symlink_to(lizarbe_script)

            app_dir.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy2(src, dest)
            else:
                content = """[Desktop Entry]
Name=Lizarbe Theme
GenericName=Gestor de Tema y Suites Lizarbe
Comment=Panel TUI para gestionar el Tema Lizarbe, Apariencia y Suites de Software en Omarchy
Exec=omarchy-launch-tui --app-id=org.omarchy.lizarbe lizarbe-tui
Icon=preferences-desktop-theme
Terminal=false
Type=Application
Categories=Settings;DesktopSettings;System;
Keywords=lizarbe;omarchy;theme;tema;suites;config;tui;hyprland;
"""
                dest.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def run_apply_user_script(self, target_theme: Optional[str] = None) -> bool:
        """Ejecuta lizarbe-apply-user para sincronizar todos los enlaces, dotfiles y el tema."""
        script = Path("/usr/bin/lizarbe-apply-user")
        if not script.exists():
            script = self.repo_dir / "lizarbe-apply-user"
        if script.exists():
            cmd = ["bash", str(script), os.environ.get("USER", "")]
            if target_theme:
                cmd.append(target_theme)
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                return res.returncode == 0
            except Exception:
                return False
        return False

    def install_or_remove_webapp(self, webapp_id: str, install: bool) -> bool:
        """Instala o remueve una Webapp de Omarchy (WhatsApp o YouTube)."""
        spec = next((w for w in self.WEBAPPS_SPEC if w[0] == webapp_id), None)
        if not spec:
            return False
        w_id, _, w_url, w_icon = spec
        try:
            if install:
                if shutil.which("omarchy-webapp-install"):
                    res = subprocess.run(
                        ["omarchy-webapp-install", w_id, w_url, w_icon],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    return res.returncode == 0
            else:
                if shutil.which("omarchy-webapp-remove"):
                    subprocess.run(
                        ["omarchy-webapp-remove", w_id],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                desktop_f = Path.home() / ".local" / "share" / "applications" / f"{w_id}.desktop"
                if desktop_f.exists():
                    desktop_f.unlink()
                return True
        except Exception:
            pass
        return False

    def is_kdeconnect_installed(self) -> bool:
        """Verifica si el paquete kdeconnect o el binario kdeconnect-cli está instalado."""
        return self.is_package_installed("kdeconnect") or bool(shutil.which("kdeconnect-cli"))

    def is_kdeconnect_daemon_running(self) -> bool:
        """Comprueba si el demonio o servicio de KDE Connect está activo."""
        try:
            res = subprocess.run(["pgrep", "-x", "kdeconnectd"], capture_output=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass
        try:
            res = subprocess.run(["systemctl", "--user", "is-active", "kdeconnect"], capture_output=True, text=True)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def is_ufw_active(self) -> bool:
        """Comprueba si el cortafuegos UFW está activo en el sistema."""
        try:
            res = subprocess.run(["systemctl", "is-active", "ufw"], capture_output=True, text=True)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def is_kdeconnect_firewall_allowed(self) -> bool:
        """Comprueba si los puertos 1714-1764 están permitidos en UFW."""
        if not self.is_ufw_active():
            return True
        try:
            content = Path("/etc/ufw/user.rules").read_text(encoding="utf-8")
            return "1714" in content
        except Exception:
            return False

    def start_or_restart_kdeconnect(self) -> bool:
        """Inicia o reinicia el demonio de KDE Connect."""
        try:
            subprocess.run(["systemctl", "--user", "restart", "kdeconnect"], capture_output=True, timeout=5)
            return True
        except Exception:
            pass
        try:
            subprocess.Popen(["kdeconnect-indicator"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
        if Path("/usr/lib/kdeconnectd").exists():
            try:
                subprocess.Popen(["/usr/lib/kdeconnectd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
        return False

    def get_kdeconnect_devices(self, force: bool = False) -> List[Dict[str, Any]]:
        """Obtiene la lista de dispositivos móviles detectados/vinculados vía kdeconnect-cli."""
        if not self.is_kdeconnect_installed():
            return []
        if not force and (time.time() - self._kdeconnect_last_check < 3.0):
            return self._kdeconnect_devices_cache
        devices: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["kdeconnect-cli", "-l"], capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    raw = line[2:].strip()
                    if ":" in raw:
                        name, rest = raw.split(":", 1)
                        name = name.strip()
                        rest = rest.strip()
                        m_st = re.search(r"\(([^)]+)\)\s*$", rest)
                        status_str = m_st.group(1).strip().lower() if m_st else ""
                        before_parens = rest[:m_st.start()].strip() if m_st else rest
                        d_id = before_parens.split()[0] if before_parens else ""
                        is_paired = "paired" in status_str
                        is_reachable = "reachable" in status_str or not status_str
                        if d_id and name:
                            devices.append({
                                "id": d_id,
                                "name": name,
                                "paired": is_paired,
                                "reachable": is_reachable,
                                "status": status_str,
                            })
        except Exception:
            pass
        self._kdeconnect_devices_cache = devices
        self._kdeconnect_last_check = time.time()
        return devices

    def ring_kdeconnect_device(self, dev_id: str = "") -> bool:
        """Hace sonar el smartphone especificado o el primer smartphone vinculado/disponible."""
        if not dev_id:
            devs = self.get_kdeconnect_devices(force=True)
            paired = [d for d in devs if d.get("paired")]
            target = paired[0]["id"] if paired else (devs[0]["id"] if devs else "")
        else:
            target = dev_id
        if not target:
            return False
        try:
            res = subprocess.run(["kdeconnect-cli", "--ring", "-d", target], capture_output=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def ping_kdeconnect(self, dev_id: str = "") -> bool:
        """Envía una señal ping al smartphone especificado o a los smartphones vinculados."""
        if not dev_id:
            devs = self.get_kdeconnect_devices(force=True)
            targets = [d["id"] for d in devs if d.get("paired")] or [d["id"] for d in devs]
        else:
            targets = [dev_id]
        if not targets:
            return False
        ok = False
        for tid in targets:
            try:
                res = subprocess.run(["kdeconnect-cli", "--ping", "-d", tid], capture_output=True, timeout=5)
                if res.returncode == 0:
                    ok = True
            except Exception:
                pass
        return ok

    def pair_kdeconnect_device(self, dev_id: str) -> bool:
        try:
            subprocess.run(["kdeconnect-cli", "--pair", "-d", dev_id], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def open_kdeconnect_gui(self) -> bool:
        for app in ["lizarbe-kdeconnect", "kdeconnect-app", "kdeconnect-settings", "kdeconnect-indicator"]:
            if shutil.which(app):
                try:
                    subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    pass
        return False

