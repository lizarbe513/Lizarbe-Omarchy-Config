#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

show_help() {
    cat << HELP
Uso: ./install.sh [OPCIONES]

Instalador modular para Omarchy (Tema Lizarbe + Suite Creativa y de Construcción).

Opciones:
  --all           Instala absolutamente todo (incluye 3D)
  --no-3d         Instala todo excepto la suite 3D (ideal para portátiles / sin GPU dedicada)
  --core-only     Instala únicamente el tema Lizarbe, branding, iconos y dotfiles base
  --2d            Instala únicamente la Suite Creativa 2D
  --3d            Instala únicamente la Suite Creativa 3D & CAD
  --dev           Instala únicamente la Suite de Desarrollo y Código
  --office        Instala únicamente la Suite de Ofimática y Notas
  --multimedia    Instala únicamente la Suite Multimedia
  --webapps       Instala únicamente las Webapps
  -h, --help      Muestra esta ayuda

Si se ejecuta sin opciones, se abrirá el modo interactivo guiado.
HELP
}

# Variables de selección
INSTALL_CORE=false
INSTALL_2D=false
INSTALL_3D=false
INSTALL_DEV=false
INSTALL_OFFICE=false
INSTALL_MULTIMEDIA=false
INSTALL_WEBAPPS=false

if [[ $# -gt 0 ]]; then
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                INSTALL_CORE=true
                INSTALL_2D=true
                INSTALL_3D=true
                INSTALL_DEV=true
                INSTALL_OFFICE=true
                INSTALL_MULTIMEDIA=true
                INSTALL_WEBAPPS=true
                shift
                ;;
            --no-3d)
                INSTALL_CORE=true
                INSTALL_2D=true
                INSTALL_3D=false
                INSTALL_DEV=true
                INSTALL_OFFICE=true
                INSTALL_MULTIMEDIA=true
                INSTALL_WEBAPPS=true
                shift
                ;;
            --core-only)
                INSTALL_CORE=true
                shift
                ;;
            --2d)
                INSTALL_2D=true
                shift
                ;;
            --3d)
                INSTALL_3D=true
                shift
                ;;
            --dev)
                INSTALL_DEV=true
                shift
                ;;
            --office)
                INSTALL_OFFICE=true
                shift
                ;;
            --multimedia)
                INSTALL_MULTIMEDIA=true
                shift
                ;;
            --webapps)
                INSTALL_WEBAPPS=true
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
    # Si estamos en una terminal interactiva y lizarbe_tui está disponible, abrir la interfaz TUI en Suites
    if [[ -t 0 && -d "$SCRIPT_DIR/lizarbe_tui" ]] && command -v python3 &>/dev/null; then
        export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
        exec python3 -m lizarbe_tui.cli --section suites
    fi

    # Modo interactivo de respaldo en consola
    echo -e "${CYAN}"
    echo "====================================================="
    echo "     OMARCHY - SETUP CREATIVO & CONSTRUCCIÓN         "
    echo "               Tema & Suite Lizarbe                  "
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

    if ask_yes_no "¿Instalar Base del Sistema (Tema Lizarbe, Iconos, GTK Darky, Fastfetch)?" "Y"; then
        INSTALL_CORE=true
    fi

    if ask_yes_no "¿Instalar Suite Creativa 2D (Krita, LibreSprite, Inkscape, Pinta)?" "Y"; then
        INSTALL_2D=true
    fi

    echo -e "${YELLOW}Nota 3D: Blender y Godot se benefician de GPU dedicada.${NC}"
    if ask_yes_no "¿Instalar Suite Creativa 3D & CAD (Blender, FreeCAD, Blockbench, Godot)?" "N"; then
        INSTALL_3D=true
    fi

    if ask_yes_no "¿Instalar Suite de Desarrollo (VS Code, Git/Lazygit, Docker/Lazydocker)?" "Y"; then
        INSTALL_DEV=true
    fi

    if ask_yes_no "¿Instalar Suite Ofimática & Notas (ONLYOFFICE, Obsidian, Xournal++)?" "Y"; then
        INSTALL_OFFICE=true
    fi

    if ask_yes_no "¿Instalar Suite Multimedia (Kdenlive, OBS Studio, Audacity)?" "Y"; then
        INSTALL_MULTIMEDIA=true
    fi

    if ask_yes_no "¿Configurar Webapps (WhatsApp, YouTube)?" "Y"; then
        INSTALL_WEBAPPS=true
    fi
fi

# Resumen de instalación
echo ""
info "=== Resumen de Suites a Instalar ==="
echo -e "  - Base & Tema Lizarbe:       $([[ "$INSTALL_CORE" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Suite Creativa 2D:         $([[ "$INSTALL_2D" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Suite Creativa 3D & CAD:   $([[ "$INSTALL_3D" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Suite de Desarrollo:       $([[ "$INSTALL_DEV" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Suite Ofimática & Notas:   $([[ "$INSTALL_OFFICE" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Suite Multimedia:          $([[ "$INSTALL_MULTIMEDIA" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo -e "  - Webapps:                   $([[ "$INSTALL_WEBAPPS" == true ]] && echo -e "${GREEN}SÍ${NC}" || echo -e "${RED}NO${NC}")"
echo ""

# Ejecución secuencial de instaladores
[[ "$INSTALL_CORE" == true ]]       && bash "$SCRIPT_DIR/scripts/install-core.sh"
[[ "$INSTALL_2D" == true ]]         && bash "$SCRIPT_DIR/scripts/install-2d.sh"
[[ "$INSTALL_3D" == true ]]         && bash "$SCRIPT_DIR/scripts/install-3d.sh"
[[ "$INSTALL_DEV" == true ]]        && bash "$SCRIPT_DIR/scripts/install-dev.sh"
[[ "$INSTALL_OFFICE" == true ]]     && bash "$SCRIPT_DIR/scripts/install-office.sh"
[[ "$INSTALL_MULTIMEDIA" == true ]] && bash "$SCRIPT_DIR/scripts/install-multimedia.sh"
[[ "$INSTALL_WEBAPPS" == true ]]    && bash "$SCRIPT_DIR/scripts/install-webapps.sh"

echo ""
success "=============================================================="
success " ¡Instalación completada! Tu entorno Omarchy está listo."
success "=============================================================="
echo ""
echo -e "${YELLOW}[INFO] Cómo aplicar el tema GTK Darky en Omarchy:${NC}"
echo -e "   1. Presiona ${CYAN}Super + Espacio${NC} para abrir el lanzador de aplicaciones."
echo -e "   2. Escribe y abre ${CYAN}nwg-look${NC}."
echo -e "   3. En la pestaña ${CYAN}Widget${NC}, selecciona ${CYAN}Darky${NC}."
echo -e "   4. Haz clic en ${GREEN}Aplicar (Apply)${NC} para guardar los cambios."
echo ""
