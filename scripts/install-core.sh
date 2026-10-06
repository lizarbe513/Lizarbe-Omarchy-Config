#!/usr/bin/env bash
# Base de Lizarbe: el tema, iconos, GTK, branding, fastfetch y starship vienen en
# el paquete lizarbe-tema (repositorio de Lizarbe); aquí solo se instala y se aplica.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/common.sh"

info "=== Instalando la base de Lizarbe ==="
ensure_sudo

install_pkg_file "$REPO_DIR/packages/pkgs-core.txt" "Paquetes Base del Sistema"

info "Instalando el paquete lizarbe-tema..."
$SUDO pacman -S --needed --noconfirm lizarbe-tema

# Enlaces y archivos de tu usuario (iconos, GTK, fastfetch...)
if command -v lizarbe-apply-user &>/dev/null; then
    lizarbe-apply-user || true
fi

if command -v omarchy-default-browser &>/dev/null; then
    info "Estableciendo Zen Browser como navegador predeterminado de Omarchy..."
    omarchy-default-browser zen || true
fi

if command -v omarchy &>/dev/null; then
    info "Aplicando tema Lizarbe con omarchy theme set..."
    omarchy theme set lizarbe || true
fi

success "Base de Lizarbe instalada y aplicada."
echo ""
echo -e "${YELLOW}[INFO] Tema GTK Darky:${NC} queda instalado sin aplicar. Para activarlo abre ${CYAN}nwg-look${NC}, pestaña 'Widget', elige ${CYAN}Darky${NC} y pulsa Apply."
echo ""
