"""
Interfaz TUI Monolítica para Lizarbe Omarchy Theme (Estilo Meca HyprConfig / HyprMod).
Arquitectura de 2 paneles (Categorías a la izquierda, Controles y Acciones de Lizarbe a la derecha),
con soporte completo de ratón, menús desplegables, tarjetas de temas, controles en cuadrados cerrados,
menú contextual de clic derecho y modales interactivos de confirmación.
"""

from __future__ import annotations
import os
import re
import sys
import tty
import termios
import select
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from lizarbe_tui.core.theme_engine import ThemeEngine
from lizarbe_tui.core.hypr_ipc import HyprIPC
from lizarbe_tui.core.system_manager import SystemManager
from lizarbe_tui.i18n import tr, trf



def _label_has(label: str, *keys: str) -> bool:
    """¿El texto contiene alguna de las palabras (en español o ya traducidas)?"""
    low = label.lower()
    return any(k.lower() in low or tr(k).lower() in low for k in keys)


class SectionItem:
    """Representa una variable, acción, encabezado, tarjeta de tema o tarjeta de aplicación."""
    def __init__(
        self,
        key: str,
        name: str,
        desc: str,
        item_type: str,  # "toggle", "select", "action", "header", "theme_card", "info_badge", "app_card"
        options: Optional[List[str]] = None,
        action_label: str = " Ejecutar ",
        is_installed: bool = False,
        pkg_name: str = "",
        category: str = "",
        icon: str = "",
    ):
        self.key = key
        self.name = name
        self.desc = desc
        self.item_type = item_type
        self.options = options or []
        self.action_label = tr(action_label) if action_label == " Ejecutar " else action_label
        self.is_installed = is_installed
        self.pkg_name = pkg_name
        self.category = category
        self.icon = icon


class LizarbeTUI:
    """
    Centro Lizarbe: identidad, software y actualizaciones de Lizarbe OS.
    Comparte la arquitectura, proporciones y controles de Meca HyprConfig.
    """

    SECTIONS = [
        (tr("SISTEMA LIZARBE"), "status", "󰚰", tr("Actualizaciones"), tr("Monitor del equipo y parches oficiales")),
        (tr("SISTEMA LIZARBE"), "theme", "󰏘", tr("Iconos y GTK"), tr("Iconos Lizarbe-Red y tema Darky")),
        (tr("SISTEMA LIZARBE"), "dotfiles", "", tr("Personalizacion"), tr("Fastfetch, Starship y branding")),
        (tr("SOFTWARE Y APPS"), "apps_util", "󰣆", tr("Utilidades"), tr("Zen Browser, monitores y herramientas")),
        (tr("SOFTWARE Y APPS"), "kdeconnect", "󰄡", "KDE Connect", tr("Vincular y sincronizar con tu smartphone")),
        (tr("SOFTWARE Y APPS"), "apps_creative", "", tr("Apps Creativas"), tr("Ilustracion 2D, 3D, CAD y Video")),
        (tr("SOFTWARE Y APPS"), "apps_work", "", tr("Apps Dev y Office"), tr("Desarrollo, Ofimatica y Webapps")),
        (tr("SOFTWARE Y APPS"), "suites", "󰏖", tr("Suites Lizarbe"), tr("Instalacion modular por suites")),
        (tr("MANTENIMIENTO"), "uninstall", "󰆴", tr("Desinstalacion"), tr("Revertir tema o remover componentes")),
    ]

    def __init__(self, was_tiled: Optional[bool] = None):
        self.sys_mgr = SystemManager()
        self.theme_engine = ThemeEngine(repo_dir=self.sys_mgr.repo_dir)
        self.running = True
        self._frame_count = 0
        self._was_tiled = was_tiled
        self.orig_termios = None

        # Asegurar que exista el archivo .desktop en el centro de aplicaciones del usuario
        self.sys_mgr.ensure_desktop_entry()

        # Navegación de paneles: "sidebar" (izquierda), "content" (derecha) o "buttons" (barra inferior)
        self.active_pane = "sidebar"
        self.current_section_idx = 0
        self.selected_item_idx = 0
        self.content_scroll_offset = 0
        self.status_message = tr("Listo.")

        # Datos cargados del sistema
        self.available_themes = self.theme_engine.list_available_themes()
        self.available_wallpapers = self.theme_engine.list_wallpapers_for_theme()
        self.settings = self.sys_mgr.load_settings_dict(
            current_theme=self.theme_engine.current_theme,
            current_wallpaper=self.theme_engine.get_current_wallpaper_name(),
        )
        self.saved_settings = dict(self.settings)

        # Estado del menú desplegable (dropdown) para controles de tipo "select"
        self.dropdown_open: bool = False
        self.dropdown_item: Optional[SectionItem] = None
        self.dropdown_options: List[str] = []
        self.dropdown_idx: int = 0
        self.dropdown_scroll: int = 0
        self.hover_dropdown_idx: Optional[int] = None
        self.dropdown_anchor_y: int = 6
        self.dropdown_anchor_x: int = 40
        self._dropdown_row_map: Dict[int, int] = {}
        self._dropdown_box_bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)

        # Estado del menú contextual de clic secundario (clic derecho / tecla m)
        self.context_menu_open: bool = False
        self.context_menu_x: int = 24
        self.context_menu_y: int = 10
        self.context_menu_items: List[Tuple[str, str]] = []
        self.context_menu_idx: int = 0
        self.hover_context_idx: Optional[int] = None
        self._context_row_map: Dict[int, int] = {}
        self._context_box_bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self.context_menu_target_key: str = ""

        # Estado de ventana modal:
        # None | "confirm_section_change" | "confirm_reset" | "confirm_command" | "kdeconnect_guide"
        self.modal_state: Optional[str] = None
        self.modal_selected_idx: int = 0
        self.pending_section_idx: Optional[int] = None
        self.pending_focus_content: bool = False
        self._pending_cmd_title: str = ""
        self._pending_cmd_msg1: str = ""
        self._pending_cmd_msg2: str = ""
        self._pending_cmd_args: List[str] = []
        self._modal_button_click_map: Dict[int, Tuple[int, int]] = {}
        self._modal_button_row_range: Tuple[int, int] = (0, 0)
        self.guide_scroll_offset: int = 0
        self._guide_lines: List[Tuple[str, str]] = []
        self._guide_content_h: int = 20
        self._guide_box_bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)

        # Mapeos de coordenadas para interacción con el ratón y estado hover
        self._sidebar_click_map: Dict[int, int] = {}
        self._content_click_map: Dict[int, Dict[str, Any]] = {}
        self._button_click_map: Dict[str, Tuple[int, int]] = {}
        self._button_row_range: Tuple[int, int] = (0, 0)
        self.selected_button_idx = 2  # 0: Restablecer, 1: Cancelar, 2: Aplicar
        self.hover_sidebar_idx: Optional[int] = None
        self.hover_item_idx: Optional[int] = None
        self.hover_subcontrol: Optional[str] = None
        self.hover_button_key: Optional[str] = None
        self.hover_modal_btn_idx: Optional[int] = None

        self.section_items = self._init_section_items()

    def _refresh_all_state(self) -> None:
        """Recarga el tema activo, lista de fondos, paquetes instalados y estado del sistema."""
        self.theme_engine.reload()
        self.available_themes = self.theme_engine.list_available_themes()
        sel_t = self.theme_engine.current_theme
        self.available_wallpapers = self.theme_engine.list_wallpapers_for_theme(sel_t)
        self.settings = self.sys_mgr.load_settings_dict(
            current_theme=sel_t,
            current_wallpaper=self.theme_engine.get_current_wallpaper_name(),
        )
        self.saved_settings = dict(self.settings)
        self.section_items = self._init_section_items()

    def _build_theme_section_items(self) -> List[SectionItem]:
        sel_t = str(self.settings.get("active_theme", self.theme_engine.current_theme))
        wps = self.theme_engine.list_wallpapers_for_theme(sel_t)
        cur_wp = str(self.settings.get("wallpaper", self.theme_engine.get_current_wallpaper_name()))
        if cur_wp and cur_wp not in wps:
            wps.insert(0, cur_wp)

        return [
            SectionItem(
                "header:theme_controls",
                tr("ICONOS Y GTK"),
                tr("Para cambiar de tema o fondo usa Menú > Apariencia en Omarchy"),
                "header",
            ),
            SectionItem(
                "icons_lizarbe",
                tr("Iconos Lizarbe-Red"),
                tr("Pack de iconos y carpeta Projects"),
                "toggle",
            ),
            SectionItem(
                "gtk_darky",
                tr("Tema GTK Darky"),
                tr("Enlazar tema Darky en el usuario"),
                "toggle",
            ),
            SectionItem(
                "action:open_nwg_look",
                tr("Abrir nwg-look"),
                tr("Configurador visual de temas GTK"),
                "action",
                action_label=tr(" Abrir "),
            ),
            SectionItem(
                "action:apply_user_now",
                tr("Reaplicar tema completo"),
                tr("Ejecutar lizarbe-apply-user ahora"),
                "action",
                action_label=tr(" Reaplicar "),
            ),
        ]

    def _build_dotfiles_section_items(self) -> List[SectionItem]:
        return [
            SectionItem(
                "header:dotfiles_toggles",
                tr("DOTFILES Y PERSONALIZACION"),
                tr("Activa o desactiva componentes y pulsa Aplicar"),
                "header",
            ),
            SectionItem(
                "fastfetch",
                tr("Fastfetch Lizarbe"),
                tr("Logo ASCII personalizado y config.jsonc"),
                "toggle",
            ),
            SectionItem(
                "starship",
                tr("Prompt Starship"),
                tr("Estilo limpio en ~/.config/starship.toml"),
                "toggle",
            ),
            SectionItem(
                "branding",
                tr("Branding Omarchy"),
                tr("Logo, about y salvapantallas Lizarbe"),
                "toggle",
            ),
            SectionItem(
                "header:dotfiles_actions",
                tr("ACCIONES RAPIDAS DEL ENTORNO"),
                tr("Aplicacion directa de utilidades del sistema"),
                "header",
            ),
            SectionItem(
                "action:set_zen_default",
                tr("Zen Browser predeterminado"),
                tr("Establecer Zen como navegador del sistema"),
                "action",
                action_label=tr(" Configurar "),
            ),
            SectionItem(
                "action:restart_shell",
                tr("Reiniciar Barra Superior"),
                tr("Recargar Quickshell (omarchy-restart-shell)"),
                "action",
                action_label=tr(" Reiniciar "),
            ),
        ]

    def _build_status_section_items(self) -> List[SectionItem]:
        local_hash = self.sys_mgr.get_local_git_hash()
        rem_hash = self.sys_mgr.remote_hash_cache
        sync_txt = self.sys_mgr.sync_state_cache

        pending_states = (tr("Pulsa Comprobar"), tr("Sin conexion"), "Verificacion bajo demanda")
        is_checked = bool(rem_hash and rem_hash not in pending_states and rem_hash not in [tr(x) for x in pending_states])
        is_up_to_date = (local_hash == rem_hash) if is_checked else _label_has(sync_txt, "Al dia")

        if is_checked and is_up_to_date:
            banner_title = tr("TU EQUIPO LIZARBE ESTA AL DIA")
            banner_desc = trf("Version oficial ({local_hash}) activa. No hay parches pendientes.", local_hash=local_hash)
            banner_action = "action:check_remote"
            banner_btn = tr(" Comprobar ")
        elif is_checked and not is_up_to_date:
            banner_title = tr("ACTUALIZACION DISPONIBLE PARA TU EQUIPO")
            banner_desc = trf("Nuevos parches en el servidor ({local_hash} -> {rem_hash}). Pulsa Actualizar.", local_hash=local_hash, rem_hash=rem_hash)
            banner_action = "action:update_github"
            banner_btn = tr(" Actualizar ")
        else:
            banner_title = tr("MONITOR DE ACTUALIZACIONES LIZARBE OS")
            banner_desc = trf("Estado: {sync_txt}. Pulsa 'Buscar Actualizaciones' para consultar GitHub.", sync_txt=sync_txt)
            banner_action = "action:check_remote"
            banner_btn = tr(" Comprobar ")

        root_theme = tr("Instalado") if Path("/usr/share/omarchy/themes/lizarbe").exists() else tr("No instalado")
        root_icons = tr("Instalados") if Path("/usr/share/icons/Lizarbe-Red").exists() else tr("No encontrados")
        root_darky = tr("Instalado") if Path("/usr/share/themes/Darky").exists() else tr("No encontrado")

        return [
            SectionItem(
                "header:update_banner",
                tr("ESTADO GENERAL DE ACTUALIZACION"),
                tr("Monitor oficial para usuarios de computadoras Lizarbe"),
                "header",
            ),
            SectionItem(
                banner_action,
                banner_title,
                banner_desc,
                "action",
                action_label=banner_btn,
            ),
            SectionItem(
                "header:update_actions",
                tr("ACCIONES DE MANTENIMIENTO DEL EQUIPO"),
                tr("Sincronizar y reparar componentes oficiales"),
                "header",
            ),
            SectionItem(
                "action:update_github",
                tr("Actualizar sistema (omarchy update)"),
                tr("Actualiza Omarchy y todos los paquetes de Lizarbe"),
                "action",
                action_label=tr(" Actualizar "),
            ),
            SectionItem(
                "action:check_remote",
                tr("Buscar Actualizaciones Ahora"),
                trf("Repositorio: {OFFICIAL_REPO_URL}", OFFICIAL_REPO_URL=self.sys_mgr.OFFICIAL_REPO_URL),
                "action",
                action_label=tr(" Comprobar "),
            ),
            SectionItem(
                "action:update_force",
                tr("Reparar integración de Lizarbe"),
                tr("Revisa el menú, reglas de ventana y archivos de Lizarbe y los arregla"),
                "action",
                action_label=tr(" Reparar "),
            ),
            SectionItem(
                "header:system_info",
                tr("COMPONENTES OFICIALES MONITOREADOS"),
                trf("Equipo Lizarbe • Repositorio: {name}", name=self.sys_mgr.repo_dir.name),
                "header",
            ),
            SectionItem(
                "info:local_version",
                tr("Versión local instalada"),
                trf("Versión del paquete en esta máquina: {local_hash}", local_hash=local_hash),
                "info_badge",
                action_label=f" {local_hash} ",
            ),
            SectionItem(
                "info:root_theme",
                tr("Temas en /usr/share/omarchy"),
                tr("Lizarbe Dark y Lizarbe Light globales"),
                "info_badge",
                action_label=f" {root_theme} ",
            ),
            SectionItem(
                "info:root_icons",
                tr("Iconos en /usr/share/icons"),
                tr("Paquete global Lizarbe-Red"),
                "info_badge",
                action_label=f" {root_icons} ",
            ),
            SectionItem(
                "info:root_darky",
                tr("Tema GTK Darky en /usr/share"),
                tr("Tema GTK3/GTK4 en la raíz del sistema"),
                "info_badge",
                action_label=f" {root_darky} ",
            ),
        ]

    def _build_suites_section_items(self) -> List[SectionItem]:
        items: List[SectionItem] = [
            SectionItem(
                "header:suites_modular",
                tr("SELECCION DE SUITES DE SOFTWARE"),
                tr("Marca las suites deseadas y pulsa Aplicar (Clic der: Accion directa)"),
                "header",
            ),
        ]
        for s_id, s_name, s_desc, _, _ in self.sys_mgr.SUITES_SPEC:
            _, inst, total = self.sys_mgr.get_suite_status(s_id)
            badge = f"[{inst}/{total}] {s_desc}"
            items.append(
                SectionItem(
                    f"suite:{s_id}",
                    s_name,
                    badge,
                    "toggle",
                )
            )

        items.extend([
            SectionItem(
                "header:suites_presets",
                tr("PERFILES DE INSTALACION RAPIDA (INSTALL.SH)"),
                tr("Ejecucion guiada de perfiles completos de instalacion"),
                "header",
            ),
            SectionItem(
                "action:install_all",
                tr("Instalar Todo (--all)"),
                tr("Base + todas las suites (incluye 3D & CAD)"),
                "action",
                action_label=tr(" Instalar Todo "),
            ),
            SectionItem(
                "action:install_no_3d",
                tr("Instalar sin 3D (--no-3d)"),
                tr("Recomendado para portatiles / sin GPU dedicada"),
                "action",
                action_label=tr(" Instalar s/3D "),
            ),
            SectionItem(
                "action:install_core_only",
                tr("Solo Base y Tema (--core-only)"),
                tr("Unicamente tema Lizarbe, iconos, GTK y dotfiles"),
                "action",
                action_label=tr(" Solo Base "),
            ),
        ])
        return items

    def _build_app_cards_from_list(
        self,
        raw_list: List[Tuple[str, str, str, str]],
        webapps: Optional[List[Tuple[str, str, str, str]]] = None,
    ) -> List[SectionItem]:
        uninstalled: List[SectionItem] = []
        installed: List[SectionItem] = []

        for cat, pkg, title, desc in raw_list:
            is_inst = self.sys_mgr.is_package_installed(pkg)
            item = SectionItem(
                f"app:{pkg}",
                title,
                desc,
                "app_card",
                is_installed=is_inst,
                pkg_name=pkg,
                category=cat,
            )
            if is_inst:
                installed.append(item)
            else:
                uninstalled.append(item)

        if webapps:
            for w_id, w_title, w_url, _ in webapps:
                is_inst = self.sys_mgr.is_webapp_installed(w_id)
                item = SectionItem(
                    f"webapp:{w_id}",
                    w_title,
                    trf("Webapp de {w_id} ({w_url})", w_id=w_id, w_url=w_url),
                    "app_card",
                    is_installed=is_inst,
                    pkg_name=w_id,
                    category=tr("WEBAPPS"),
                )
                if is_inst:
                    installed.append(item)
                else:
                    uninstalled.append(item)

        items: List[SectionItem] = []

        # Arriba: Disponibles para descargar/instalar (Borde estándar delgado)
        items.append(
            SectionItem(
                "header:avail",
                tr("DISPONIBLES PARA INSTALAR"),
                trf("({len} aplicaciones listas para instalar en tu equipo)", len=len(uninstalled)),
                "header",
            )
        )
        if uninstalled:
            items.extend(uninstalled)
        else:
            items.append(
                SectionItem(
                    "info:all_installed",
                    tr("Todas las aplicaciones instaladas"),
                    tr("¡Tu equipo ya cuenta con todas las aplicaciones de esta sección!"),
                    "info_badge",
                    action_label=tr(" [Al dia] "),
                )
            )

        # Abajo: Instaladas (Borde grueso resaltado en estilo Meca)
        items.append(
            SectionItem(
                "header:installed",
                tr("APLICACIONES INSTALADAS"),
                trf("({len} aplicaciones activas en tu equipo)", len=len(installed)),
                "header",
            )
        )
        if installed:
            items.extend(installed)
        else:
            items.append(
                SectionItem(
                    "info:none_installed",
                    tr("Ninguna instalada todavía"),
                    tr("Selecciona cualquiera de las aplicaciones de arriba para instalarla."),
                    "info_badge",
                    action_label=tr(" 0 instaladas "),
                )
            )

        return items

    def _build_apps_util_items(self) -> List[SectionItem]:
        return self._build_app_cards_from_list(self.sys_mgr.UTIL_PKGS)

    def _build_creative_apps_items(self) -> List[SectionItem]:
        return self._build_app_cards_from_list(self.sys_mgr.CREATIVE_PKGS)

    def _build_work_apps_items(self) -> List[SectionItem]:
        return self._build_app_cards_from_list(self.sys_mgr.WORK_PKGS, self.sys_mgr.WEBAPPS_SPEC)

    def _build_kdeconnect_section_items(self) -> List[SectionItem]:
        items: List[SectionItem] = []
        is_inst = self.sys_mgr.is_kdeconnect_installed()
        is_running = self.sys_mgr.is_kdeconnect_daemon_running() if is_inst else False

        # 1. Estado del servicio KDE Connect
        items.append(
            SectionItem(
                "header:kc_service",
                tr("ESTADO DEL SERVICIO KDE CONNECT"),
                tr("Demonio en segundo plano para recepción de datos y eventos"),
                "header",
            )
        )
        if is_inst:
            items.append(
                SectionItem(
                    "action:kc_toggle_daemon",
                    tr("Demonio KDE Connect"),
                    tr("Servicio activo y escuchando en la red local") if is_running else tr("Servicio inactivo o en espera"),
                    "action",
                    action_label=tr(" Reiniciar ") if is_running else tr(" Iniciar "),
                    is_installed=False,
                )
            )
        else:
            items.append(
                SectionItem(
                    "action:kc_toggle_daemon",
                    tr("Demonio KDE Connect"),
                    tr("KDE Connect no está instalado en el equipo"),
                    "action",
                    action_label=tr(" No Instalado "),
                    is_installed=True,  # Opacada / atenuada
                )
            )

        # 2. Herramientas y acciones de control
        items.append(
            SectionItem(
                "header:kc_tools",
                tr("HERRAMIENTAS Y CONTROL"),
                tr("Acciones de prueba, emparejamiento y gestión remota"),
                "header",
            )
        )
        if is_inst and not self.sys_mgr.is_kdeconnect_firewall_allowed():
            items.append(
                SectionItem(
                    "action:kc_fix_firewall",
                    tr("Cortafuegos: Puertos 1714-1764 Bloqueados"),
                    tr("UFW impide descubrir tu celular. Pulsa para desbloquearlos"),
                    "action",
                    action_label=tr(" Abrir Puertos "),
                    is_installed=False,
                )
            )
        items.extend([
            SectionItem(
                "action:kc_how_to_use",
                tr("Guía de Conexión y Uso"),
                tr("Instrucciones paso a paso y diagramas para vincular tu teléfono"),
                "action",
                action_label=tr(" Cómo Usar "),
                is_installed=False,
            ),
            SectionItem(
                "action:open_kdeconnect_gui",
                tr("Abrir Gestor KDE Connect"),
                tr("Abrir interfaz gráfica completa para vincular dispositivos"),
                "action",
                action_label=tr(" Abrir GUI "),
                is_installed=(not is_inst),
            ),
            SectionItem(
                "action:kc_ping_all",
                tr("Probar Conexión (Ping a todos)"),
                tr("Enviar señal de prueba a los dispositivos vinculados"),
                "action",
                action_label=tr(" Enviar Ping "),
                is_installed=(not is_inst),
            ),
            SectionItem(
                "action:kc_ring",
                tr("Hacer Sonar mi Teléfono"),
                tr("Envía una alarma acústica para encontrar tu teléfono móvil"),
                "action",
                action_label=tr(" Hacer Sonar "),
                is_installed=(not is_inst),
            ),
        ])

        # 3. Dispositivos detectados en la red
        items.append(
            SectionItem(
                "header:kc_devices",
                tr("DISPOSITIVOS DETECTADOS EN TU RED LOCAL (WIFI)"),
                tr("Smartphones con la app KDE Connect abierta en tu misma red"),
                "header",
            )
        )

        devices = self.sys_mgr.get_kdeconnect_devices() if is_inst else []
        if devices:
            for dev in devices:
                d_id = dev["id"]
                d_name = dev["name"]
                paired = dev["paired"]
                st_desc = tr("Vinculado y sincronizado") if paired else tr("Disponible para vincular")
                items.append(
                    SectionItem(
                        f"kc_device:{d_id}",
                        trf("Smartphone: {d_name}", d_name=d_name),
                        trf("ID: {d_id} • Estado: {st_desc}", d_id=d_id, st_desc=st_desc),
                        "action",
                        action_label=tr(" Vinculado ") if paired else tr(" Vincular "),
                        is_installed=paired,
                    )
                )
        else:
            items.append(
                SectionItem(
                    "action:kc_refresh_devices",
                    tr("Buscar Teléfonos en la Red"),
                    tr("Asegúrate de tener la app KDE Connect abierta en tu teléfono") if is_inst else tr("Requiere instalar KDE Connect para buscar en tu red"),
                    "action",
                    action_label=tr(" Actualizar "),
                    is_installed=(not is_inst),
                )
            )

        # 4. Gestión del paquete (Instalación o Desinstalación)
        items.append(
            SectionItem(
                "header:kc_manage",
                tr("GESTION DEL PAQUETE"),
                tr("Opciones de administración del software"),
                "header",
            )
        )
        if is_inst:
            items.append(
                SectionItem(
                    "action:uninstall_kdeconnect",
                    tr("Desinstalar KDE Connect"),
                    tr("Remover paquete y servicio de KDE Connect del equipo"),
                    "action",
                    action_label=tr(" Desinstalar "),
                    is_installed=True,
                )
            )
        else:
            items.append(
                SectionItem(
                    "action:install_kdeconnect_now",
                    tr("Instalar KDE Connect"),
                    tr("Instalar paquete kdeconnect oficial desde repositorios de Arch"),
                    "action",
                    action_label=tr("  Instalar "),
                    is_installed=False,
                )
            )

        return items

    def _build_uninstall_section_items(self) -> List[SectionItem]:
        return [
            SectionItem(
                "header:uninstall_main",
                tr("REVERSION Y DESINSTALACION GENERAL"),
                tr("Restaura el estado original de Omarchy con confirmacion"),
                "header",
            ),
            SectionItem(
                "action:uninstall_theme_only",
                tr("Desinstalar solo el Tema (--theme-only)"),
                tr("Remueve tema Lizarbe, iconos, Darky y restaura tema oficial"),
                "action",
                action_label=tr(" Revertir Tema "),
            ),
            SectionItem(
                "action:uninstall_apps_only",
                tr("Desinstalar todas las Suites (--apps-only)"),
                tr("Desinstala las aplicaciones conservando el tema Lizarbe"),
                "action",
                action_label=tr(" Borrar Apps "),
            ),
            SectionItem(
                "action:uninstall_all",
                tr("Desinstalacion Completa (--all)"),
                tr("Elimina el tema Lizarbe y todas las suites de software"),
                "action",
                action_label=tr(" Borrar Todo "),
            ),
            SectionItem(
                "header:uninstall_suites",
                tr("DESINSTALAR SUITES INDIVIDUALES"),
                tr("Remueve unicamente los paquetes de una suite especifica"),
                "header",
            ),
            SectionItem(
                "action:uninstall_2d",
                tr("Desinstalar Suite 2D (--2d)"),
                tr("Krita, LibreSprite, Inkscape y Pinta"),
                "action",
                action_label=tr(" Desinstalar "),
            ),
            SectionItem(
                "action:uninstall_3d",
                tr("Desinstalar Suite 3D & CAD (--3d)"),
                tr("Blender, FreeCAD, Godot y Blockbench"),
                "action",
                action_label=tr(" Desinstalar "),
            ),
            SectionItem(
                "action:uninstall_dev",
                tr("Desinstalar Suite Desarrollo (--dev)"),
                tr("VS Code, Lazygit, Docker y Lazydocker"),
                "action",
                action_label=tr(" Desinstalar "),
            ),
            SectionItem(
                "action:uninstall_office",
                tr("Desinstalar Suite Ofimatica (--office)"),
                tr("genOffice, ONLYOFFICE, LibreOffice, Obsidian y Xournal++"),
                "action",
                action_label=tr(" Desinstalar "),
            ),
            SectionItem(
                "action:uninstall_multimedia",
                tr("Desinstalar Suite Multimedia (--multimedia)"),
                tr("Kdenlive, Shotcut, OBS Studio y Audacity"),
                "action",
                action_label=tr(" Desinstalar "),
            ),
            SectionItem(
                "action:uninstall_webapps",
                tr("Remover Webapps (--webapps)"),
                tr("Eliminar accesos de WhatsApp Web y YouTube"),
                "action",
                action_label=tr(" Remover "),
            ),
        ]

    def _build_section_items_for_id(self, sec_id: str) -> List[SectionItem]:
        if sec_id == "status":
            return self._build_status_section_items()
        elif sec_id == "theme":
            return self._build_theme_section_items()
        elif sec_id == "dotfiles":
            return self._build_dotfiles_section_items()
        elif sec_id == "apps_util":
            return self._build_apps_util_items()
        elif sec_id == "kdeconnect":
            return self._build_kdeconnect_section_items()
        elif sec_id == "apps_creative":
            return self._build_creative_apps_items()
        elif sec_id == "apps_work":
            return self._build_work_apps_items()
        elif sec_id == "suites":
            return self._build_suites_section_items()
        elif sec_id == "uninstall":
            return self._build_uninstall_section_items()
        return []

    def _init_section_items(self) -> Dict[str, List[SectionItem]]:
        return {
            "status": self._build_status_section_items(),
            "theme": self._build_theme_section_items(),
            "dotfiles": self._build_dotfiles_section_items(),
            "apps_util": self._build_apps_util_items(),
            "kdeconnect": self._build_kdeconnect_section_items(),
            "apps_creative": self._build_creative_apps_items(),
            "apps_work": self._build_work_apps_items(),
            "suites": self._build_suites_section_items(),
            "uninstall": self._build_uninstall_section_items(),
        }

    # ==========================
    # CICLO PRINCIPAL Y EJECUCIÓN DE TAREAS EN TERMINAL
    # ==========================

    def _run_interactive_command(self, title: str, cmd: List[str], pause_after: bool = True) -> int:
        """
        Suspende temporalmente el buffer alternativo de la TUI para ejecutar comandos
        interactivos (como yay, pacman, sudo, install.sh o uninstall.sh)
        mostrando su salida en tiempo real, y luego restaura la TUI limpiamente.
        """
        fd = sys.stdin.fileno()
        sys.stdout.write("\033[<1u\033[?1006l\033[?1003l\033[?1002l\033[?1000l\033[?7h\033[?25h\033[?1049l\033[0m")
        sys.stdout.flush()
        if self.orig_termios:
            termios.tcsetattr(fd, termios.TCSADRAIN, self.orig_termios)

        ar, ag, ab = self.theme_engine.hex_to_rgb(self.theme_engine.colors.get("accent", "#E31B23"))
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.write(f"\033[1;38;2;{ar};{ag};{ab}m==========================================================\033[0m\n")
        sys.stdout.write(f"\033[1;38;2;{ar};{ag};{ab}m  󰏘  LIZARBE TUI — {title.upper()}\033[0m\n")
        sys.stdout.write(f"\033[1;38;2;{ar};{ag};{ab}m==========================================================\033[0m\n\n")
        sys.stdout.flush()

        ret_code = 0
        try:
            res = subprocess.run(cmd, cwd=str(self.sys_mgr.repo_dir))
            ret_code = res.returncode
        except KeyboardInterrupt:
            sys.stdout.write("\n\033[1;33m" + tr("[AVISO] Operación interrumpida por el usuario.") + "\033[0m\n")
            ret_code = 130
        except Exception as exc:
            sys.stdout.write(f"\n\033[1;31m[ERROR] {exc}\033[0m\n")
            ret_code = 1

        if pause_after:
            sys.stdout.write(f"\n\033[1;38;2;{ar};{ag};{ab}m──────────────────────────────────────────────────────────\033[0m\n")
            if ret_code == 0:
                sys.stdout.write("\033[1;32m✓ " + tr("Operación finalizada con éxito.") + "\033[0m ")
            else:
                sys.stdout.write("\033[1;33m" + trf("[AVISO] La operación terminó con código {ret_code}.", ret_code=ret_code) + "\033[0m ")
            sys.stdout.write(tr("Presiona [Enter] para volver al panel Lizarbe TUI..."))
            sys.stdout.flush()
            try:
                sys.stdin.readline()
            except KeyboardInterrupt:
                pass

        tty.setraw(fd)
        sys.stdout.write("\033[?1049h\033[?25l\033[?7l\033[?1000h\033[?1002h\033[?1003h\033[?1006h\033[2J")
        sys.stdout.flush()
        HyprIPC.ensure_floating_centered(width=680, height=960)
        return ret_code

    def run(self) -> None:
        """Ciclo principal TUI en modo crudo y ventana flotante rectangular vertical (680x960)."""
        if not sys.stdin.isatty():
            print(tr("Error: lizarbe TUI debe ejecutarse en una terminal TTY."))
            return

        sys.stdout.write("\033]0;CENTRO LIZARBE\007\033]2;LIZARBE Theme & Suite\007")
        sys.stdout.flush()

        if self._was_tiled is None:
            self._was_tiled = HyprIPC.ensure_floating_centered(width=680, height=960)
        else:
            HyprIPC.ensure_floating_centered(width=680, height=960)

        fd = sys.stdin.fileno()
        self.orig_termios = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?1049h\033[?25l\033[?7l\033[?1000h\033[?1002h\033[?1003h\033[?1006h\033[2J")
            sys.stdout.flush()

            while self.running:
                self._frame_count += 1
                if self._frame_count == 2:
                    HyprIPC.ensure_floating_centered(width=680, height=960)
                try:
                    self.render()
                    self.handle_input(fd)
                except KeyboardInterrupt:
                    self.running = False
                except Exception as exc:
                    self.modal_state = None
                    self.dropdown_open = False
                    self.context_menu_open = False
                    self.status_message = trf("Error: {exc}", exc=exc)
        finally:
            sys.stdout.write("\033[<1u\033[?1006l\033[?1003l\033[?1002l\033[?1000l\033[?7h\033[?25h\033[?1049l\033[0m")
            sys.stdout.flush()
            if self.orig_termios:
                termios.tcsetattr(fd, termios.TCSADRAIN, self.orig_termios)
            if self._was_tiled:
                HyprIPC.restore_tiled()

    # ==========================
    # RENDERIZADO CON POSICIONAMIENTO EXACTO
    # ==========================

    def _get_sidebar_width(self, cols: int) -> int:
        return 23 if cols < 95 else 26

    def render(self) -> None:
        cols, rows = shutil.get_terminal_size((84, 42))
        sidebar_w = self._get_sidebar_width(cols)
        content_w = max(30, cols - sidebar_w - 1)
        buf: List[str] = []

        # 1. Barra de Título Superior en fila exacta 1 (\033[1;1H)
        local_ver = self.sys_mgr.get_local_git_hash()
        title_left = " CENTRO LIZARBE "
        unsaved_badge = " *PENDIENTE* | " if self.has_unsaved_changes() else ""
        title_right = trf("{unsaved_badge}v:{local_ver} | Tema: {current_theme} | q/Esc: Salir ", unsaved_badge=unsaved_badge, local_ver=local_ver, current_theme=self.theme_engine.current_theme)
        if len(title_left) + len(title_right) > cols:
            title_right = trf("{unsaved_badge}Tema: {current_theme} | q/Esc: Salir ", unsaved_badge=unsaved_badge, current_theme=self.theme_engine.current_theme)

        space_len = max(0, cols - len(title_left) - len(title_right))
        header_line = (title_left + (" " * space_len) + title_right)[:cols]
        buf.append(f"\033[1;1H" + self.theme_engine.style("bright_foreground", "accent", header_line, bold=True) + "\033[K")

        # 2. Cuerpo Dividido (Filas 2 a rows - 1)
        body_rows = max(10, rows - 2)
        sidebar_lines = self._render_sidebar(sidebar_w, body_rows)
        content_lines = self._render_content(content_w, body_rows, sidebar_w)

        sep_styled = self.theme_engine.fg("muted", "│")
        for r in range(body_rows):
            screen_y = r + 2
            s_line = sidebar_lines[r] if r < len(sidebar_lines) else (" " * sidebar_w)
            c_line = content_lines[r] if r < len(content_lines) else ""
            buf.append(f"\033[{screen_y};1H{s_line}")
            buf.append(f"\033[{screen_y};{sidebar_w + 1}H{sep_styled}")
            buf.append(f"\033[{screen_y};{sidebar_w + 2}H{c_line}\033[K")

        # 3. Barra Inferior de Estado en fila exacta 'rows'
        if self.modal_state == "kdeconnect_guide":
            keys_hint = tr(" j/k/Flechas: Desplazar │ Enter/Espacio/Esc/q: Cerrar guía ")
        elif self.modal_state:
            keys_hint = tr(" Tab/Flechas: Seleccionar │ Enter/Espacio: Confirmar │ Esc: Cancelar ")
        elif self.context_menu_open:
            keys_hint = tr(" j/k/Flechas: Mover │ Enter/Espacio: Ejecutar │ Esc/q: Cerrar ")
        elif self.dropdown_open:
            keys_hint = tr(" j/k/Flechas: Navegar │ Enter/Espacio: Seleccionar │ Esc: Cerrar ")
        else:
            keys_hint = tr(" Tab: Foco │ b/Esc: Panel izq │ m: Menú │ 1-9: Secciones │ Espacio: Conmutar │ a: Aplicar │ q: Salir ")
            if cols < 135:
                keys_hint = tr(" Tab: Foco │ b/Esc: Panel izq │ m: Menú │ 1-9: Secc │ a: Aplicar │ q: Salir ")
            if cols < 115:
                keys_hint = tr(" Tab: Foco │ b: Panel izq │ m: Menú │ a: Aplicar │ q: Salir ")
            if cols < 95:
                keys_hint = tr(" b: Panel izq │ m: Menú │ a: Aplicar │ q: Salir ")
            if cols < 75:
                keys_hint = tr(" b: Izq │ a: Aplicar │ q: Salir ")

        max_status_w = max(8, cols - len(keys_hint) - 1)
        status_txt = f" {self.status_message}"[:max_status_w]
        footer_space = max(0, cols - 1 - len(status_txt) - len(keys_hint))
        footer_line = (status_txt + (" " * footer_space) + keys_hint)[:cols - 1]
        buf.append(f"\033[{rows};1H" + self.theme_engine.style("bright_foreground", "muted", footer_line) + "\033[K")

        # 4. Menú desplegable (Dropdown)
        if self.dropdown_open and not self.modal_state:
            buf.extend(self._render_dropdown_overlay(cols, rows, sidebar_w))

        # 5. Menú contextual de clic secundario (Right-Click)
        if self.context_menu_open and not self.modal_state:
            buf.extend(self._render_context_menu_overlay(cols, rows))

        # 6. Ventana Modal
        if self.modal_state:
            buf.extend(self._render_modal_overlay(cols, rows))

        sys.stdout.write("".join(buf))
        sys.stdout.flush()

    def _render_sidebar(self, width: int, max_rows: int) -> List[str]:
        """Renderiza el panel izquierdo con categorías e iconos Nerd Font."""
        lines: List[str] = []
        current_cat = None
        self._sidebar_click_map.clear()

        for idx, (cat, sec_id, icon, title, desc) in enumerate(self.SECTIONS):
            if cat != current_cat:
                if current_cat is not None and len(lines) < max_rows:
                    lines.append(" " * width)

                current_cat = cat
                if len(lines) < max_rows:
                    lines.append(self.theme_engine.style("muted", None, f" {cat}".ljust(width)[:width], bold=True))

            if len(lines) >= max_rows:
                break

            is_sel = (idx == self.current_section_idx)
            is_hover = (idx == self.hover_sidebar_idx and not self.modal_state and not self.dropdown_open and not self.context_menu_open)
            is_active_pane = (self.active_pane == "sidebar" and not self.modal_state and not self.dropdown_open and not self.context_menu_open)

            screen_row = 2 + len(lines)
            self._sidebar_click_map[screen_row] = idx

            prefix = " ▸" if is_hover else "  "
            item_text = f"{prefix}{icon}  {title}".ljust(width)[:width]

            if is_sel and (is_active_pane or is_hover):
                line = self.theme_engine.style("bright_foreground", "soft_selection", item_text, bold=True)
            elif is_sel:
                line = self.theme_engine.style("bright_foreground", "soft_muted", item_text, bold=True)
            elif is_hover:
                line = self.theme_engine.style("bright_foreground", "soft_muted", item_text, bold=True)
            else:
                line = self.theme_engine.style("foreground", None, item_text)

            lines.append(line)

        while len(lines) < max_rows:
            lines.append(" " * width)

        return lines[:max_rows]

    def _render_theme_card_3lines(
        self,
        item: SectionItem,
        width: int,
        is_sel: bool,
        is_hover: bool,
    ) -> Tuple[str, str, str, Tuple[int, int]]:
        """
        Renderiza una tarjeta de tema de 3 líneas:
        - Cuando está activo/seleccionado (is_chosen), resalta su borde haciéndolo más grueso (┏━━━┓ / ┃...┃ / ┗━━━┛).
        """
        u_name = item.name
        info = self.theme_engine.get_theme_info(u_name)
        mode = info.get("mode", "dark")
        icons = info.get("icon_theme", "Lizarbe-Red")

        u_slug = self.theme_engine.normalize_theme_slug(u_name)
        sel_slug = self.theme_engine.normalize_theme_slug(
            str(self.settings.get("active_theme", self.theme_engine.current_theme))
        )
        is_chosen = (u_slug == sel_slug)

        card_w = max(28, width - 3)
        inner_w = card_w - 2

        border_col = "accent" if is_chosen else ("bright_foreground" if (is_sel or is_hover) else "muted")
        card_bg = (
            "soft_hover"
            if is_hover
            else ("soft_selection" if (is_chosen or is_sel) else None)
        )

        mode_icon = "󰖔" if mode == "dark" else "󰖨"
        left_str = f"  {u_name} — {item.desc}"
        right_str = f"  {mode_icon}  {icons}  "
        avail_left_w = max(6, inner_w - len(right_str))
        left_padded = left_str[:avail_left_w].ljust(avail_left_w)
        inner_plain = (left_padded + right_str)[:inner_w].ljust(inner_w)

        is_bold_card = (is_chosen or is_sel or is_hover)
        if is_chosen:
            top_border = " " + self.theme_engine.style(border_col, None, "┏" + ("━" * inner_w) + "┓", bold=True)
            bot_border = " " + self.theme_engine.style(border_col, None, "┗" + ("━" * inner_w) + "┛", bold=True)
            side_char = "┃"
        else:
            top_border = " " + self.theme_engine.style(border_col, None, "┌" + ("─" * inner_w) + "┐", bold=is_bold_card)
            bot_border = " " + self.theme_engine.style(border_col, None, "└" + ("─" * inner_w) + "┘", bold=is_bold_card)
            side_char = "│"

        inner_styled = self.theme_engine.style(
            "bright_foreground" if is_bold_card else "foreground",
            card_bg,
            inner_plain,
            bold=is_bold_card,
        )

        mid_line = (
            " "
            + self.theme_engine.style(border_col, None, side_char, bold=is_bold_card)
            + inner_styled
            + self.theme_engine.style(border_col, None, side_char, bold=is_bold_card)
        )

        return top_border, mid_line, bot_border, (1, card_w)

    def _get_app_icon(self, item: SectionItem) -> str:
        if item.icon:
            return item.icon
        key = (item.pkg_name or item.key).lower()
        if "zen" in key:
            return "󰖟"
        if "krita" in key:
            return ""
        if "blender" in key:
            return "󰂫"
        if "code" in key or "vscode" in key:
            return "󰨞"
        if "git" in key:
            return "󰊢"
        if "docker" in key:
            return "󰡨"
        if "office" in key or "libreoffice" in key:
            return "󰈙"
        if "obsidian" in key:
            return "󱞁"
        if "kdenlive" in key or "shotcut" in key or "video" in key:
            return "󰕧"
        if "obs" in key:
            return "󰑋"
        if "audacity" in key:
            return "󰓃"
        if "whatsapp" in key:
            return "󰖣"
        if "youtube" in key:
            return "󰗃"
        if "fastfetch" in key:
            return "󰚰"
        if "htop" in key or "btop" in key:
            return "󰄪"
        if "alacritty" in key or "ghostty" in key or "term" in key:
            return ""
        if "kdeconnect" in key:
            return "󰄡"
        if "nwg-look" in key:
            return "󰏘"
        if "localsend" in key:
            return "󰖟"
        if "bleachbit" in key:
            return "󰃢"
        return "󰏖"

    def _render_app_card_3lines(
        self,
        item: SectionItem,
        width: int,
        is_sel: bool,
        is_hover: bool,
        hover_sub: Optional[str] = None,
    ) -> Tuple[str, str, str, Tuple[int, int], Tuple[int, int]]:
        """
        Renderiza una tarjeta de aplicación de 3 líneas (Estilo Meca):
        - Arriba (No instaladas): borde estándar delgado (┌───┐ / │...│ / └───┘) y botón verde [ + Instalar ].
        - Abajo (Instaladas): resalto en los bordes con borde grueso (┏━━━┓ / ┃...┃ / ┗━━━┛) y botón rojo [ Desinstalar ].
        """
        is_inst = item.is_installed
        btn_label = tr(" Desinstalar ") if is_inst else tr("  Instalar  ")
        inner_btn_w = len(btn_label)
        btn_w = inner_btn_w + 2

        # Espacio para tarjeta a la izquierda y botón a la derecha
        card_w = max(20, width - btn_w - 3)
        card_inner_w = card_w - 2

        is_btn_hov = (hover_sub == "btn")
        card_bg = "soft_hover" if (is_hover and not is_btn_hov) else ("soft_selection" if is_sel else None)
        icon = self._get_app_icon(item)

        if not is_inst:
            # 1. No instaladas -> RESALTADAS (borde grueso, texto nítido brillante y botón destacado)
            border_col = "accent" if (is_sel or is_hover) else "bright_foreground"
            c_top = " " + self.theme_engine.style(border_col, None, "┏" + ("━" * card_inner_w) + "┓", bold=True)
            c_bot = " " + self.theme_engine.style(border_col, None, "┗" + ("━" * card_inner_w) + "┛", bold=True)
            side_char = "┃"

            left_plain = f"  {icon}  {item.name} — {item.desc}"[:card_inner_w].ljust(card_inner_w)
            left_styled = self.theme_engine.style(
                "bright_foreground",
                card_bg,
                left_plain,
                bold=True,
            )
            c_mid = (
                " "
                + self.theme_engine.style(border_col, None, side_char, bold=True)
                + left_styled
                + self.theme_engine.style(border_col, None, side_char, bold=True)
            )

            # Botón ' Instalar' (destacado con borde nítido y sobrio)
            b_col = "accent" if is_btn_hov else ("bright_foreground" if is_sel else "bright_foreground")
            sh_col = "accent" if (is_btn_hov or is_sel) else "bright_foreground"
            btn_bg = "soft_hover" if is_btn_hov else ("soft_selection" if is_sel else None)
            btn_fg = "bright_foreground"

            btn_top = self.theme_engine.style(b_col, None, "┌" + ("─" * inner_btn_w) + "┐", bold=(is_sel or is_btn_hov))
            btn_mid = (
                self.theme_engine.style(sh_col, None, "┃", bold=True)
                + self.theme_engine.style(btn_fg, btn_bg, btn_label, bold=True)
                + self.theme_engine.style(b_col, None, "│", bold=(is_sel or is_btn_hov))
            )
            btn_bot = self.theme_engine.style(sh_col, None, "┗" + ("━" * inner_btn_w) + "┙", bold=True)

        else:
            # 2. Instaladas -> MÁS APAGADAS (borde delgado atenuado, texto sobrio y botón normal)
            border_col = "accent" if is_sel else ("bright_foreground" if is_hover else "muted")
            c_top = " " + self.theme_engine.style(border_col, None, "┌" + ("─" * card_inner_w) + "┐", bold=is_sel)
            c_bot = " " + self.theme_engine.style(border_col, None, "└" + ("─" * card_inner_w) + "┘", bold=is_sel)
            side_char = "│"

            text_fg = "bright_foreground" if is_sel else ("foreground" if is_hover else "muted")
            left_plain = f"  {icon}  {item.name} — {item.desc}"[:card_inner_w].ljust(card_inner_w)
            left_styled = self.theme_engine.style(
                text_fg,
                card_bg,
                left_plain,
                bold=is_sel,
            )
            c_mid = (
                " "
                + self.theme_engine.style(border_col, None, side_char, bold=is_sel)
                + left_styled
                + self.theme_engine.style(border_col, None, side_char, bold=is_sel)
            )

            # Botón 'Desinstalar' normal, atenuado y sobrio
            b_col = "accent" if is_btn_hov else ("bright_foreground" if is_sel else "muted")
            sh_col = "accent" if (is_btn_hov or is_sel) else "muted"
            btn_bg = "soft_hover" if is_btn_hov else ("soft_selection" if is_sel else None)
            btn_fg = "bright_foreground" if (is_sel or is_btn_hov) else "muted"

            btn_top = self.theme_engine.style(b_col, None, "┌" + ("─" * inner_btn_w) + "┐", bold=(is_sel or is_btn_hov))
            btn_mid = (
                self.theme_engine.style(sh_col, None, "┃", bold=(is_sel or is_btn_hov))
                + self.theme_engine.style(btn_fg, btn_bg, btn_label, bold=(is_sel or is_btn_hov))
                + self.theme_engine.style(b_col, None, "│", bold=(is_sel or is_btn_hov))
            )
            btn_bot = self.theme_engine.style(sh_col, None, "┗" + ("━" * inner_btn_w) + "┙", bold=(is_sel or is_btn_hov))

        top_line = c_top + " " + btn_top
        mid_line = c_mid + " " + btn_mid
        bot_line = c_bot + " " + btn_bot

        card_rel_start = 1
        card_rel_end = card_w
        btn_rel_start = card_w + 2
        btn_rel_end = btn_rel_start + btn_w - 1

        return top_line, mid_line, bot_line, (card_rel_start, card_rel_end), (btn_rel_start, btn_rel_end)

    def _render_content(self, width: int, max_rows: int, sidebar_w: int) -> List[str]:
        lines: List[str] = []
        if self.current_section_idx >= len(self.SECTIONS):
            self.current_section_idx = 0
        sec_meta = self.SECTIONS[self.current_section_idx]
        sec_id = sec_meta[1]
        sec_title = sec_meta[3]
        sec_desc = sec_meta[4]
        self._content_click_map.clear()

        # Encabezado de la Sección Activa (3 líneas)
        lines.append(" " + self.theme_engine.style("bright_foreground", None, sec_title.upper(), bold=True))
        lines.append(" " + self.theme_engine.fg("muted", sec_desc[:width - 2]))
        lines.append(" " + self.theme_engine.fg("muted", "─" * max(1, width - 2)))

        if sec_id not in self.section_items or not self.section_items[sec_id]:
            self.section_items[sec_id] = self._build_section_items_for_id(sec_id)

        items = self.section_items.get(sec_id, [])
        is_active_pane = (self.active_pane == "content" and not self.modal_state and not self.context_menu_open)
        content_start_x = sidebar_w + 2

        # Asegurar que selected_item_idx no apunte a un separador "header"
        if items and 0 <= self.selected_item_idx < len(items) and items[self.selected_item_idx].item_type == "header":
            if self.selected_item_idx + 1 < len(items):
                self.selected_item_idx += 1
            elif self.selected_item_idx > 0:
                self.selected_item_idx -= 1

        buttons_block_h = 4
        items_area_rows = max(3, max_rows - 3 - buttons_block_h)
        max_visible_items = max(1, items_area_rows // 3)

        if self.selected_item_idx >= len(items):
            self.selected_item_idx = max(0, len(items) - 1)

        if self.selected_item_idx < self.content_scroll_offset:
            self.content_scroll_offset = self.selected_item_idx
        elif self.selected_item_idx >= self.content_scroll_offset + max_visible_items:
            self.content_scroll_offset = self.selected_item_idx - max_visible_items + 1
        self.content_scroll_offset = max(0, min(self.content_scroll_offset, max(0, len(items) - max_visible_items)))

        visible_end = min(len(items), self.content_scroll_offset + max_visible_items)

        for i in range(self.content_scroll_offset, visible_end):
            item = items[i]
            item_screen_row = 2 + len(lines)

            if item.item_type == "header":
                hdr_title = f" ━━ {item.name} "
                rem_bars = max(2, width - len(hdr_title) - 2)
                l1 = self.theme_engine.style("accent", None, hdr_title + ("━" * rem_bars), bold=True)
                l2 = " " + self.theme_engine.fg("muted", item.desc[:width - 2])
                l3 = ""
                lines.append(l1)
                lines.append(l2)
                lines.append(l3)
                continue

            is_hover_row = (i == self.hover_item_idx and not self.modal_state and not self.dropdown_open and not self.context_menu_open)
            is_sel = (i == self.selected_item_idx and is_active_pane) or is_hover_row

            if item.item_type == "theme_card":
                t_top, t_mid, t_bot, (c_rel_start, c_rel_end) = self._render_theme_card_3lines(
                    item, width, is_sel, is_hover_row
                )
                card_x_start = content_start_x + c_rel_start
                card_x_end = content_start_x + c_rel_end
                click_info = {
                    "item_idx": i,
                    "item": item,
                    "control_range": (card_x_start, card_x_end),
                    "btn_range": (card_x_start, card_x_end),
                    "row_y": item_screen_row,
                }
                self._content_click_map[item_screen_row] = click_info
                self._content_click_map[item_screen_row + 1] = click_info
                self._content_click_map[item_screen_row + 2] = click_info
                lines.append(t_top)
                lines.append(t_mid)
                lines.append(t_bot)
                continue

            if item.item_type == "app_card":
                hover_sub = self.hover_subcontrol if is_hover_row else None
                t_top, t_mid, t_bot, (c_rel_start, c_rel_end), (b_rel_start, b_rel_end) = self._render_app_card_3lines(
                    item, width, is_sel, is_hover_row, hover_sub
                )
                card_x_start = content_start_x + c_rel_start
                card_x_end = content_start_x + c_rel_end
                btn_x_start = content_start_x + b_rel_start
                btn_x_end = content_start_x + b_rel_end
                click_info = {
                    "item_idx": i,
                    "item": item,
                    "control_range": (card_x_start, card_x_end),
                    "btn_range": (btn_x_start, btn_x_end),
                    "row_y": item_screen_row,
                }
                self._content_click_map[item_screen_row] = click_info
                self._content_click_map[item_screen_row + 1] = click_info
                self._content_click_map[item_screen_row + 2] = click_info
                lines.append(t_top)
                lines.append(t_mid)
                lines.append(t_bot)
                continue

            hover_sub = self.hover_subcontrol if is_hover_row else None
            c_top, c_mid, c_bot, ctrl_vis_w = self._format_item_control_3lines(item, is_sel, hover_sub)
            left_max_w = max(12, width - ctrl_vis_w - 3)

            control_x_start = content_start_x + left_max_w + 1
            control_x_end = control_x_start + ctrl_vis_w - 1

            click_info = {
                "item_idx": i,
                "item": item,
                "control_range": (control_x_start, control_x_end),
                "row_y": item_screen_row,
            }
            self._content_click_map[item_screen_row] = click_info
            self._content_click_map[item_screen_row + 1] = click_info
            self._content_click_map[item_screen_row + 2] = click_info

            sec_id = self.SECTIONS[self.current_section_idx][1]
            is_subdued_item = (
                (getattr(item, "is_installed", False) and item.item_type == "action")
                or _label_has(item.action_label, "Desinstalar", "No Instalado")
                or (sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed() and item.key not in ("action:install_kdeconnect_now", "action:kc_how_to_use"))
            )
            if is_sel:
                l1_raw = f" ▌ {item.name}"[:left_max_w].ljust(left_max_w)
                l2_raw = f" ▌ └─ {item.desc}"[:left_max_w].ljust(left_max_w)
                l1_styled = self.theme_engine.style("bright_foreground", "soft_selection", l1_raw, bold=True)
                l2_styled = self.theme_engine.fg("foreground", l2_raw)
            else:
                l1_raw = f"   {item.name}"[:left_max_w].ljust(left_max_w)
                l2_raw = f"   {item.desc}"[:left_max_w].ljust(left_max_w)
                title_col = "muted" if is_subdued_item else "bright_foreground"
                l1_styled = self.theme_engine.style(title_col, None, l1_raw, bold=(not is_subdued_item))
                l2_styled = self.theme_engine.fg("muted", l2_raw)

            l3_styled = " " * left_max_w

            lines.append(f"{l1_styled} {c_top}")
            lines.append(f"{l2_styled} {c_mid}")
            lines.append(f"{l3_styled} {c_bot}")

        target_before_buttons = max(3, max_rows - buttons_block_h)
        while len(lines) < target_before_buttons:
            lines.append("")

        lines.append(" " + self.theme_engine.fg("muted", "─" * max(1, width - 2)))

        btn_top_screen_y = 2 + len(lines)
        btn_lines = self._render_3d_buttons(width, btn_top_screen_y, content_start_x)
        lines.extend(btn_lines)

        return lines[:max_rows]

    def _format_item_control_3lines(
        self,
        item: SectionItem,
        is_sel: bool,
        hover_sub: Optional[str] = None,
    ) -> Tuple[str, str, str, int]:
        """Dibuja los controles del panel derecho usando cuadrados cerrados de 3 líneas."""
        val = self._get_item_value(item)
        b_col = "bright_foreground" if is_sel else "foreground"
        sh_col = "accent" if is_sel else "muted"

        if item.item_type == "toggle":
            is_on = bool(val)
            c_hov = (hover_sub == "control")
            box_top = self.theme_engine.style("accent" if c_hov else b_col, None, "┌───┐", bold=c_hov) + "    "
            mark = " ■ " if is_on else "   "
            state_lbl = " ON " if is_on else " off"
            mark_bg = "soft_hover" if c_hov else ("soft_selection" if (is_sel or is_on) else None)
            mark_styled = self.theme_engine.style(
                "bright_foreground" if (is_on or c_hov) else "muted",
                mark_bg,
                mark,
                bold=(is_on or c_hov),
            )
            lbl_styled = self.theme_engine.style(
                "bright_foreground" if (is_on or c_hov) else "muted",
                None,
                state_lbl,
                bold=(is_on or c_hov),
            )
            box_mid = (
                self.theme_engine.fg("accent" if c_hov else sh_col, "┃")
                + mark_styled
                + self.theme_engine.fg(b_col, "│")
                + lbl_styled
            )
            box_bot = self.theme_engine.fg("accent" if c_hov else sh_col, "┗━━━┙") + "    "
            return box_top, box_mid, box_bot, 9

        elif item.item_type == "select":
            val_str = str(val)
            if len(val_str) > 22:
                val_str = val_str[:19] + "..."
            c_hov = (hover_sub == "control") or (self.dropdown_open and self.dropdown_item == item)
            inner_bg = "soft_hover" if c_hov else ("soft_selection" if is_sel else None)
            raw_lbl = f" {val_str} ▾ "
            inner_w = len(raw_lbl)
            inner_s = self.theme_engine.style("bright_foreground", inner_bg, raw_lbl, bold=(is_sel or c_hov))

            c_top = self.theme_engine.style("accent" if c_hov else b_col, None, "┌" + ("─" * inner_w) + "┐", bold=c_hov)
            c_mid = self.theme_engine.fg("accent" if c_hov else sh_col, "┃") + inner_s + self.theme_engine.fg(b_col, "│")
            c_bot = self.theme_engine.fg("accent" if c_hov else sh_col, "┗" + ("━" * inner_w) + "┙")
            return c_top, c_mid, c_bot, inner_w + 2

        elif item.item_type == "info_badge":
            raw_lbl = item.action_label
            inner_w = len(raw_lbl)
            sec_id = self.SECTIONS[self.current_section_idx][1]
            if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
                badge_col = "muted"
                border_col = "muted"
            else:
                if _label_has(raw_lbl, "Instalad", "Activo", "Al dia", "local"):
                    badge_col = "green"
                elif _label_has(raw_lbl, "Pendiente", "Advertencia"):
                    badge_col = "yellow"
                elif _label_has(raw_lbl, "Error", "Falta", "No detectado"):
                    badge_col = "red"
                else:
                    badge_col = "bright_foreground" if is_sel else "foreground"
                border_col = "accent" if is_sel else "muted"

            c_top = self.theme_engine.style(border_col, None, "┌" + ("─" * inner_w) + "┐", bold=is_sel)
            inner_s = self.theme_engine.style(badge_col, "soft_selection" if is_sel else None, raw_lbl, bold=is_sel)
            c_mid = self.theme_engine.fg(border_col, "│") + inner_s + self.theme_engine.fg(border_col, "│")
            c_bot = self.theme_engine.fg(border_col, "└" + ("─" * inner_w) + "┘")
            return c_top, c_mid, c_bot, inner_w + 2

        elif item.item_type == "action":
            raw_lbl = item.action_label
            inner_w = len(raw_lbl)
            c_hov = (hover_sub == "control")
            sec_id = self.SECTIONS[self.current_section_idx][1]
            is_subdued = (
                getattr(item, "is_installed", False)
                or _label_has(raw_lbl, "Desinstalar", "No Instalado")
                or (sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed() and item.key not in ("action:install_kdeconnect_now", "action:kc_how_to_use"))
            )

            if is_subdued:
                b_color = "accent" if is_sel else ("bright_foreground" if c_hov else "muted")
                sh_color = "accent" if (c_hov or is_sel) else "muted"
                text_fg = "bright_foreground" if (is_sel or c_hov) else "muted"
                inner_bg = "soft_hover" if c_hov else ("soft_selection" if is_sel else None)
                c_top = self.theme_engine.style(b_color, None, "┌" + ("─" * inner_w) + "┐", bold=(is_sel or c_hov))
                inner_s = self.theme_engine.style(text_fg, inner_bg, raw_lbl, bold=(is_sel or c_hov))
                c_mid = self.theme_engine.fg(sh_color, "┃") + inner_s + self.theme_engine.fg(b_color, "│")
                c_bot = self.theme_engine.fg(sh_color, "┗" + ("━" * inner_w) + "┙")
            else:
                c_top = self.theme_engine.style("accent" if c_hov else b_col, None, "┌" + ("─" * inner_w) + "┐", bold=c_hov)
                inner_bg = "soft_hover" if c_hov else ("soft_selection" if is_sel else None)
                inner_s = self.theme_engine.style("bright_foreground", inner_bg, raw_lbl, bold=True)
                c_mid = self.theme_engine.fg("accent" if c_hov else sh_col, "┃") + inner_s + self.theme_engine.fg(b_col, "│")
                c_bot = self.theme_engine.fg("accent" if c_hov else sh_col, "┗" + ("━" * inner_w) + "┙")
            return c_top, c_mid, c_bot, inner_w + 2

        raw = str(val)
        return " " * len(raw), raw, " " * len(raw), len(raw)

    def _render_3d_buttons(self, width: int, btn_top_screen_y: int, content_start_x: int) -> List[str]:
        """Dibuja los botones inferiores compactos de 3 líneas con bisel 3D Unicode."""
        self._button_click_map.clear()
        self._button_row_range = (btn_top_screen_y, btn_top_screen_y + 2)

        buttons_spec = [
            ("reset", 0, tr(" Restablecer ")),
            ("cancel", 1, tr(" Cancelar ")),
            ("save", 2, tr("  Aplicar  ")),
        ]

        gap = 2
        total_btns_w = sum(len(lbl) + 2 for _, _, lbl in buttons_spec) + gap * (len(buttons_spec) - 1)
        left_pad = max(1, width - total_btns_w - 2)

        row0_parts = [" " * left_pad]
        row1_parts = [" " * left_pad]
        row2_parts = [" " * left_pad]

        cur_rel_x = left_pad
        is_btn_pane = (self.active_pane == "buttons" and not self.modal_state and not self.dropdown_open and not self.context_menu_open)

        for btn_key, btn_idx, label in buttons_spec:
            inner_w = len(label)
            btn_w = inner_w + 2
            is_hover_btn = (self.hover_button_key == btn_key and not self.modal_state and not self.dropdown_open and not self.context_menu_open)
            is_sel = (is_btn_pane and self.selected_button_idx == btn_idx) or is_hover_btn
            is_primary = (btn_key == "save")

            abs_x_start = content_start_x + cur_rel_x
            abs_x_end = abs_x_start + btn_w - 1
            self._button_click_map[btn_key] = (abs_x_start, abs_x_end)

            border_col = "bright_foreground" if (is_sel or is_primary) else "foreground"
            bevel_col = "accent" if (is_sel or is_primary) else "muted"

            r0 = self.theme_engine.style(border_col, None, "┌" + ("─" * inner_w) + "┐", bold=(is_sel or is_primary))

            left_edge = self.theme_engine.style(bevel_col, None, "┃", bold=True)
            right_edge = self.theme_engine.style(border_col, None, "│", bold=(is_sel or is_primary))
            if is_hover_btn:
                inner_styled = self.theme_engine.style("bright_foreground", "soft_hover", label, bold=True)
            elif is_sel:
                inner_styled = self.theme_engine.style("bright_foreground", "soft_selection", label, bold=True)
            elif is_primary:
                inner_styled = self.theme_engine.style("bright_foreground", None, label, bold=True)
            else:
                inner_styled = self.theme_engine.style("foreground", None, label)
            r1 = f"{left_edge}{inner_styled}{right_edge}"

            r2 = self.theme_engine.style(bevel_col, None, "┗" + ("━" * inner_w) + "┙", bold=True)

            row0_parts.append(r0 + (" " * gap))
            row1_parts.append(r1 + (" " * gap))
            row2_parts.append(r2 + (" " * gap))

            cur_rel_x += btn_w + gap

        return [
            "".join(row0_parts),
            "".join(row1_parts),
            "".join(row2_parts),
        ]

    # ==========================
    # MENÚ DESPLEGABLE (DROPDOWN) Y MENÚ CONTEXTUAL
    # ==========================

    def _open_dropdown_for_item(self, item: SectionItem, anchor_y: int = 8, anchor_x: int = 45) -> None:
        if not item.options:
            return
        self.dropdown_open = True
        self.dropdown_item = item
        self.dropdown_options = list(item.options)
        cur_val = str(self._get_item_value(item))
        try:
            self.dropdown_idx = self.dropdown_options.index(cur_val)
        except ValueError:
            self.dropdown_idx = 0
        self.dropdown_scroll = max(0, self.dropdown_idx - 3)
        self.hover_dropdown_idx = None
        self.dropdown_anchor_y = anchor_y
        self.dropdown_anchor_x = anchor_x

    def _render_dropdown_overlay(self, cols: int, rows: int, sidebar_w: int) -> List[str]:
        self._dropdown_row_map.clear()
        if not self.dropdown_item or not self.dropdown_options:
            return []

        opts = self.dropdown_options
        max_vis = min(8, len(opts), max(4, rows - 8))
        if self.dropdown_idx < self.dropdown_scroll:
            self.dropdown_scroll = self.dropdown_idx
        elif self.dropdown_idx >= self.dropdown_scroll + max_vis:
            self.dropdown_scroll = self.dropdown_idx - max_vis + 1
        self.dropdown_scroll = max(0, min(self.dropdown_scroll, max(0, len(opts) - max_vis)))

        max_opt_len = max(len(str(o)) for o in opts)
        inner_w = max(22, min(44, max_opt_len + 6))
        box_w = inner_w + 2
        box_h = max_vis + 2

        start_x = max(sidebar_w + 3, cols - box_w - 2)
        start_y = self.dropdown_anchor_y + 3
        if start_y + box_h >= rows - 1:
            start_y = max(3, self.dropdown_anchor_y - box_h)

        self._dropdown_box_bounds = (start_y, start_y + box_h - 1, start_x, start_x + box_w - 1)
        cur_val = str(self._get_item_value(self.dropdown_item))

        overlay: List[str] = []
        hdr_hint = " ▲ " if self.dropdown_scroll > 0 else "───"
        top_line = "┌" + ("─" * (inner_w - 3)) + hdr_hint + "┐"
        overlay.append(f"\033[{start_y};{start_x}H" + self.theme_engine.style("accent", "background", top_line, bold=True))

        for r_off in range(max_vis):
            opt_idx = self.dropdown_scroll + r_off
            scr_y = start_y + 1 + r_off
            opt_str = str(opts[opt_idx])
            self._dropdown_row_map[scr_y] = opt_idx

            is_sel = (opt_idx == self.dropdown_idx)
            is_hov = (opt_idx == self.hover_dropdown_idx)
            is_cur = (opt_str == cur_val)
            is_bold = (is_sel or is_hov or is_cur)

            check = "✓" if is_cur else ("▸" if (is_sel or is_hov) else " ")
            row_bg = "soft_hover" if is_hov else ("soft_selection" if is_sel else "background")
            row_fg = "bright_foreground" if is_bold else "foreground"

            row_txt = f" {check} {opt_str}"[:inner_w].ljust(inner_w)
            row_styled = self.theme_engine.style(row_fg, row_bg, row_txt, bold=is_bold)

            overlay.append(
                f"\033[{scr_y};{start_x}H"
                + self.theme_engine.style("accent", "background", "┃", bold=True)
                + row_styled
                + self.theme_engine.style("accent", "background", "│", bold=True)
            )

        ftr_hint = " ▼ " if (self.dropdown_scroll + max_vis < len(opts)) else "━━━"
        bot_line = "┗" + ("━" * (inner_w - 3)) + ftr_hint + "┙"
        overlay.append(f"\033[{start_y + max_vis + 1};{start_x}H" + self.theme_engine.style("accent", "background", bot_line, bold=True))
        return overlay

    def _open_context_menu(self, x: int, y: int, sidebar_w: int) -> None:
        """Abre el menú contextual de clic secundario según el elemento bajo el cursor."""
        self.dropdown_open = False
        self.context_menu_x = x
        self.context_menu_y = y
        self.context_menu_idx = 0
        self.hover_context_idx = None
        self.context_menu_target_key = ""

        if x > sidebar_w + 1 and y in self._content_click_map:
            info = self._content_click_map[y]
            self.active_pane = "content"
            self.selected_item_idx = info["item_idx"]
            item: SectionItem = info["item"]
            self.context_menu_target_key = item.key

            sec_id = self.SECTIONS[self.current_section_idx][1]
            if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
                self.context_menu_items = [
                    ("action:install_kdeconnect_now", tr("  Instalar KDE Connect")),
                    ("app:refresh_state", tr("󰑐  Recargar estado del equipo")),
                ]
                self.context_menu_open = True
                return

            if item.item_type == "theme_card":
                t_name = item.name
                self.context_menu_items = [
                    (f"theme:activate:{t_name}", trf("󰸌  Activar '{t_name}' ahora", t_name=t_name)),
                    ("theme:next_wp", tr("󰸉  Siguiente fondo")),
                    ("theme:apply_user", "󰑐  Reaplicar lizarbe-apply-user"),
                ]
                self.context_menu_open = True
                return

            if item.key.startswith("suite:"):
                s_id = item.key.split(":", 1)[1]
                self.context_menu_items = [
                    (f"suite:install_now:{s_id}", trf("  Instalar '{name}' ahora", name=item.name)),
                    (f"suite:remove_now:{s_id}", trf("󰆴  Desinstalar '{name}'", name=item.name)),
                    ("item:toggle", tr("󰔡  Conmutar seleccion")),
                    ("app:save", tr("󰄬  Aplicar cambios")),
                ]
                self.context_menu_open = True
                return

            if item.item_type == "app_card" or item.key.startswith("app:") or item.key.startswith("pkg:"):
                pkg = item.pkg_name or item.key.split(":", 1)[1]
                is_inst = item.is_installed if item.item_type == "app_card" else self.sys_mgr.is_package_installed(pkg)
                self.context_menu_items = [
                    (f"pkg:remove_now:{pkg}" if is_inst else f"pkg:install_now:{pkg}",
                     trf("󰆴  Desinstalar '{name}'", name=item.name) if is_inst else trf("  Instalar '{name}' ahora", name=item.name)),
                    ("app:refresh_state", tr("󰑐  Recargar estado del equipo")),
                ]
                self.context_menu_open = True
                return

            if item.key.startswith("kc_device:"):
                dev_id = item.key.split(":", 1)[1]
                is_p = item.is_installed
                self.context_menu_items = [
                    (f"kc:ping:{dev_id}", tr("󰂚  Enviar señal Ping")),
                    (f"kc:ring:{dev_id}", tr("󰂞  Hacer sonar teléfono")),
                    (f"kc:pair:{dev_id}", tr("󰄡  Vincular dispositivo") if not is_p else tr("󰄬  Ya vinculado")),
                    ("action:open_kdeconnect_gui", tr("󰍹  Abrir Gestor KDE Connect")),
                ]
                self.context_menu_open = True
                return

            if item.key.startswith("webapp:"):
                w_id = item.key.split(":", 1)[1]
                is_inst = self.sys_mgr.is_webapp_installed(w_id)
                self.context_menu_items = [
                    (f"webapp:toggle_now:{w_id}", trf("󰆴  Remover {w_id}", w_id=w_id) if is_inst else trf("  Instalar {w_id}", w_id=w_id)),
                    ("app:save", tr("󰄬  Aplicar cambios")),
                ]
                self.context_menu_open = True
                return

            self.context_menu_items = [
                ("item:activate", trf("󰏫  Accion en '{name}'", name=item.name[:20])),
                ("app:save", tr("󰄬  Aplicar cambios")),
                ("app:reset_all", tr("󰑐  Recargar estado")),
            ]
            self.context_menu_open = True
            return

        if x <= sidebar_w and y in self._sidebar_click_map:
            s_idx = self._sidebar_click_map[y]
            s_title = self.SECTIONS[s_idx][3]
            self.context_menu_items = [
                (f"sec:goto:{s_idx}", trf("󰁔  Ir a {s_title}", s_title=s_title)),
                ("app:save", tr("󰄬  Aplicar cambios")),
                ("app:reset_all", tr("󰑐  Recargar estado")),
                ("app:cancel", tr("󰅖  Salir")),
            ]
            self.context_menu_open = True
            return

        self.context_menu_items = [
            ("app:save", tr("󰄬  Aplicar cambios")),
            ("app:reset_all", tr("󰑐  Recargar estado")),
            ("app:cancel", tr("󰅖  Salir")),
        ]
        self.context_menu_open = True

    def _open_context_menu_for_current_selection(self) -> None:
        """Abre el menú contextual centrado en la opción o categoría seleccionada actualmente por teclado."""
        if self.modal_state or self.dropdown_open:
            return
        cols, rows = shutil.get_terminal_size((84, 42))
        sidebar_w = self._get_sidebar_width(cols)
        self.dropdown_open = False
        self.context_menu_idx = 0
        self.hover_context_idx = None
        self.context_menu_target_key = ""

        if self.active_pane == "sidebar":
            self.context_menu_x = min(cols - 28, 4)
            self.context_menu_y = min(rows - 10, max(3, self.current_section_idx * 2 + 2))
            s_title = self.SECTIONS[self.current_section_idx][3]
            self.context_menu_items = [
                (f"sec:goto:{self.current_section_idx}", trf("󰁔  Ir a {s_title}", s_title=s_title)),
                ("app:save", tr("󰄬  Aplicar cambios")),
                ("app:reset_all", tr("󰑐  Restablecer valores")),
                ("app:cancel", tr("󰅖  Cancelar y salir")),
            ]
            self.context_menu_open = True
            return

        sec_id = self.SECTIONS[self.current_section_idx][1]
        if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
            self.context_menu_items = [
                ("action:install_kdeconnect_now", tr("  Instalar KDE Connect")),
                ("app:refresh_state", tr("󰑐  Recargar estado del equipo")),
            ]
            self.context_menu_open = True
            return

        items = self.section_items.get(sec_id, [])
        if not items or self.selected_item_idx >= len(items):
            return
        item = items[self.selected_item_idx]
        self.context_menu_target_key = item.key
        self.context_menu_x = min(cols - 35, sidebar_w + 4)
        rel_idx = max(0, self.selected_item_idx - self.content_scroll_offset)
        self.context_menu_y = min(rows - 10, max(4, 5 + rel_idx * 3))

        if item.item_type == "theme_card":
            t_name = item.name
            self.context_menu_items = [
                (f"theme:activate:{t_name}", trf("󰸌  Activar '{t_name}' ahora", t_name=t_name)),
                ("theme:next_wp", tr("󰸉  Siguiente fondo")),
                ("theme:apply_user", "󰑐  Reaplicar lizarbe-apply-user"),
            ]
            self.context_menu_open = True
            return

        if item.key.startswith("suite:"):
            s_id = item.key.split(":", 1)[1]
            self.context_menu_items = [
                (f"suite:install_now:{s_id}", trf("  Instalar '{name}' ahora", name=item.name)),
                (f"suite:remove_now:{s_id}", trf("󰆴  Desinstalar '{name}'", name=item.name)),
                ("item:toggle", tr("󰔡  Conmutar seleccion")),
                ("app:save", tr("󰄬  Aplicar cambios")),
            ]
            self.context_menu_open = True
            return

        if item.item_type == "app_card" or item.key.startswith("app:") or item.key.startswith("pkg:"):
            pkg = item.pkg_name or item.key.split(":", 1)[1]
            is_inst = item.is_installed if item.item_type == "app_card" else self.sys_mgr.is_package_installed(pkg)
            self.context_menu_items = [
                (f"pkg:remove_now:{pkg}" if is_inst else f"pkg:install_now:{pkg}",
                 trf("󰆴  Desinstalar '{name}'", name=item.name) if is_inst else trf("  Instalar '{name}' ahora", name=item.name)),
                ("app:refresh_state", tr("󰑐  Recargar estado del equipo")),
            ]
            self.context_menu_open = True
            return

        if item.key.startswith("kc_device:"):
            dev_id = item.key.split(":", 1)[1]
            is_p = item.is_installed
            self.context_menu_items = [
                (f"kc:ping:{dev_id}", tr("󰂚  Enviar señal Ping")),
                (f"kc:ring:{dev_id}", tr("󰂞  Hacer sonar teléfono")),
                (f"kc:pair:{dev_id}", tr("󰄡  Vincular dispositivo") if not is_p else tr("󰄬  Ya vinculado")),
                ("action:open_kdeconnect_gui", tr("󰍹  Abrir Gestor KDE Connect")),
            ]
            self.context_menu_open = True
            return

        if item.key.startswith("webapp:"):
            w_id = item.key.split(":", 1)[1]
            is_inst = self.sys_mgr.is_webapp_installed(w_id)
            self.context_menu_items = [
                (f"webapp:toggle_now:{w_id}", trf("󰆴  Remover {w_id}", w_id=w_id) if is_inst else trf("  Instalar {w_id}", w_id=w_id)),
                ("app:save", tr("󰄬  Aplicar cambios")),
            ]
            self.context_menu_open = True
            return

        self.context_menu_items = [
            ("item:activate", trf("󰏫  Accion en '{name}'", name=item.name[:20])),
            ("app:save", tr("󰄬  Aplicar cambios")),
            ("app:reset_all", tr("󰑐  Recargar estado")),
        ]
        self.context_menu_open = True

    def _render_context_menu_overlay(self, cols: int, rows: int) -> List[str]:
        self._context_row_map.clear()
        if not self.context_menu_items:
            return []

        max_lbl = max(len(lbl) for _, lbl in self.context_menu_items)
        inner_w = max(24, min(44, max_lbl + 4))
        box_w = inner_w + 2
        box_h = len(self.context_menu_items) + 2

        start_x = min(max(2, self.context_menu_x), max(2, cols - box_w - 1))
        start_y = min(max(2, self.context_menu_y), max(2, rows - box_h - 1))
        self._context_box_bounds = (start_y, start_y + box_h - 1, start_x, start_x + box_w - 1)

        overlay: List[str] = []
        top_line = "┌" + ("─" * inner_w) + "┐"
        overlay.append(f"\033[{start_y};{start_x}H" + self.theme_engine.style("accent", "background", top_line, bold=True))

        for idx, (_, label) in enumerate(self.context_menu_items):
            scr_y = start_y + 1 + idx
            self._context_row_map[scr_y] = idx
            is_sel = (idx == self.context_menu_idx)
            is_hov = (idx == self.hover_context_idx)
            is_hi = (is_sel or is_hov)

            prefix = " ▸ " if is_hi else "   "
            row_txt = f"{prefix}{label}"[:inner_w].ljust(inner_w)
            row_bg = "soft_hover" if is_hov else ("soft_selection" if is_sel else "background")
            row_fg = "bright_foreground" if is_hi else "foreground"

            overlay.append(
                f"\033[{scr_y};{start_x}H"
                + self.theme_engine.style("accent", "background", "┃", bold=True)
                + self.theme_engine.style(row_fg, row_bg, row_txt, bold=is_hi)
                + self.theme_engine.style("accent", "background", "│", bold=True)
            )

        bot_line = "┗" + ("━" * inner_w) + "┙"
        overlay.append(f"\033[{start_y + box_h - 1};{start_x}H" + self.theme_engine.style("accent", "background", bot_line, bold=True))
        return overlay

    def _execute_context_action(self, act_id: str) -> None:
        self.context_menu_open = False
        self.hover_context_idx = None

        if act_id.startswith("sec:goto:"):
            s_idx = int(act_id.split(":")[-1])
            self._request_section_change(s_idx, focus_content=True)
            return
        if act_id == "app:save":
            self.save_all()
            return
        if act_id == "app:reset_all":
            self.reset_to_defaults()
            return
        if act_id == "app:cancel":
            self.cancel_changes()
            return
        if act_id in ("item:activate", "item:toggle"):
            self._activate_current_item()
            return

        if not self.sys_mgr.is_kdeconnect_installed() and (
            act_id.startswith("kc:") or act_id.startswith("action:kc_")
        ):
            self.status_message = tr("KDE Connect aún no está instalado en el equipo. Pulsa ' Instalar' abajo para comenzar.")
            return

        if act_id.startswith("kc:ping:"):
            d_id = act_id.split(":", 2)[-1]
            self.sys_mgr.ping_kdeconnect(d_id)
            self.status_message = trf("✓ Ping enviado al smartphone {d_id}.", d_id=d_id)
            return
        if act_id.startswith("kc:ring:"):
            d_id = act_id.split(":", 2)[-1]
            self.sys_mgr.ring_kdeconnect_device(d_id)
            self.status_message = trf("✓ Enviando alarma acústica a {d_id}...", d_id=d_id)
            return
        if act_id.startswith("kc:pair:"):
            d_id = act_id.split(":", 2)[-1]
            self.sys_mgr.pair_kdeconnect_device(d_id)
            self.status_message = trf("✓ Solicitud de vinculación enviada a {d_id}.", d_id=d_id)
            return
        if act_id == "app:refresh_state":
            self._refresh_all_state()
            self.status_message = tr("✓ Estado del equipo actualizado.")
            return

        if act_id.startswith("theme:activate:"):
            t_name = act_id.split(":", 2)[-1]
            self.status_message = trf("Activando tema '{t_name}'...", t_name=t_name)
            self.render()
            self.theme_engine.set_theme(t_name)
            self._refresh_all_state()
            self.status_message = trf("✓ Tema '{t_name}' activado.", t_name=t_name)
            return
        if act_id == "theme:next_wp":
            self._execute_action("action:next_wallpaper")
            return
        if act_id == "theme:apply_user":
            self._execute_action("action:apply_user_now")
            return

        if act_id.startswith("suite:install_now:"):
            s_id = act_id.split(":", 2)[-1]
            script_map = {s[0]: s[4] for s in self.sys_mgr.SUITES_SPEC}
            script_name = script_map.get(s_id, f"install-{s_id}.sh")
            self._run_interactive_command(
                trf("Instalando Suite {upper}", upper=s_id.upper()),
                ["bash", str(self.sys_mgr.repo_dir / "scripts" / script_name)],
            )
            self._refresh_all_state()
            self.status_message = trf("✓ Suite '{s_id}' procesada.", s_id=s_id)
            return

        if act_id.startswith("suite:remove_now:"):
            s_id = act_id.split(":", 2)[-1]
            if s_id == "core":
                self._prompt_command_modal(
                    tr("REVERTIR TEMA LIZARBE"),
                    tr("Se desinstalara el tema Lizarbe y restaurara el oficial."),
                    tr("¿Confirmar reversion del tema?"),
                    ["bash", str(self.sys_mgr.repo_dir / "uninstall.sh"), "--theme-only"],
                )
            else:
                self._prompt_command_modal(
                    trf("DESINSTALAR SUITE {upper}", upper=s_id.upper()),
                    trf("Se desinstalaran los paquetes de la suite '{s_id}'.", s_id=s_id),
                    tr("¿Confirmar desinstalacion?"),
                    ["bash", str(self.sys_mgr.repo_dir / "uninstall.sh"), f"--{s_id}"],
                )
            return

        if act_id.startswith("pkg:install_now:"):
            pkg = act_id.split(":", 2)[-1]
            helper = ["yay", "-S", "--needed", "--noconfirm", pkg] if shutil.which("yay") else ["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg]
            self._run_interactive_command(trf("Instalando paquete {pkg}", pkg=pkg), helper)
            self._refresh_all_state()
            self.status_message = trf("✓ Paquete '{pkg}' instalado.", pkg=pkg)
            return

        if act_id.startswith("pkg:remove_now:"):
            pkg = act_id.split(":", 2)[-1]
            cmd = ["omarchy-pkg-drop", pkg] if shutil.which("omarchy-pkg-drop") else ["sudo", "pacman", "-Rns", "--noconfirm", pkg]
            self._run_interactive_command(trf("Desinstalando paquete {pkg}", pkg=pkg), cmd)
            self._refresh_all_state()
            self.status_message = trf("✓ Paquete '{pkg}' desinstalado.", pkg=pkg)
            return

        if act_id.startswith("webapp:toggle_now:"):
            w_id = act_id.split(":", 2)[-1]
            is_inst = self.sys_mgr.is_webapp_installed(w_id)
            self.sys_mgr.install_or_remove_webapp(w_id, install=not is_inst)
            self._refresh_all_state()
            self.status_message = trf("✓ Webapp {w_id} {v}.", w_id=w_id, v='eliminada' if is_inst else 'instalada')
            return

        if act_id.startswith("action:"):
            self._execute_action(act_id)
            return

    # ==========================
    # VENTANAS MODALES DE CONFIRMACIÓN
    # ==========================

    def _prompt_command_modal(self, title: str, msg1: str, msg2: str, cmd_args: List[str]) -> None:
        self._pending_cmd_title = f" {title.strip()} "
        self._pending_cmd_msg1 = msg1
        self._pending_cmd_msg2 = msg2
        self._pending_cmd_args = cmd_args
        self.modal_state = "confirm_command"
        self.modal_selected_idx = 1

    def _get_kdeconnect_guide_lines(self) -> List[Tuple[str, str]]:
        return [
            ("sec_hdr", tr("1. INSTALAR LA APP EN TU SMARTPHONE")),
            ("text", tr("Descarga e instala la aplicación oficial KDE Connect:")),
            ("box_top", "┌────────────────────────────────────────────────────────┐"),
            ("box_item", tr("│ • Android: Google Play Store o F-Droid (código libre)  │")),
            ("box_item", "│ • iOS (iPhone / iPad): App Store oficial               │"),
            ("box_item", "│   Busca exactamente: \"KDE Connect\"                     │"),
            ("box_bot", "└────────────────────────────────────────────────────────┘"),
            ("empty", ""),
            ("sec_hdr", tr("2. CONECTAR AMBOS EQUIPOS A LA MISMA RED (WI-FI)")),
            ("text", tr("Tu PC y tu smartphone deben estar conectados a la misma red:")),
            ("diagram", "       ┌──────────────┐                 ┌──────────┐        "),
            ("diagram", tr("       │ Lizarbe / PC │     (((·)))     │  Móvil   │        ")),
            ("diagram", "       │  ┌────────┐  │      Wi-Fi      │ ┌──────┐ │        "),
            ("diagram", "       │  │ KDE    │  │ <=============> │ │ KDE  │ │        "),
            ("diagram", "       │  │ Connect│  │    1714-1764    │ │ App  │ │        "),
            ("diagram", "       │  └────────┘  │                 │ └──────┘ │        "),
            ("diagram", "       │   [======]   │                 │   ( )    │        "),
            ("diagram", "       └──────────────┘                 └──────────┘        "),
            ("bullet", tr("• Ambos dispositivos deben conectarse a la misma red local.")),
            ("bullet", tr("• Si no tienes Wi-Fi común, activa 'Zona Wi-Fi' en tu móvil.")),
            ("bullet", tr("• Desactiva temporalmente VPNs si bloquean el tráfico local.")),
            ("empty", ""),
            ("sec_hdr", tr("3. PUERTOS EN EL CORTAFUEGOS (UFW)")),
            ("text", tr("Omarchy protege las conexiones entrantes con cortafuegos:")),
            ("box_top", "┌────────────────────────────────────────────────────────┐"),
            ("box_item", tr("│ Si ves el aviso 'Cortafuegos Bloqueado' en este panel, │")),
            ("box_item", tr("│ presiona el botón '[ Abrir Puertos ]' para autorizar   │")),
            ("box_item", tr("│ el tráfico en los puertos 1714 a 1764 (TCP y UDP).     │")),
            ("box_bot", "└────────────────────────────────────────────────────────┘"),
            ("empty", ""),
            ("sec_hdr", tr("4. EMPAREJAR Y VINCULAR DISPOSITIVOS")),
            ("text", tr("Pasos para enlazar tu teléfono con la PC:")),
            ("box_top", "┌────────────────────────────────────────────────────────┐"),
            ("box_item", tr("│ 1. Abre la aplicación KDE Connect en tu teléfono.      │")),
            ("box_item", tr("│ 2. En 'Dispositivos disponibles', selecciona tu PC.    │")),
            ("box_item", tr("│ 3. Pulsa en 'Solicitar vinculación'.                   │")),
            ("box_item", tr("│ 4. Acepta la solicitud que aparecerá en tu PC.         │")),
            ("box_item", tr("│    O en este panel, pulsa en tu móvil '[ Vincular ]'.  │")),
            ("box_item", tr("│ 5. Una vez vinculado, el botón cambiará a [ Vinculado ]│")),
            ("box_bot", "└────────────────────────────────────────────────────────┘"),
            ("empty", ""),
            ("sec_hdr", tr("5. FUNCIONES Y VENTAJAS EN OMARCHY")),
            ("box_top", "┌────────────────────────────────────────────────────────┐"),
            ("box_item", tr("│ ✓ Portapapeles compartido en tiempo real (copiar/pegar)│")),
            ("box_item", tr("│ ✓ Notificaciones de WhatsApp y llamadas en pantalla    │")),
            ("box_item", tr("│ ✓ Envío rápido de fotos y archivos sin cables          │")),
            ("box_item", tr("│ ✓ Control multimedia (pausar música) y ratón táctil    │")),
            ("box_item", tr("│ ✓ Encontrar tu teléfono haciéndolo sonar desde la PC   │")),
            ("box_bot", "└────────────────────────────────────────────────────────┘"),
        ]

    def _render_kdeconnect_guide_overlay(self, cols: int, rows: int) -> List[str]:
        self._modal_button_click_map.clear()
        self._guide_lines = self._get_kdeconnect_guide_lines()

        gw = min(78, cols - 4)
        inner_gw = gw - 2
        avail_text_w = max(10, inner_gw - 2)

        max_gh = max(12, rows - 3)
        gh = min(36, max_gh)
        content_h = max(4, gh - 8)
        gh = content_h + 8
        self._guide_content_h = content_h

        start_x = max(2, (cols - gw) // 2)
        start_y = max(2, (rows - gh) // 2)
        if start_y + gh >= rows:
            start_y = max(2, rows - gh - 1)
        self._guide_box_bounds = (start_y, start_y + gh - 1, start_x, start_x + gw - 1)

        total_lines = len(self._guide_lines)
        max_scroll = max(0, total_lines - content_h)
        self.guide_scroll_offset = max(0, min(self.guide_scroll_offset, max_scroll))

        overlay: List[str] = []

        # 1. Borde superior
        top_line = "┌" + ("─" * inner_gw) + "┐"
        overlay.append(f"\033[{start_y};{start_x}H" + self.theme_engine.style("accent", "background", top_line, bold=True))

        # 2. Barra de título con indicador de desplazamiento
        title = tr(" GUIA DE CONEXION: OMARCHY & SMARTPHONE ")
        if max_scroll > 0:
            scr_pct = f" [{self.guide_scroll_offset + 1}-{min(total_lines, self.guide_scroll_offset + content_h)}/{total_lines}] "
        else:
            scr_pct = ""
        avail_title_w = max(1, inner_gw - len(scr_pct))
        title_padded = title[:avail_title_w].ljust(avail_title_w) + scr_pct
        overlay.append(
            f"\033[{start_y + 1};{start_x}H"
            + self.theme_engine.style("accent", "background", "┃", bold=True)
            + self.theme_engine.style("bright_foreground", "accent", title_padded[:inner_gw].ljust(inner_gw), bold=True)
            + self.theme_engine.style("accent", "background", "│", bold=True)
        )

        # 3. Separador horizontal
        sep_line = "├" + ("─" * inner_gw) + "┤"
        overlay.append(f"\033[{start_y + 2};{start_x}H" + self.theme_engine.style("muted", "background", sep_line))

        # 4. Líneas de contenido visible con barra de desplazamiento lateral
        thumb_row = int((self.guide_scroll_offset / max_scroll) * (content_h - 1)) if max_scroll > 0 else -1

        for r_idx in range(content_h):
            cur_line_idx = self.guide_scroll_offset + r_idx
            scr_y = start_y + 3 + r_idx

            if cur_line_idx < total_lines:
                l_type, l_raw = self._guide_lines[cur_line_idx]
            else:
                l_type, l_raw = "empty", ""

            # Borde derecho: indicador de desplazamiento '█' sobrio
            if max_scroll > 0 and r_idx == thumb_row:
                r_border = self.theme_engine.style("bright_foreground", "accent", "█", bold=True)
            else:
                r_border = self.theme_engine.style("accent" if max_scroll > 0 else "muted", "background", "│")

            l_border = self.theme_engine.style("accent", "background", "┃", bold=True)

            # Formateo y estilización por tipo
            if l_type == "sec_hdr":
                raw_txt = (" ━━ " + l_raw + " ").ljust(avail_text_w, "─")[:avail_text_w]
                styled_content = self.theme_engine.style("bright_foreground", "background", raw_txt, bold=True)
            elif l_type in ("box_top", "box_bot"):
                if avail_text_w < len(l_raw):
                    raw_txt = l_raw[:avail_text_w].ljust(avail_text_w)
                else:
                    pad = (avail_text_w - len(l_raw)) // 2
                    rem_w = avail_text_w - pad - len(l_raw)
                    raw_txt = (" " * pad) + l_raw + (" " * rem_w)
                styled_content = self.theme_engine.style("accent", "background", raw_txt, bold=True)
            elif l_type == "box_item":
                if avail_text_w < len(l_raw):
                    raw_txt = l_raw[:avail_text_w].ljust(avail_text_w)
                    styled_content = self.theme_engine.style("bright_foreground", "background", raw_txt)
                else:
                    pad = (avail_text_w - len(l_raw)) // 2
                    left_pad = " " * pad
                    rem_w = avail_text_w - pad - len(l_raw)
                    right_pad = " " * rem_w
                    if l_raw.startswith("│") and l_raw.endswith("│"):
                        box_core = l_raw[1:-1]
                        styled_content = (
                            self.theme_engine.style("foreground", "background", left_pad)
                            + self.theme_engine.style("accent", "background", "│", bold=True)
                            + self.theme_engine.style("bright_foreground", "background", box_core)
                            + self.theme_engine.style("accent", "background", "│", bold=True)
                            + self.theme_engine.style("foreground", "background", right_pad)
                        )
                    else:
                        raw_txt = (left_pad + l_raw + right_pad)[:avail_text_w]
                        styled_content = self.theme_engine.style("bright_foreground", "background", raw_txt)
            elif l_type == "diagram":
                pad = max(0, (avail_text_w - len(l_raw.rstrip())) // 2)
                raw_txt = ((" " * pad) + l_raw.rstrip())[:avail_text_w].ljust(avail_text_w)
                styled_content = self.theme_engine.style("bright_foreground", "background", raw_txt, bold=True)
            elif l_type == "bullet":
                sym = l_raw[0] if l_raw and l_raw[0] in ("•", "✓") else "•"
                rest = l_raw[1:].strip() if l_raw and l_raw[0] in ("•", "✓") else l_raw
                sym_str = f"  {sym} "
                avail_rest = max(0, avail_text_w - len(sym_str))
                rest_padded = rest[:avail_rest].ljust(avail_rest)
                styled_content = (
                    self.theme_engine.style("accent", "background", sym_str, bold=True)
                    + self.theme_engine.style("foreground", "background", rest_padded)
                )
            elif l_type == "text":
                raw_txt = ("   " + l_raw)[:avail_text_w].ljust(avail_text_w)
                styled_content = self.theme_engine.style("foreground", "background", raw_txt)
            else:
                styled_content = self.theme_engine.style("foreground", "background", " " * avail_text_w)

            overlay.append(f"\033[{scr_y};{start_x}H{l_border} {styled_content} {r_border}")

        # 5. Espacio en blanco antes de botón
        btn_pre_y = start_y + 3 + content_h
        empty_line = " " * inner_gw
        overlay.append(
            f"\033[{btn_pre_y};{start_x}H"
            + self.theme_engine.style("accent", "background", "┃", bold=True)
            + self.theme_engine.style("foreground", "background", empty_line)
            + self.theme_engine.style("accent", "background", "│", bold=True)
        )

        # 6. Botón 3D sobrio: [ Entendido (Enter / Esc) ]
        btn_y_top = start_y + 4 + content_h
        self._modal_button_row_range = (btn_y_top, btn_y_top + 2)

        b_lbl = " Entendido (Enter / Esc) "
        bw = len(b_lbl) + 2
        pad_left = max(1, (inner_gw - bw) // 2)
        pad_right = max(0, inner_gw - bw - pad_left)

        btn_start_x = start_x + 1 + pad_left
        self._modal_button_click_map[0] = (btn_start_x, btn_start_x + bw - 1)

        is_b_hov = (self.hover_modal_btn_idx == 0)
        b_col = "accent" if is_b_hov else "bright_foreground"
        sh_col = "accent"
        btn_bg = "soft_hover" if is_b_hov else "soft_selection"

        r0_s = self.theme_engine.style(b_col, "background", "┌" + ("─" * len(b_lbl)) + "┐", bold=True)
        r1_s = (
            self.theme_engine.style(sh_col, "background", "┃", bold=True)
            + self.theme_engine.style("bright_foreground", btn_bg, b_lbl, bold=True)
            + self.theme_engine.style(b_col, "background", "│", bold=True)
        )
        r2_s = self.theme_engine.style(sh_col, "background", "┗" + ("━" * len(b_lbl)) + "┙", bold=True)

        overlay.append(
            f"\033[{btn_y_top};{start_x}H"
            + self.theme_engine.style("accent", "background", "┃", bold=True)
            + self.theme_engine.style("foreground", "background", " " * pad_left)
            + r0_s
            + self.theme_engine.style("foreground", "background", " " * pad_right)
            + self.theme_engine.style("accent", "background", "│", bold=True)
        )
        overlay.append(
            f"\033[{btn_y_top + 1};{start_x}H"
            + self.theme_engine.style("accent", "background", "┃", bold=True)
            + self.theme_engine.style("foreground", "background", " " * pad_left)
            + r1_s
            + self.theme_engine.style("foreground", "background", " " * pad_right)
            + self.theme_engine.style("accent", "background", "│", bold=True)
        )
        overlay.append(
            f"\033[{btn_y_top + 2};{start_x}H"
            + self.theme_engine.style("accent", "background", "┃", bold=True)
            + self.theme_engine.style("foreground", "background", " " * pad_left)
            + r2_s
            + self.theme_engine.style("foreground", "background", " " * pad_right)
            + self.theme_engine.style("accent", "background", "│", bold=True)
        )

        # 7. Borde inferior
        bot_line = "┗" + ("━" * inner_gw) + "┙"
        overlay.append(f"\033[{start_y + gh - 1};{start_x}H" + self.theme_engine.style("accent", "background", bot_line, bold=True))

        return overlay

    def _render_modal_overlay(self, cols: int, rows: int) -> List[str]:
        if self.modal_state == "kdeconnect_guide":
            return self._render_kdeconnect_guide_overlay(cols, rows)

        self._modal_button_click_map.clear()

        if self.modal_state == "confirm_section_change":
            title = tr(" CAMBIOS SIN APLICAR ")
            msg_1 = tr("Hay cambios pendientes en esta seccion.")
            msg_2 = tr("¿Aplicar antes de cambiar de seccion?")
            modal_btns = [
                (0, tr(" Descartar ")),
                (1, tr(" Cancelar ")),
                (2, tr(" Aplicar ")),
            ]
        elif self.modal_state == "confirm_command":
            title = self._pending_cmd_title or tr(" CONFIRMAR ACCION ")
            msg_1 = self._pending_cmd_msg1
            msg_2 = self._pending_cmd_msg2
            modal_btns = [
                (0, tr(" Cancelar ")),
                (1, tr(" Confirmar ")),
            ]
        else:
            title = tr(" RECARGAR ESTADO ")
            msg_1 = tr("Se descartaran las selecciones pendientes")
            msg_2 = tr("y se recargara el estado actual del sistema.")
            modal_btns = [
                (0, tr(" Cancelar ")),
                (1, tr(" Confirmar ")),
            ]

        mw = min(max(54, len(msg_1) + 8, len(msg_2) + 8), cols - 4)
        inner_mw = mw - 2
        mh = 10
        start_x = max(2, (cols - mw) // 2)
        start_y = max(3, (rows - mh) // 2)

        overlay: List[str] = []

        top_line = "┌" + ("─" * inner_mw) + "┐"
        title_centered = title.center(inner_mw)[:inner_mw]
        sep_line = "├" + ("─" * inner_mw) + "┤"
        m1_line = msg_1.center(inner_mw)[:inner_mw]
        m2_line = msg_2.center(inner_mw)[:inner_mw]
        empty_line = " " * inner_mw
        bot_line = "┗" + ("━" * inner_mw) + "┙"

        overlay.append(f"\033[{start_y};{start_x}H" + self.theme_engine.style("bright_foreground", "background", top_line, bold=True))
        overlay.append(f"\033[{start_y + 1};{start_x}H" + self.theme_engine.style("bright_foreground", "accent", "┃" + title_centered + "│", bold=True))
        overlay.append(f"\033[{start_y + 2};{start_x}H" + self.theme_engine.style("muted", "background", sep_line))
        overlay.append(f"\033[{start_y + 3};{start_x}H" + self.theme_engine.style("bright_foreground", "background", "┃" + m1_line + "│", bold=True))
        overlay.append(f"\033[{start_y + 4};{start_x}H" + self.theme_engine.style("foreground", "background", "┃" + m2_line + "│"))
        overlay.append(f"\033[{start_y + 5};{start_x}H" + self.theme_engine.style("foreground", "background", "┃" + empty_line + "│"))

        gap = 2
        btns_total_w = sum(len(lbl) + 2 for _, lbl in modal_btns) + gap * (len(modal_btns) - 1)
        pad_left = max(1, (inner_mw - btns_total_w) // 2)
        pad_right = max(0, inner_mw - btns_total_w - pad_left)

        btn_y_top = start_y + 6
        self._modal_button_row_range = (btn_y_top, btn_y_top + 2)

        b_r0 = [self.theme_engine.style("foreground", "background", "┃" + (" " * pad_left))]
        b_r1 = [self.theme_engine.style("foreground", "background", "┃" + (" " * pad_left))]
        b_r2 = [self.theme_engine.style("foreground", "background", "┃" + (" " * pad_left))]

        cur_x = start_x + 1 + pad_left
        for b_idx, b_lbl in modal_btns:
            bw = len(b_lbl) + 2
            is_b_hov = (self.hover_modal_btn_idx == b_idx)
            is_b_sel = (self.modal_selected_idx == b_idx) or is_b_hov
            self._modal_button_click_map[b_idx] = (cur_x, cur_x + bw - 1)

            b_col = "bright_foreground" if is_b_sel else "foreground"
            sh_col = "accent" if is_b_sel else "muted"
            btn_bg = "soft_hover" if is_b_hov else ("soft_selection" if is_b_sel else "background")

            r0_s = self.theme_engine.style(b_col, "background", "┌" + ("─" * len(b_lbl)) + "┐", bold=is_b_sel)
            r1_s = (
                self.theme_engine.style(sh_col, "background", "┃", bold=True)
                + self.theme_engine.style("bright_foreground" if is_b_sel else "foreground", btn_bg, b_lbl, bold=is_b_sel)
                + self.theme_engine.style(b_col, "background", "│", bold=is_b_sel)
            )
            r2_s = self.theme_engine.style(sh_col, "background", "┗" + ("━" * len(b_lbl)) + "┙", bold=True)

            sep_gap = self.theme_engine.style("foreground", "background", " " * gap) if b_idx < len(modal_btns) - 1 else ""
            b_r0.append(r0_s + sep_gap)
            b_r1.append(r1_s + sep_gap)
            b_r2.append(r2_s + sep_gap)
            cur_x += bw + gap

        b_r0.append(self.theme_engine.style("foreground", "background", (" " * pad_right) + "│"))
        b_r1.append(self.theme_engine.style("foreground", "background", (" " * pad_right) + "│"))
        b_r2.append(self.theme_engine.style("foreground", "background", (" " * pad_right) + "│"))

        overlay.append(f"\033[{btn_y_top};{start_x}H" + "".join(b_r0))
        overlay.append(f"\033[{btn_y_top + 1};{start_x}H" + "".join(b_r1))
        overlay.append(f"\033[{btn_y_top + 2};{start_x}H" + "".join(b_r2))
        overlay.append(f"\033[{start_y + 9};{start_x}H" + self.theme_engine.style("accent", "background", bot_line, bold=True))

        return overlay

    def _execute_modal_choice(self, choice_idx: int) -> None:
        state = self.modal_state
        self.modal_state = None
        self.hover_modal_btn_idx = None

        if state == "confirm_section_change":
            if choice_idx == 0:
                self.settings = dict(self.saved_settings)
                self.status_message = tr("Cambios descartados.")
                if self.pending_section_idx is not None:
                    self.current_section_idx = self.pending_section_idx
                    sec_id = self.SECTIONS[self.current_section_idx][1]
                    self.section_items[sec_id] = self._build_section_items_for_id(sec_id)
                    self.selected_item_idx = 0
                    self.content_scroll_offset = 0
                    if self.pending_focus_content:
                        self.active_pane = "content"
            elif choice_idx == 1:
                self.status_message = tr("Cambio de seccion cancelado.")
            elif choice_idx == 2:
                self.save_all()
                if self.pending_section_idx is not None:
                    self.current_section_idx = self.pending_section_idx
                    sec_id = self.SECTIONS[self.current_section_idx][1]
                    self.section_items[sec_id] = self._build_section_items_for_id(sec_id)
                    self.selected_item_idx = 0
                    self.content_scroll_offset = 0
                    if self.pending_focus_content:
                        self.active_pane = "content"
            self.pending_section_idx = None

        elif state == "confirm_command":
            if choice_idx == 1 and self._pending_cmd_args:
                title = self._pending_cmd_title.strip()
                cmd = list(self._pending_cmd_args)
                self._pending_cmd_args = []
                if cmd and cmd[0] == "internal_webapp":
                    _, act, w_id = cmd
                    self.sys_mgr.install_or_remove_webapp(w_id, install=(act == "install"))
                    self._refresh_all_state()
                    st = "instalada" if act == "install" else "removida"
                    self.status_message = trf("✓ Webapp {w_id} {st}.", w_id=w_id, st=st)
                else:
                    self._run_interactive_command(title, cmd)
                    self._refresh_all_state()
                    self.status_message = trf("✓ {title} completado.", title=title)
            else:
                self.status_message = tr("Operacion cancelada.")

        elif state == "confirm_reset":
            if choice_idx == 1:
                self._refresh_all_state()
                self.status_message = tr("✓ Estado recargado desde el sistema.")
            else:
                self.status_message = tr("Recarga cancelada.")

    # ==========================
    # LECTURA, ESCRITURA Y EJECUCIÓN DE ACCIONES
    # ==========================

    def _get_item_value(self, item: SectionItem) -> Any:
        key = item.key
        if key in self.settings:
            return self.settings[key]
        return "-"

    def _set_item_value(self, key: str, val: Any) -> None:
        if key == "active_theme":
            self.settings["active_theme"] = str(val)
            wps = self.theme_engine.list_wallpapers_for_theme(str(val))
            if wps:
                self.settings["wallpaper"] = wps[0]
            self.section_items["theme"] = self._build_theme_section_items()
            self.status_message = trf("Tema '{val}' seleccionado (Pulsa 'Aplicar').", val=val)
            return

        if key == "wallpaper":
            self.settings["wallpaper"] = str(val)
            self.status_message = trf("Fondo '{val}' seleccionado (Pulsa 'Aplicar').", val=val)
            return

        self.settings[key] = val
        if key.startswith("suite:"):
            s_id = key.split(":", 1)[1]
            st = tr("marcada para instalar") if val else tr("marcada para desinstalar")
            self.status_message = trf("Suite '{s_id}' {st} (Pulsa 'Aplicar').", s_id=s_id, st=st)
        elif key.startswith("pkg:"):
            pkg = key.split(":", 1)[1]
            st = tr("marcado para instalar") if val else tr("marcado para desinstalar")
            self.status_message = trf("Paquete '{pkg}' {st} (Pulsa 'Aplicar').", pkg=pkg, st=st)
        elif key.startswith("webapp:"):
            w_id = key.split(":", 1)[1]
            st = tr("marcada para instalar") if val else tr("marcada para remover")
            self.status_message = trf("Webapp '{w_id}' {st} (Pulsa 'Aplicar').", w_id=w_id, st=st)

    def has_unsaved_changes(self) -> bool:
        return self.settings != self.saved_settings

    def _request_section_change(self, target_idx: int, focus_content: bool = False) -> None:
        self.dropdown_open = False
        self.context_menu_open = False
        target_idx = max(0, min(len(self.SECTIONS) - 1, target_idx))
        if target_idx == self.current_section_idx:
            if focus_content:
                self.active_pane = "content"
            return

        if self.has_unsaved_changes():
            self.modal_state = "confirm_section_change"
            self.pending_section_idx = target_idx
            self.pending_focus_content = focus_content
            self.modal_selected_idx = 2
        else:
            self.current_section_idx = target_idx
            sec_id = self.SECTIONS[target_idx][1]
            self.section_items[sec_id] = self._build_section_items_for_id(sec_id)
            self.selected_item_idx = 0
            self.content_scroll_offset = 0
            if focus_content:
                self.active_pane = "content"

    def _execute_action(self, action_key: str) -> None:
        if action_key.startswith("theme_card:"):
            t_name = action_key.split(":", 1)[1]
            self._set_item_value("active_theme", t_name)
            return

        if action_key.startswith("info:"):
            self.status_message = tr("Verificando estado del sistema...")
            self.render()
            self.sys_mgr.check_remote_version()
            self._refresh_all_state()
            self.status_message = f"✓ {self.sys_mgr.sync_state_cache}"
            return

        if action_key == "action:next_wallpaper":
            try:
                subprocess.Popen(
                    ["omarchy-theme-bg-next"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.status_message = tr("✓ Fondo de pantalla rotado.")
            except Exception:
                self.status_message = tr("No se encontró 'omarchy-theme-bg-next'.")
            return

        if action_key == "action:open_nwg_look":
            if shutil.which("nwg-look"):
                try:
                    subprocess.Popen(
                        ["nwg-look"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.status_message = "✓ Abriendo nwg-look..."
                except Exception:
                    self.status_message = tr("Error al iniciar nwg-look.")
            else:
                self.status_message = tr("nwg-look no está instalado (instala Base del Sistema).")
            return

        if action_key == "action:apply_user_now":
            self.status_message = tr("Aplicando configuracion de usuario Lizarbe...")
            self.render()
            sel_t = str(self.settings.get("active_theme", self.theme_engine.current_theme))
            ok = self.sys_mgr.run_apply_user_script(target_theme=sel_t)
            self._refresh_all_state()
            self.status_message = tr("✓ Tema, iconos y dotfiles de usuario aplicados.") if ok else tr("[AVISO] Aplicado parcial.")
            return

        if action_key == "action:set_zen_default":
            if shutil.which("omarchy-default-browser"):
                subprocess.run(["omarchy-default-browser", "zen"], capture_output=True, timeout=5)
                self.status_message = "✓ Zen Browser establecido como predeterminado."
            else:
                self.status_message = tr("No se encontró 'omarchy-default-browser'.")
            return

        if action_key == "action:restart_shell":
            try:
                subprocess.Popen(
                    ["omarchy-restart-shell"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.status_message = tr("✓ Reiniciando barra superior de Omarchy...")
            except Exception:
                self.status_message = tr("No se encontró 'omarchy-restart-shell'.")
            return

        if action_key == "action:check_remote":
            self.status_message = tr("Consultando el repositorio de Lizarbe...")
            self.render()
            ok, rem, sync_msg = self.sys_mgr.check_remote_version()
            self.section_items["status"] = self._build_status_section_items()
            self.status_message = f"✓ {sync_msg}" if ok else tr("Sin conexion al repositorio.")
            return

        if action_key == "action:update_github":
            self._run_interactive_command(
                tr("Actualizando el sistema (omarchy update)"),
                ["omarchy-update"],
            )
            self._refresh_all_state()
            self.status_message = tr("✓ Actualización de Lizarbe completada.")
            return

        if action_key == "action:update_force":
            self._run_interactive_command(
                tr("Reparando la integración de Lizarbe"),
                ["bash", "-c", "lizarbe-doctor --fix; lizarbe apply"],
            )
            self._refresh_all_state()
            self.status_message = tr("✓ Reparación completada.")
            return

        # Perfiles de instalación rápida
        if action_key == "action:install_all":
            self._prompt_command_modal(
                tr("INSTALAR TODO (--all)"),
                tr("Se instalara el tema base y todas las suites (incluyendo 3D)."),
                tr("¿Deseas iniciar la instalacion completa?"),
                ["bash", str(self.sys_mgr.repo_dir / "install.sh"), "--all"],
            )
            return

        if action_key == "action:install_no_3d":
            self._prompt_command_modal(
                tr("INSTALAR SIN 3D (--no-3d)"),
                tr("Se instalara el tema base y todas las suites excepto 3D."),
                tr("¿Deseas iniciar la instalacion?"),
                ["bash", str(self.sys_mgr.repo_dir / "install.sh"), "--no-3d"],
            )
            return

        if action_key == "action:install_core_only":
            self._prompt_command_modal(
                tr("INSTALAR SOLO BASE (--core-only)"),
                tr("Se instalara unicamente el tema Lizarbe, iconos, GTK y dotfiles."),
                tr("¿Deseas iniciar la instalacion base?"),
                ["bash", str(self.sys_mgr.repo_dir / "install.sh"), "--core-only"],
            )
            return

        # Acciones de desinstalación con confirmación
        uninstall_map = {
            "action:uninstall_theme_only": (
                tr("REVERTIR TEMA LIZARBE"),
                tr("Se eliminara el tema Lizarbe y se restaurara el tema oficial."),
                "--theme-only",
            ),
            "action:uninstall_apps_only": (
                tr("DESINSTALAR TODAS LAS SUITES"),
                tr("Se desinstalaran todas las suites de software conservando el tema."),
                "--apps-only",
            ),
            "action:uninstall_all": (
                tr("DESINSTALACION COMPLETA"),
                tr("Se eliminara el tema Lizarbe y todas las suites de software."),
                "--all",
            ),
            "action:uninstall_2d": (
                tr("DESINSTALAR SUITE 2D"),
                tr("Se desinstalaran Krita, LibreSprite, Inkscape y Pinta."),
                "--2d",
            ),
            "action:uninstall_3d": (
                tr("DESINSTALAR SUITE 3D & CAD"),
                tr("Se desinstalaran Blender, FreeCAD, Godot y Blockbench."),
                "--3d",
            ),
            "action:uninstall_dev": (
                tr("DESINSTALAR SUITE DESARROLLO"),
                tr("Se desinstalaran VS Code, Lazygit, Docker y Lazydocker."),
                "--dev",
            ),
            "action:uninstall_office": (
                tr("DESINSTALAR SUITE OFIMATICA"),
                tr("Se desinstalaran genOffice, ONLYOFFICE, LibreOffice, Obsidian y Xournal++."),
                "--office",
            ),
            "action:uninstall_multimedia": (
                tr("DESINSTALAR SUITE MULTIMEDIA"),
                tr("Se desinstalaran Kdenlive, Shotcut, OBS Studio y Audacity."),
                "--multimedia",
            ),
            "action:uninstall_webapps": (
                tr("REMOVER WEBAPPS"),
                tr("Se eliminaran los accesos de WhatsApp Web y YouTube."),
                "--webapps",
            ),
        }
        if action_key in uninstall_map:
            u_title, u_msg, u_flag = uninstall_map[action_key]
            self._prompt_command_modal(
                u_title,
                u_msg,
                tr("¿Confirmas esta desinstalacion?"),
                ["bash", str(self.sys_mgr.repo_dir / "uninstall.sh"), "--yes", u_flag],
            )
            return

        # Acciones para tarjetas de aplicaciones (app_card) y paquetes
        if action_key.startswith("app:"):
            pkg = action_key.split(":", 1)[1]
            is_inst = self.sys_mgr.is_package_installed(pkg)
            if is_inst:
                rm_cmd = ["omarchy-pkg-drop", pkg] if shutil.which("omarchy-pkg-drop") else ["sudo", "pacman", "-Rns", "--noconfirm", pkg]
                self._prompt_command_modal(
                    trf("DESINSTALAR {upper}", upper=pkg.upper()),
                    trf("Se desinstalará el paquete '{pkg}' del equipo.", pkg=pkg),
                    tr("¿Deseas desinstalar esta aplicación?"),
                    rm_cmd,
                )
            else:
                helper = ["yay", "-S", "--needed", "--noconfirm", pkg] if shutil.which("yay") else ["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg]
                self._prompt_command_modal(
                    trf("INSTALAR {upper}", upper=pkg.upper()),
                    trf("Se descargará e instalará '{pkg}' en tu equipo.", pkg=pkg),
                    tr("¿Deseas iniciar la instalación?"),
                    helper,
                )
            return

        # Acciones para webapps integradas
        if action_key.startswith("webapp:"):
            w_id = action_key.split(":", 1)[1]
            is_inst = self.sys_mgr.is_webapp_installed(w_id)
            if is_inst:
                self._prompt_command_modal(
                    trf("REMOVER WEBAPP {upper}", upper=w_id.upper()),
                    trf("Se eliminará el acceso de '{w_id}' de tu sistema.", w_id=w_id),
                    tr("¿Deseas desinstalar esta aplicación web?"),
                    ["internal_webapp", "remove", w_id],
                )
            else:
                self._prompt_command_modal(
                    trf("INSTALAR WEBAPP {upper}", upper=w_id.upper()),
                    trf("Se creará el acceso integrado de '{w_id}' en tu sistema.", w_id=w_id),
                    tr("¿Deseas instalar esta aplicación web?"),
                    ["internal_webapp", "install", w_id],
                )
            return

        # Acciones para KDE Connect cuando no está instalado
        if not self.sys_mgr.is_kdeconnect_installed():
            if action_key not in ("action:install_kdeconnect_now", "action:kc_how_to_use") and (
                action_key.startswith("kc_")
                or action_key.startswith("action:kc_")
                or action_key.startswith("info:kc_")
                or action_key in (
                    "action:open_kdeconnect_gui",
                    "action:uninstall_kdeconnect",
                )
            ):
                self.status_message = tr("KDE Connect aún no está instalado en el equipo. Pulsa ' Instalar' abajo para comenzar.")
                return

        if action_key == "action:kc_how_to_use":
            self.guide_scroll_offset = 0
            self.modal_state = "kdeconnect_guide"
            self.modal_selected_idx = 0
            return

        if action_key.startswith("kc_device:"):
            dev_id = action_key.split(":", 1)[1]
            devices = self.sys_mgr.get_kdeconnect_devices()
            dev_info = next((d for d in devices if d["id"] == dev_id), None)
            is_paired = dev_info["paired"] if dev_info else False
            dev_name = dev_info["name"] if dev_info else dev_id
            if is_paired:
                ok = self.sys_mgr.ping_kdeconnect(dev_id)
                self.status_message = trf("✓ Dispositivo '{dev_name}' vinculado y sincronizado. Ping enviado con éxito.", dev_name=dev_name) if ok else trf("✓ Dispositivo '{dev_name}' vinculado.", dev_name=dev_name)
            else:
                ok = self.sys_mgr.pair_kdeconnect_device(dev_id)
                if ok:
                    self.status_message = trf("✓ Solicitud de vinculación enviada a '{dev_name}'. Acepta en tu smartphone.", dev_name=dev_name)
                else:
                    self.status_message = trf("No se pudo enviar solicitud de vinculación a '{dev_name}'.", dev_name=dev_name)
            return

        # Acciones exclusivas de KDE Connect
        if action_key == "action:install_kdeconnect_now":
            helper = ["yay", "-S", "--needed", "--noconfirm", "kdeconnect"] if shutil.which("yay") else ["sudo", "pacman", "-S", "--needed", "--noconfirm", "kdeconnect"]
            self._prompt_command_modal(
                tr("INSTALAR KDE CONNECT"),
                tr("Permite enlazar notificaciones, fotos, portapapeles y archivos."),
                tr("¿Deseas instalar KDE Connect?"),
                helper,
            )
            return

        if action_key == "action:uninstall_kdeconnect":
            rm_cmd = ["omarchy-pkg-drop", "kdeconnect"] if shutil.which("omarchy-pkg-drop") else ["sudo", "pacman", "-Rns", "--noconfirm", "kdeconnect"]
            self._prompt_command_modal(
                tr("DESINSTALAR KDE CONNECT"),
                tr("Se desinstalará KDE Connect y se detendrá su demonio."),
                tr("¿Confirmas la desinstalación?"),
                rm_cmd,
            )
            return

        if action_key == "action:open_kdeconnect_gui":
            ok = self.sys_mgr.open_kdeconnect_gui()
            self.status_message = "✓ Abriendo gestor KDE Connect..." if ok else tr("No se pudo abrir la interfaz gráfica de KDE Connect.")
            return

        if action_key == "action:kc_toggle_daemon":
            self.sys_mgr.start_or_restart_kdeconnect()
            self._refresh_all_state()
            self.status_message = tr("✓ Demonio de KDE Connect reiniciado.")
            return

        if action_key == "action:kc_ping_all":
            ok = self.sys_mgr.ping_kdeconnect()
            devs = self.sys_mgr.get_kdeconnect_devices()
            paired = [d for d in devs if d.get("paired")]
            names = ", ".join(d["name"] for d in paired) if paired else "smartphone"
            self.status_message = trf("✓ Señal ping enviada a '{names}'.", names=names) if ok else tr("No hay smartphone vinculado o en línea para enviar ping.")
            return

        if action_key == "action:kc_ring":
            ok = self.sys_mgr.ring_kdeconnect_device()
            devs = self.sys_mgr.get_kdeconnect_devices()
            paired = [d for d in devs if d.get("paired")]
            target_name = paired[0]["name"] if paired else tr("teléfono")
            self.status_message = trf("✓ Alarma acústica enviada a '{target_name}'. Sonando...", target_name=target_name) if ok else tr("No hay smartphone vinculado o en línea.")
            return

        if action_key == "action:kc_fix_firewall":
            cmd = ["bash", "-c", "sudo ufw allow 1714:1764/udp && sudo ufw allow 1714:1764/tcp && sudo ufw reload"]
            self._prompt_command_modal(
                tr("DESBLOQUEAR PUERTOS DE CORTAFUEGOS"),
                tr("Se añadirán reglas a UFW (puertos 1714-1764 TCP/UDP) para KDE Connect."),
                tr("¿Deseas autorizar la apertura de puertos en el cortafuegos?"),
                cmd,
            )
            return

        if action_key == "action:kc_refresh_devices":
            self.status_message = tr("Buscando teléfonos KDE Connect en tu WiFi...")
            self.render()
            self.sys_mgr.start_or_restart_kdeconnect()
            self._refresh_all_state()
            devs = self.sys_mgr.get_kdeconnect_devices(force=True)
            self.section_items["kdeconnect"] = self._build_kdeconnect_section_items()
            if not devs and not self.sys_mgr.is_kdeconnect_firewall_allowed():
                self.status_message = "Cortafuegos UFW bloqueando puertos 1714-1764. Usa 'Abrir Puertos' arriba."
            elif devs:
                self.status_message = trf("✓ {len} dispositivo(s) detectado(s).", len=len(devs))
            else:
                self.status_message = tr("No se detectaron dispositivos. Abre KDE Connect en tu teléfono.")
            return

    def save_all(self) -> None:
        """Aplica todos los cambios de tema, fondo, dotfiles, suites, paquetes y webapps."""
        self.status_message = tr("Aplicando cambios...")
        self.render()

        # 1. Tema activo
        if self.settings.get("active_theme") != self.saved_settings.get("active_theme"):
            new_theme = str(self.settings.get("active_theme", "lizarbe"))
            self.status_message = trf("Activando tema '{new_theme}'...", new_theme=new_theme)
            self.render()
            self.theme_engine.set_theme(new_theme)

        # 2. Fondo de pantalla
        if self.settings.get("wallpaper") != self.saved_settings.get("wallpaper"):
            new_wp = str(self.settings.get("wallpaper", ""))
            sel_t = str(self.settings.get("active_theme", self.theme_engine.current_theme))
            if new_wp:
                self.theme_engine.set_wallpaper(new_wp, theme_name=sel_t)

        # 3. Dotfiles y configuración de usuario
        if self.settings.get("icons_lizarbe") != self.saved_settings.get("icons_lizarbe"):
            self.sys_mgr.apply_icons_user(bool(self.settings.get("icons_lizarbe")))
        if self.settings.get("gtk_darky") != self.saved_settings.get("gtk_darky"):
            self.sys_mgr.apply_gtk_darky_user(bool(self.settings.get("gtk_darky")))
        if self.settings.get("fastfetch") != self.saved_settings.get("fastfetch"):
            self.sys_mgr.apply_fastfetch_user(bool(self.settings.get("fastfetch")))
        if self.settings.get("starship") != self.saved_settings.get("starship"):
            self.sys_mgr.apply_starship_user(bool(self.settings.get("starship")))
        if self.settings.get("branding") != self.saved_settings.get("branding"):
            self.sys_mgr.apply_branding_user(bool(self.settings.get("branding")))

        # 4. Webapps individuales
        for w_id, _, _, _ in self.sys_mgr.WEBAPPS_SPEC:
            w_key = f"webapp:{w_id}"
            if self.settings.get(w_key) != self.saved_settings.get(w_key):
                self.sys_mgr.install_or_remove_webapp(w_id, install=bool(self.settings.get(w_key)))

        # 5. Suites modificadas
        suites_to_install: List[str] = []
        suites_to_remove: List[str] = []
        for s_id, _, _, _, _ in self.sys_mgr.SUITES_SPEC:
            s_key = f"suite:{s_id}"
            if self.settings.get(s_key) != self.saved_settings.get(s_key):
                if self.settings.get(s_key):
                    suites_to_install.append(f"--core-only" if s_id == "core" else f"--{s_id}")
                else:
                    suites_to_remove.append(f"--theme-only" if s_id == "core" else f"--{s_id}")

        if suites_to_install:
            self._run_interactive_command(
                trf("Instalando Suites ({names})", names=', '.join(suites_to_install)),
                ["bash", str(self.sys_mgr.repo_dir / "install.sh")] + suites_to_install,
            )

        if suites_to_remove:
            self._run_interactive_command(
                trf("Desinstalando Suites ({names})", names=', '.join(suites_to_remove)),
                ["bash", str(self.sys_mgr.repo_dir / "uninstall.sh"), "--yes"] + suites_to_remove,
            )

        # 6. Paquetes individuales modificados
        pkgs_to_install: List[str] = []
        pkgs_to_remove: List[str] = []
        for _, pkg, _, _ in self.sys_mgr.UTIL_PKGS + self.sys_mgr.CREATIVE_PKGS + self.sys_mgr.WORK_PKGS:
            p_key = f"pkg:{pkg}"
            if self.settings.get(p_key) != self.saved_settings.get(p_key):
                if self.settings.get(p_key):
                    pkgs_to_install.append(pkg)
                else:
                    pkgs_to_remove.append(pkg)

        if pkgs_to_install:
            helper = ["yay", "-S", "--needed", "--noconfirm"] if shutil.which("yay") else ["sudo", "pacman", "-S", "--needed", "--noconfirm"]
            self._run_interactive_command(
                trf("Instalando paquetes ({n})", n=len(pkgs_to_install)),
                helper + pkgs_to_install,
            )

        if pkgs_to_remove:
            rm_cmd = ["omarchy-pkg-drop"] if shutil.which("omarchy-pkg-drop") else ["sudo", "pacman", "-Rns", "--noconfirm"]
            self._run_interactive_command(
                trf("Desinstalando paquetes ({n})", n=len(pkgs_to_remove)),
                rm_cmd + pkgs_to_remove,
            )

        self._refresh_all_state()
        self.status_message = tr("✓ Cambios aplicados correctamente.")

    def cancel_changes(self) -> None:
        self.settings = dict(self.saved_settings)
        self.running = False

    def reset_to_defaults(self) -> None:
        self.modal_state = "confirm_reset"
        self.modal_selected_idx = 1

    # ==========================
    # MANEJO DE ENTRADA Y RATÓN
    # ==========================

    def _move_content_selection(self, delta: int) -> None:
        sec_id = self.SECTIONS[self.current_section_idx][1]
        items = self.section_items.get(sec_id, [])
        if not items:
            return
        idx = self.selected_item_idx + delta
        max_steps = len(items) + 1
        steps = 0
        while 0 <= idx < len(items) and items[idx].item_type == "header" and steps < max_steps:
            idx += (1 if delta >= 0 else -1)
            steps += 1
        if idx < 0:
            self.selected_item_idx = 0
        elif idx >= len(items):
            if abs(delta) > 1:
                last_valid = len(items) - 1
                while last_valid >= 0 and items[last_valid].item_type == "header":
                    last_valid -= 1
                self.selected_item_idx = max(0, last_valid)
            else:
                self.active_pane = "buttons"
                self.selected_button_idx = 2
        else:
            self.selected_item_idx = idx

    def _adjust_current_item(self, delta: int) -> None:
        sec_id = self.SECTIONS[self.current_section_idx][1]
        items = self.section_items.get(sec_id, [])
        if not items or self.selected_item_idx >= len(items):
            return
        item = items[self.selected_item_idx]

        if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
            if item.key != "action:install_kdeconnect_now":
                self.status_message = tr("KDE Connect aún no está instalado en el equipo. Pulsa ' Instalar' abajo para comenzar.")
                return

        if item.item_type == "select" and item.options:
            cur = str(self._get_item_value(item))
            try:
                idx = item.options.index(cur)
            except ValueError:
                idx = 0
            next_idx = (idx + delta) % len(item.options)
            self._set_item_value(item.key, item.options[next_idx])
        elif item.item_type == "toggle":
            cur = bool(self._get_item_value(item))
            self._set_item_value(item.key, not cur)

    def _activate_current_item(self) -> None:
        sec_id = self.SECTIONS[self.current_section_idx][1]
        items = self.section_items.get(sec_id, [])
        if not items or self.selected_item_idx >= len(items):
            return
        item = items[self.selected_item_idx]

        if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
            if item.key not in ("action:install_kdeconnect_now", "action:kc_how_to_use"):
                self.status_message = tr("KDE Connect aún no está instalado en el equipo. Pulsa ' Instalar' abajo para comenzar.")
                return

        if item.item_type == "toggle":
            self._adjust_current_item(delta=1)
        elif item.item_type == "select":
            row_y = 5 + (self.selected_item_idx - self.content_scroll_offset) * 3
            self._open_dropdown_for_item(item, anchor_y=row_y, anchor_x=45)
        elif item.item_type in ("action", "theme_card", "info_badge", "app_card"):
            self._execute_action(item.key)

    def handle_input(self, fd: Any) -> None:
        if isinstance(fd, (bytes, bytearray)):
            ch = bytes(fd)
        else:
            r, _, _ = select.select([fd], [], [], 0.05)
            if not r:
                return
            ch = os.read(fd, 4096)
        if not ch:
            return

        mouse_matches = list(re.finditer(b"\x1b\\[<(\\d+);(\\d+);(\\d+)([Mm])", ch))
        if mouse_matches:
            for m in mouse_matches:
                btn = int(m.group(1))
                x = int(m.group(2))
                y = int(m.group(3))
                act = m.group(4)
                self._handle_mouse_event(btn, x, y, act)
            return

        self.hover_sidebar_idx = None
        self.hover_item_idx = None
        self.hover_subcontrol = None
        self.hover_button_key = None
        self.hover_dropdown_idx = None
        self.hover_context_idx = None

        # 0. Menú contextual
        if self.context_menu_open and not self.modal_state:
            if ch in (b"\x1b", b"q", b"Q") and len(ch) == 1:
                self.context_menu_open = False
                return
            if ch in (b"\x1b[A", b"k", b"K"):
                self.context_menu_idx = max(0, self.context_menu_idx - 1)
                return
            if ch in (b"\x1b[B", b"j", b"J"):
                self.context_menu_idx = min(len(self.context_menu_items) - 1, self.context_menu_idx + 1)
                return
            if ch in (b"\r", b"\n", b" "):
                if 0 <= self.context_menu_idx < len(self.context_menu_items):
                    self._execute_context_action(self.context_menu_items[self.context_menu_idx][0])
                else:
                    self.context_menu_open = False
                return
            self.context_menu_open = False
            return

        # 1. Dropdown abierto
        if self.dropdown_open and not self.modal_state:
            if ch in (b"\x1b", b"q", b"Q") and len(ch) == 1:
                self.dropdown_open = False
                return
            if ch in (b"\x1b[A", b"k", b"K"):
                self.dropdown_idx = max(0, self.dropdown_idx - 1)
                return
            if ch in (b"\x1b[B", b"j", b"J"):
                self.dropdown_idx = min(len(self.dropdown_options) - 1, self.dropdown_idx + 1)
                return
            if ch in (b"\x1b[5~",):  # Page Up
                self.dropdown_idx = max(0, self.dropdown_idx - 5)
                return
            if ch in (b"\x1b[6~",):  # Page Down
                self.dropdown_idx = min(len(self.dropdown_options) - 1, self.dropdown_idx + 5)
                return
            if ch in (b"\x1b[H", b"\x1b[1~"):  # Home
                self.dropdown_idx = 0
                return
            if ch in (b"\x1b[F", b"\x1b[4~"):  # End
                self.dropdown_idx = max(0, len(self.dropdown_options) - 1)
                return
            if ch in (b"\r", b"\n", b" "):
                if self.dropdown_item and 0 <= self.dropdown_idx < len(self.dropdown_options):
                    chosen = self.dropdown_options[self.dropdown_idx]
                    target_key = self.dropdown_item.key
                    self.dropdown_open = False
                    self._set_item_value(target_key, chosen)
                self.dropdown_open = False
                return
            return

        # 2. Modal de guía de KDE Connect
        if self.modal_state == "kdeconnect_guide":
            max_scroll = max(0, len(self._guide_lines) - self._guide_content_h)
            if (ch == b"\x1b" and len(ch) == 1) or ch in (b"q", b"Q", b"\r", b"\n", b" "):
                self.modal_state = None
                return
            if ch in (b"\x1b[A", b"k", b"K"):
                self.guide_scroll_offset = max(0, self.guide_scroll_offset - 1)
                return
            if ch in (b"\x1b[B", b"j", b"J"):
                self.guide_scroll_offset = min(max_scroll, self.guide_scroll_offset + 1)
                return
            if ch in (b"\x1b[5~", b"\x02"):  # PageUp, Ctrl+B
                self.guide_scroll_offset = max(0, self.guide_scroll_offset - max(1, self._guide_content_h - 2))
                return
            if ch in (b"\x1b[6~", b"\x06"):  # PageDown, Ctrl+F
                self.guide_scroll_offset = min(max_scroll, self.guide_scroll_offset + max(1, self._guide_content_h - 2))
                return
            if ch in (b"\x1b[H", b"\x1b[1~"):  # Home
                self.guide_scroll_offset = 0
                return
            if ch in (b"\x1b[F", b"\x1b[4~"):  # End
                self.guide_scroll_offset = max_scroll
                return
            return

        # 3. Modal de confirmación
        if self.modal_state:
            max_idx = 2 if self.modal_state == "confirm_section_change" else 1
            if ch == b"\x1b" and len(ch) == 1:
                self.modal_state = None
                self.pending_section_idx = None
                return
            if ch in (b"\x1b[D", b"\x1b[Z", b"h", b"H"):
                self.modal_selected_idx = max(0, self.modal_selected_idx - 1)
                return
            if ch in (b"\x1b[C", b"\t", b"l", b"L"):
                self.modal_selected_idx = min(max_idx, self.modal_selected_idx + 1)
                return
            if ch in (b"\r", b"\n", b" "):
                self._execute_modal_choice(self.modal_selected_idx)
                return
            return

        # Salir o regresar con Esc (si está en contenido o botones, regresa a sidebar; si está en sidebar, sale)
        if ch == b"\x1b" and len(ch) == 1:
            if self.active_pane != "sidebar":
                self.active_pane = "sidebar"
                self.status_message = tr("Foco en el panel izquierdo (Barra lateral).")
                return
            self.running = False
            return

        if ch in (b"q", b"Q") and len(ch) == 1:
            self.running = False
            return

        # Atajo dedicado para volver al panel izquierdo (barra lateral):
        # 'b', 'B', Backspace (\x7f, \x08), Ctrl+Left (\x1b[1;5D), Alt+Left (\x1b[1;3D)
        if ch in (b"b", b"B", b"\x7f", b"\x08", b"\x1b[1;5D", b"\x1b[1;3D"):
            self.active_pane = "sidebar"
            self.status_message = tr("Foco en el panel izquierdo (Barra lateral).")
            return

        # Menú contextual con tecla m / M o tecla Menú (\x1b[29~)
        if ch in (b"m", b"M", b"\x1b[29~") and not self.modal_state and not self.dropdown_open:
            self._open_context_menu_for_current_selection()
            return

        # Atajos rápidos físicos directos (a/s/g: Aplicar/Guardar, c: Cancelar, r: Restablecer)
        if ch in (b"a", b"A", b"s", b"S", b"g", b"G"):
            self.save_all()
            return
        if ch in (b"c", b"C"):
            self.cancel_changes()
            return
        if ch in (b"r", b"R"):
            self.reset_to_defaults()
            return

        # Atajos numéricos 1-9 directos en la barra lateral
        if self.active_pane == "sidebar" and ch in (b"1", b"2", b"3", b"4", b"5", b"6", b"7", b"8", b"9"):
            target_s = int(ch) - 1
            if 0 <= target_s < len(self.SECTIONS):
                self._request_section_change(target_s, focus_content=False)
            return

        # Cambiar foco con Tab (avance) y Shift+Tab (retroceso)
        if ch == b"\t":
            if self.active_pane == "sidebar":
                self.active_pane = "content"
            elif self.active_pane == "content":
                self.active_pane = "buttons"
            else:
                self.active_pane = "sidebar"
            return

        if ch == b"\x1b[Z":  # Shift+Tab: ciclo inverso
            if self.active_pane == "sidebar":
                self.active_pane = "buttons"
            elif self.active_pane == "buttons":
                self.active_pane = "content"
            else:
                self.active_pane = "sidebar"
            return

        # Page Up (\x1b[5~) y Page Down (\x1b[6~)
        if ch == b"\x1b[5~":  # Page Up
            if self.active_pane == "sidebar":
                self._request_section_change(max(0, self.current_section_idx - 5), focus_content=False)
            elif self.active_pane == "content":
                self._move_content_selection(-5)
            return

        if ch == b"\x1b[6~":  # Page Down
            if self.active_pane == "sidebar":
                self._request_section_change(min(len(self.SECTIONS) - 1, self.current_section_idx + 5), focus_content=False)
            elif self.active_pane == "content":
                self._move_content_selection(5)
            return

        # Home (\x1b[H / \x1b[1~) y End (\x1b[F / \x1b[4~)
        if ch in (b"\x1b[H", b"\x1b[1~"):
            if self.active_pane == "sidebar":
                self._request_section_change(0, focus_content=False)
            elif self.active_pane == "content":
                self.selected_item_idx = 0
            return

        if ch in (b"\x1b[F", b"\x1b[4~"):
            if self.active_pane == "sidebar":
                self._request_section_change(len(self.SECTIONS) - 1, focus_content=False)
            elif self.active_pane == "content":
                sec_id = self.SECTIONS[self.current_section_idx][1]
                items = self.section_items.get(sec_id, [])
                if items:
                    self.selected_item_idx = len(items) - 1
            return

        # Navegación izquierda (Flecha Izquierda / h)
        if ch in (b"\x1b[D", b"h"):
            if self.active_pane == "buttons":
                if ch == b"h" or self.selected_button_idx == 0:
                    self.active_pane = "sidebar"
                else:
                    self.selected_button_idx = max(0, self.selected_button_idx - 1)
            elif self.active_pane == "content":
                if ch == b"h":
                    self.active_pane = "sidebar"
                else:
                    sec_id = self.SECTIONS[self.current_section_idx][1]
                    items = self.section_items.get(sec_id, [])
                    if items and 0 <= self.selected_item_idx < len(items):
                        item = items[self.selected_item_idx]
                        if item.item_type in ("select", "slider", "stepper"):
                            self._adjust_current_item(delta=-1)
                        else:
                            self.active_pane = "sidebar"
                    else:
                        self.active_pane = "sidebar"
            else:
                self.active_pane = "sidebar"
            return

        # Navegación derecha (Flecha Derecha / l)
        if ch in (b"\x1b[C", b"l"):
            if self.active_pane == "buttons":
                self.selected_button_idx = min(2, self.selected_button_idx + 1)
            elif self.active_pane == "content":
                self._adjust_current_item(delta=1)
            else:
                self.active_pane = "content"
            return

        # Ajuste de valores con + / = y - / _
        if ch in (b"+", b"="):
            if self.active_pane == "content":
                self._adjust_current_item(delta=1)
            return

        if ch in (b"-", b"_"):
            if self.active_pane == "content":
                self._adjust_current_item(delta=-1)
            return

        # Navegación vertical arriba (Flecha Arriba / k)
        if ch in (b"\x1b[A", b"k"):
            if self.active_pane == "buttons":
                self.active_pane = "content"
            elif self.active_pane == "sidebar":
                self._request_section_change(self.current_section_idx - 1, focus_content=False)
            else:
                self._move_content_selection(-1)
            return

        # Navegación vertical abajo (Flecha Abajo / j)
        if ch in (b"\x1b[B", b"j"):
            if self.active_pane == "sidebar":
                self._request_section_change(self.current_section_idx + 1, focus_content=False)
            elif self.active_pane == "content":
                self._move_content_selection(1)
            return

        # Espacio para conmutar directamente (toggle / activar)
        if ch == b" ":
            if self.active_pane == "sidebar":
                self.active_pane = "content"
            elif self.active_pane == "buttons":
                if self.selected_button_idx == 0:
                    self.reset_to_defaults()
                elif self.selected_button_idx == 1:
                    self.cancel_changes()
                elif self.selected_button_idx == 2:
                    self.save_all()
            else:
                self._activate_current_item()
            return

        # Enter para activar/abrir/confirmar
        if ch in (b"\r", b"\n"):
            if self.active_pane == "sidebar":
                self.active_pane = "content"
            elif self.active_pane == "buttons":
                if self.selected_button_idx == 0:
                    self.reset_to_defaults()
                elif self.selected_button_idx == 1:
                    self.cancel_changes()
                elif self.selected_button_idx == 2:
                    self.save_all()
            else:
                self._activate_current_item()
            return

    def _handle_mouse_event(self, btn: int, x: int, y: int, act: bytes) -> None:
        cols, rows = shutil.get_terminal_size((84, 42))
        sidebar_w = self._get_sidebar_width(cols)

        # 0. Menú contextual
        if self.context_menu_open and not self.modal_state:
            cy1, cy2, cx1, cx2 = self._context_box_bounds
            if act == b"M" and btn == 35:
                if cy1 <= y <= cy2 and cx1 <= x <= cx2 and y in self._context_row_map:
                    self.hover_context_idx = self._context_row_map[y]
                    self.context_menu_idx = self.hover_context_idx
                else:
                    self.hover_context_idx = None
                return
            if act == b"M" and btn in (64, 65):
                if btn == 64:
                    self.context_menu_idx = max(0, self.context_menu_idx - 1)
                else:
                    self.context_menu_idx = min(len(self.context_menu_items) - 1, self.context_menu_idx + 1)
                return
            if act == b"M" and btn == 0:
                if cy1 <= y <= cy2 and cx1 <= x <= cx2 and y in self._context_row_map:
                    c_idx = self._context_row_map[y]
                    if 0 <= c_idx < len(self.context_menu_items):
                        self._execute_context_action(self.context_menu_items[c_idx][0])
                        return
                self.context_menu_open = False
                return
            if act == b"M" and btn == 2:
                self._open_context_menu(x, y, sidebar_w)
                return
            return

        # 1. Dropdown
        if self.dropdown_open and not self.modal_state:
            dy1, dy2, dx1, dx2 = self._dropdown_box_bounds
            if act == b"M" and btn == 35:
                if dy1 <= y <= dy2 and dx1 <= x <= dx2 and y in self._dropdown_row_map:
                    self.hover_dropdown_idx = self._dropdown_row_map[y]
                    self.dropdown_idx = self.hover_dropdown_idx
                else:
                    self.hover_dropdown_idx = None
                return
            if act == b"M" and btn in (64, 65):
                if btn == 64:
                    self.dropdown_idx = max(0, self.dropdown_idx - 1)
                else:
                    self.dropdown_idx = min(len(self.dropdown_options) - 1, self.dropdown_idx + 1)
                return
            if act == b"M" and btn == 0:
                if dy1 <= y <= dy2 and dx1 <= x <= dx2 and y in self._dropdown_row_map:
                    opt_idx = self._dropdown_row_map[y]
                    if self.dropdown_item and 0 <= opt_idx < len(self.dropdown_options):
                        chosen = self.dropdown_options[opt_idx]
                        target_key = self.dropdown_item.key
                        self.dropdown_open = False
                        self._set_item_value(target_key, chosen)
                self.dropdown_open = False
                return
            if act == b"M" and btn == 2:
                self.dropdown_open = False
                self._open_context_menu(x, y, sidebar_w)
                return
            return

        # 2. Modal activo
        if self.modal_state == "kdeconnect_guide":
            max_scroll = max(0, len(self._guide_lines) - self._guide_content_h)
            if btn == 64:  # Rueda arriba
                self.guide_scroll_offset = max(0, self.guide_scroll_offset - 2)
                return
            if btn == 65:  # Rueda abajo
                self.guide_scroll_offset = min(max_scroll, self.guide_scroll_offset + 2)
                return
            if act == b"M" and btn == 35:  # Hover
                m_ymin, m_ymax = self._modal_button_row_range
                self.hover_modal_btn_idx = None
                if m_ymin <= y <= m_ymax:
                    for b_idx, (bx_min, bx_max) in self._modal_button_click_map.items():
                        if bx_min <= x <= bx_max:
                            self.hover_modal_btn_idx = b_idx
                            return
                return
            if act == b"M" and btn == 0:  # Clic izquierdo
                m_ymin, m_ymax = self._modal_button_row_range
                if m_ymin <= y <= m_ymax:
                    for b_idx, (bx_min, bx_max) in self._modal_button_click_map.items():
                        if bx_min <= x <= bx_max:
                            self.modal_state = None
                            return
                b_ymin, b_ymax, b_xmin, b_xmax = getattr(self, "_guide_box_bounds", (0, 0, 0, 0))
                if x < b_xmin or x > b_xmax or y < b_ymin or y > b_ymax:
                    self.modal_state = None
                    return
                return
            if act == b"M" and btn == 2:  # Clic derecho -> cerrar
                self.modal_state = None
                return
            return

        if self.modal_state:
            if act == b"M" and btn == 35:
                m_ymin, m_ymax = self._modal_button_row_range
                self.hover_modal_btn_idx = None
                if m_ymin <= y <= m_ymax:
                    for b_idx, (bx_min, bx_max) in self._modal_button_click_map.items():
                        if bx_min <= x <= bx_max:
                            self.modal_selected_idx = b_idx
                            self.hover_modal_btn_idx = b_idx
                            return
                return
            if act == b"M" and btn == 0:
                m_ymin, m_ymax = self._modal_button_row_range
                if m_ymin <= y <= m_ymax:
                    for b_idx, (bx_min, bx_max) in self._modal_button_click_map.items():
                        if bx_min <= x <= bx_max:
                            self.modal_selected_idx = b_idx
                            self._execute_modal_choice(b_idx)
                            return
            return

        if act == b"M":
            # Clic derecho -> Menú contextual
            if btn == 2:
                self._open_context_menu(x, y, sidebar_w)
                return

            # Hover (btn == 35)
            if btn == 35:
                btn_y_min, btn_y_max = self._button_row_range
                if x <= sidebar_w:
                    sec_idx = self._sidebar_click_map.get(y)
                    self.hover_sidebar_idx = sec_idx
                    self.hover_item_idx = None
                    self.hover_subcontrol = None
                    self.hover_button_key = None
                    if sec_idx is not None and 0 <= sec_idx < len(self.SECTIONS):
                        _, _, _, s_title, s_desc = self.SECTIONS[sec_idx]
                        self.status_message = f"{s_title}: {s_desc}"
                    return

                if x > sidebar_w + 1 and btn_y_min <= y <= btn_y_max:
                    self.hover_sidebar_idx = None
                    self.hover_item_idx = None
                    self.hover_subcontrol = None
                    hovered_btn = None
                    btn_idx_map = {"reset": 0, "cancel": 1, "save": 2}
                    for b_key, (bx_min, bx_max) in self._button_click_map.items():
                        if bx_min <= x <= bx_max:
                            hovered_btn = b_key
                            self.active_pane = "buttons"
                            self.selected_button_idx = btn_idx_map[b_key]
                            break
                    self.hover_button_key = hovered_btn
                    return

                if x > sidebar_w + 1:
                    info = self._content_click_map.get(y)
                    if info:
                        self.hover_sidebar_idx = None
                        self.hover_button_key = None
                        self.hover_item_idx = info["item_idx"]
                        self.active_pane = "content"
                        self.selected_item_idx = info["item_idx"]
                        item = info["item"]
                        self.status_message = f"{item.name}: {item.desc}"
                        c_start, c_end = info["control_range"]
                        self.hover_subcontrol = "control" if (c_start <= x <= c_end) else None
                        return

                self.hover_sidebar_idx = None
                self.hover_item_idx = None
                self.hover_subcontrol = None
                self.hover_button_key = None
                return

            # Clic izquierdo (btn == 0)
            if btn == 0:
                if y == 1 and x >= cols - 15:
                    self.running = False
                    return

                btn_y_min, btn_y_max = self._button_row_range
                if x > sidebar_w + 1 and btn_y_min <= y <= btn_y_max:
                    reset_r = self._button_click_map.get("reset")
                    cancel_r = self._button_click_map.get("cancel")
                    save_r = self._button_click_map.get("save")

                    if reset_r and reset_r[0] <= x <= reset_r[1]:
                        self.active_pane = "buttons"
                        self.selected_button_idx = 0
                        self.reset_to_defaults()
                        return
                    elif cancel_r and cancel_r[0] <= x <= cancel_r[1]:
                        self.active_pane = "buttons"
                        self.selected_button_idx = 1
                        self.cancel_changes()
                        return
                    elif save_r and save_r[0] <= x <= save_r[1]:
                        self.active_pane = "buttons"
                        self.selected_button_idx = 2
                        self.save_all()
                        return

                if y == rows:
                    if x > cols - 15:
                        self.running = False
                    elif x <= 16:
                        if self.active_pane == "sidebar":
                            self.active_pane = "content"
                        elif self.active_pane == "content":
                            self.active_pane = "buttons"
                        else:
                            self.active_pane = "sidebar"
                    return

                if x <= sidebar_w:
                    sec_idx = self._sidebar_click_map.get(y)
                    if sec_idx is not None:
                        self._request_section_change(sec_idx, focus_content=True)
                    return

                if x > sidebar_w + 1:
                    info = self._content_click_map.get(y)
                    if info:
                        self.active_pane = "content"
                        self.selected_item_idx = info["item_idx"]
                        item = info["item"]
                        sec_id = self.SECTIONS[self.current_section_idx][1]

                        if sec_id == "kdeconnect" and not self.sys_mgr.is_kdeconnect_installed():
                            if item.key in ("action:install_kdeconnect_now", "action:kc_how_to_use"):
                                self._activate_current_item()
                            else:
                                self.status_message = tr("KDE Connect aún no está instalado en el equipo. Pulsa ' Instalar' abajo para comenzar.")
                            return

                        if item.item_type == "toggle":
                            self._activate_current_item()
                        elif item.item_type == "select":
                            c_start, _ = info["control_range"]
                            self._open_dropdown_for_item(item, anchor_y=info.get("row_y", y), anchor_x=c_start)
                        elif item.item_type in ("action", "info_badge"):
                            c_start, c_end = info["control_range"]
                            if c_start <= x <= c_end:
                                self._activate_current_item()
                        elif item.item_type in ("theme_card", "app_card"):
                            self._activate_current_item()

            # Rueda arriba (btn == 64)
            elif btn == 64:
                if x <= sidebar_w:
                    self._request_section_change(self.current_section_idx - 1, focus_content=False)
                else:
                    self._move_content_selection(-1)

            # Rueda abajo (btn == 65)
            elif btn == 65:
                if x <= sidebar_w:
                    self._request_section_change(self.current_section_idx + 1, focus_content=False)
                else:
                    self._move_content_selection(1)
