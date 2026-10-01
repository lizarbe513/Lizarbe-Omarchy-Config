#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

show_help() {
    cat << HELP
Uso: ./uninstall.sh [OPCIONES]

Desinstalador para Omarchy - Setup Lizarbe (Tema y Suites de Software).

Opciones:
  --all           Desinstala todo (tema, configuraciones y aplicaciones)
  --theme-only    Desinstala únicamente el tema Lizarbe y restaura el tema oficial
  --apps-only     Desinstala únicamente las suites de software (2D, 3D, Dev, Ofimática, Multimedia, Webapps)
  --2d            Desinstala únicamente la Suite 2D
  --3d            Desinstala únicamente la Suite 3D
  --dev           Desinstala únicamente la Suite de Desarrollo
  --office        Desinstala únicamente la Suite de Ofimática
  --multimedia    Desinstala únicamente la Suite Multimedia
  --webapps       Remueve únicamente las Webapps
  -h, --help      Muestra esta ayuda

Si se ejecuta sin opciones, se abrirá el asistente interactivo.
HELP
}

# Funciones de desinstalación de paquetes
remove_pkg_file() {
    local pkg_file="$1"
    local suite_name="$2"

    if [[ ! -f "$pkg_file" ]]; then return 0; fi

    local pkgs=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="$(echo "$line" | sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        if [[ -n "$line" && "$line" != "git" && "$line" != "bash" && "$line" != "sudo" ]]; then
            pkgs+=("$line")
        fi
    done < "$pkg_file"

    local to_remove=()
    for pkg in "${pkgs[@]}"; do
        if pacman -Qq "$pkg" &>/dev/null; then
            to_remove+=("$pkg")
        fi
    done

    if [[ ${#to_remove[@]} -gt 0 ]]; then
        info "Desinstalando paquetes de ${suite_name} (${#to_remove[@]} encontrados)..."
        if command -v omarchy-pkg-drop &>/dev/null; then
            omarchy-pkg-drop "${to_remove[@]}" || sudo pacman -Rns --noconfirm "${to_remove[@]}" || true
        else
            sudo pacman -Rns --noconfirm "${to_remove[@]}" || true
        fi
        success "${suite_name} desinstalada."
    else
        info "No hay paquetes para desinstalar de ${suite_name}."
    fi
}

uninstall_theme() {
    info "=== Revertiendo Tema y Personalizaciones Visuales en la Raíz y Usuario ==="
    ensure_sudo

    # 1. Cambiar tema activo de Omarchy si está en lizarbe
    if command -v omarchy &>/dev/null; then
        local current_theme
        current_theme=$(omarchy theme current 2>/dev/null || echo "")
        if [[ "$current_theme" =~ [Ll]izarbe ]]; then
            info "Cambiando tema activo a tokyo-night..."
            omarchy theme set tokyo-night || omarchy theme set catppuccin || true
        fi
    fi

    # 2. Eliminar temas Lizarbe de omarchy (raíz y usuario)
    if [[ -d "/usr/share/omarchy/themes/lizarbe" || -d "/usr/share/omarchy/themes/lizarbe-light" ]]; then
        info "Eliminando temas Lizarbe de /usr/share/omarchy/themes/..."
        $SUDO rm -rf "/usr/share/omarchy/themes/lizarbe" "/usr/share/omarchy/themes/lizarbe-light"
    fi
    rm -rf "$HOME/.config/omarchy/themes/lizarbe" "$HOME/.config/omarchy/themes/lizarbe-light"

    # 3. Eliminar branding propio (raíz y usuario)
    info "Limpiando branding personalizado..."
    $SUDO rm -f "/usr/share/omarchy/branding/about.txt" "/usr/share/omarchy/branding/logo.png" "/usr/share/omarchy/branding/screensaver.txt" 2>/dev/null || true
    $SUDO rm -f "/etc/omarchy/branding/about.txt" "/etc/omarchy/branding/logo.png" "/etc/omarchy/branding/screensaver.txt" 2>/dev/null || true
    rm -f "$HOME/.config/omarchy/branding/about.txt" "$HOME/.config/omarchy/branding/logo.png" "$HOME/.config/omarchy/branding/screensaver.txt"

    # 4. Limpiar Fastfetch y Starship (raíz y usuario)
    info "Limpiando configuración de Fastfetch y Starship..."
    $SUDO rm -rf "/etc/xdg/fastfetch" 2>/dev/null || true
    $SUDO rm -f "/etc/starship.toml" 2>/dev/null || true
    if [[ -d "$HOME/.config/fastfetch" ]]; then
        rm -f "$HOME/.config/fastfetch/logo.txt"
    fi

    # 5. Eliminar tema de iconos Lizarbe-Red (raíz y usuario)
    if [[ -d "/usr/share/icons/Lizarbe-Red" ]]; then
        info "Eliminando pack de iconos Lizarbe-Red de /usr/share/icons/..."
        $SUDO rm -rf "/usr/share/icons/Lizarbe-Red"
    fi
    if [[ -d "$HOME/.local/share/icons/Lizarbe-Red" ]]; then
        rm -rf "$HOME/.local/share/icons/Lizarbe-Red"
        rm -f "$HOME/.icons/Lizarbe-Red"
    fi

    # 6. Eliminar tema GTK Darky (raíz y usuario)
    if [[ -d "/usr/share/themes/Darky" ]]; then
        info "Eliminando tema GTK Darky de /usr/share/themes/..."
        $SUDO rm -rf "/usr/share/themes/Darky"
    fi
    if [[ -d "$HOME/.local/share/themes/Darky" ]]; then
        rm -rf "$HOME/.local/share/themes/Darky"
    fi
    for f in "$HOME/.config/gtk-4.0/gtk.css" "$HOME/.config/gtk-4.0/gtk-dark.css" "$HOME/.config/gtk-4.0/assets"; do
        if [[ -L "$f" && "$(readlink -f "$f" 2>/dev/null)" == *Darky* ]]; then
            rm -f "$f"
        fi
    done

    # 7. Eliminar binarios de la aplicación Lizarbe, entrada .desktop y hooks
    info "Eliminando binarios, entrada de aplicaciones y hooks de Lizarbe..."
    $SUDO rm -f "/usr/local/bin/lizarbe" "/usr/local/bin/lizarbe-tui" "/usr/local/bin/lizarbe-update" "/usr/local/bin/lizarbe-apply-user" 2>/dev/null || true
    $SUDO rm -f "/usr/share/applications/lizarbe.desktop" 2>/dev/null || true
    $SUDO rm -f "/etc/pacman.d/hooks/00-lizarbe-update.hook" 2>/dev/null || true
    $SUDO rm -f "/etc/skel/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook" 2>/dev/null || true
    rm -f "$HOME/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook" 2>/dev/null || true
    rm -f "$HOME/.local/bin/lizarbe" "$HOME/.local/bin/lizarbe-tui" "$HOME/.local/bin/lizarbe-update" "$HOME/.local/bin/lizarbe-apply-user" 2>/dev/null || true
    rm -f "$HOME/.local/share/applications/lizarbe.desktop" 2>/dev/null || true

    success "Tema Lizarbe revertido y desinstalado exitosamente de la raíz y usuario."
}

uninstall_webapps() {
    info "=== Removiendo Webapps ==="
    if command -v omarchy-webapp-remove &>/dev/null; then
        omarchy-webapp-remove "WhatsApp" >/dev/null 2>&1 || true
        omarchy-webapp-remove "YouTube" >/dev/null 2>&1 || true
    fi
    rm -f "$HOME/.local/share/applications/WhatsApp.desktop"
    rm -f "$HOME/.local/share/applications/YouTube.desktop"
    success "Webapps removidas."
}

# Selección de módulos
UNINSTALL_THEME=false
UNINSTALL_2D=false
UNINSTALL_3D=false
UNINSTALL_DEV=false
UNINSTALL_OFFICE=false
UNINSTALL_MULTIMEDIA=false
UNINSTALL_WEBAPPS=false
AUTO_CONFIRM=false

if [[ $# -gt 0 ]]; then
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --yes|-y)
                AUTO_CONFIRM=true
                shift
                ;;
            --all)
                UNINSTALL_THEME=true
                UNINSTALL_2D=true
                UNINSTALL_3D=true
                UNINSTALL_DEV=true
                UNINSTALL_OFFICE=true
                UNINSTALL_MULTIMEDIA=true
                UNINSTALL_WEBAPPS=true
                shift
                ;;
            --theme-only)
                UNINSTALL_THEME=true
                shift
                ;;
            --apps-only)
                UNINSTALL_2D=true
                UNINSTALL_3D=true
                UNINSTALL_DEV=true
                UNINSTALL_OFFICE=true
                UNINSTALL_MULTIMEDIA=true
                UNINSTALL_WEBAPPS=true
                shift
                ;;
            --2d)
                UNINSTALL_2D=true
                shift
                ;;
            --3d)
                UNINSTALL_3D=true
                shift
                ;;
            --dev)
                UNINSTALL_DEV=true
                shift
                ;;
            --office)
                UNINSTALL_OFFICE=true
                shift
                ;;
            --multimedia)
                UNINSTALL_MULTIMEDIA=true
                shift
                ;;
            --webapps)
                UNINSTALL_WEBAPPS=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Opción desconocida: $1"
                show_help
                exit 1
                ;;
        esac
    done
else
    # Si estamos en una terminal interactiva y lizarbe_tui está disponible, abrir la interfaz TUI en Desinstalación
    if [[ -t 0 && -d "$SCRIPT_DIR/lizarbe_tui" ]] && command -v python3 &>/dev/null; then
        export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
        exec python3 -m lizarbe_tui.cli --section uninstall
    fi

    # Modo interactivo de respaldo en consola
    echo -e "${RED}"
    echo "====================================================="
    echo "       OMARCHY - DESINSTALADOR DE SUITE LIZARBE      "
    echo "====================================================="
    echo -e "${NC}"

    ask_yes_no() {
        local prompt="$1"
        local default="$2"
        local answer
        if [[ "$default" == "Y" ]]; then
            read -rp "$prompt [S/n]: " answer
            answer=${answer:-S}
        else
            read -rp "$prompt [s/N]: " answer
            answer=${answer:-N}
        fi
        if [[ "$answer" =~ ^[SsYy]$ ]]; then
            return 0
        else
            return 1
        fi
    }

    if ask_yes_no "¿Deseas desinstalar el Tema Lizarbe (restaura tema oficial)?" "N"; then
        UNINSTALL_THEME=true
    fi

    if ask_yes_no "¿Deseas desinstalar la Suite Creativa 2D (Krita, LibreSprite, Inkscape, Pinta)?" "N"; then
        UNINSTALL_2D=true
    fi

    if ask_yes_no "¿Deseas desinstalar la Suite Creativa 3D & CAD (Blender, FreeCAD, Blockbench, Godot)?" "N"; then
        UNINSTALL_3D=true
    fi

    if ask_yes_no "¿Deseas desinstalar la Suite de Desarrollo (VS Code, Docker, Lazygit)?" "N"; then
        UNINSTALL_DEV=true
    fi

    if ask_yes_no "¿Deseas desinstalar la Suite Ofimática (ONLYOFFICE, Obsidian, Xournal++)?" "N"; then
        UNINSTALL_OFFICE=true
    fi

    if ask_yes_no "¿Deseas desinstalar la Suite Multimedia (Kdenlive, OBS, Audacity)?" "N"; then
        UNINSTALL_MULTIMEDIA=true
    fi

    if ask_yes_no "¿Deseas remover las Webapps (WhatsApp, YouTube)?" "N"; then
        UNINSTALL_WEBAPPS=true
    fi
fi

# Resumen antes de proceder
echo ""
info "=== Resumen de Componentes a Desinstalar ==="
echo -e "  - Tema Lizarbe:              $([[ "$UNINSTALL_THEME" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Suite Creativa 2D:         $([[ "$UNINSTALL_2D" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Suite Creativa 3D & CAD:   $([[ "$UNINSTALL_3D" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Suite de Desarrollo:       $([[ "$UNINSTALL_DEV" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Suite Ofimática & Notas:   $([[ "$UNINSTALL_OFFICE" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Suite Multimedia:          $([[ "$UNINSTALL_MULTIMEDIA" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo -e "  - Webapps:                   $([[ "$UNINSTALL_WEBAPPS" == true ]] && echo -e "${RED}DESINSTALAR${NC}" || echo -e "${GREEN}CONSERVAR${NC}")"
echo ""

if [[ "$AUTO_CONFIRM" == false ]]; then
    read -rp "¿Confirmas la desinstalación de los elementos seleccionados? [s/N]: " confirm
    if [[ ! "$confirm" =~ ^[SsYy]$ ]]; then
        warn "Operación cancelada por el usuario. No se realizaron cambios."
        exit 0
    fi
fi

[[ "$UNINSTALL_2D" == true ]]         && remove_pkg_file "$SCRIPT_DIR/packages/pkgs-2d.txt" "Suite Creativa 2D"
[[ "$UNINSTALL_3D" == true ]]         && remove_pkg_file "$SCRIPT_DIR/packages/pkgs-3d.txt" "Suite Creativa 3D & CAD"
[[ "$UNINSTALL_DEV" == true ]]        && remove_pkg_file "$SCRIPT_DIR/packages/pkgs-dev.txt" "Suite de Desarrollo"
[[ "$UNINSTALL_OFFICE" == true ]]     && remove_pkg_file "$SCRIPT_DIR/packages/pkgs-office.txt" "Suite Ofimática y Notas"
[[ "$UNINSTALL_MULTIMEDIA" == true ]] && remove_pkg_file "$SCRIPT_DIR/packages/pkgs-multimedia.txt" "Suite Multimedia"
[[ "$UNINSTALL_WEBAPPS" == true ]]    && uninstall_webapps
[[ "$UNINSTALL_THEME" == true ]]      && uninstall_theme

echo ""
success "=============================================================="
success " ¡Desinstalación completada con éxito!"
success "=============================================================="
