#!/usr/bin/env bash
set -e

# Colores para salida
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Privilegios para operaciones en la raíz del sistema
SUDO=""
if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
fi

ensure_sudo() {
    if [[ $EUID -ne 0 ]]; then
        info "Se requieren privilegios de superusuario para operaciones en la raíz del sistema (/usr/share y /etc)..."
        sudo -v || {
            error "No se pudieron obtener privilegios de superusuario con sudo."
            exit 1
        }
    fi
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Comprobar que yay esté disponible
check_aur_helper() {
    if ! command -v yay &>/dev/null; then
        error "yay no está instalado. Es necesario para instalar paquetes de AUR."
        error "Instálalo primero: https://github.com/Jguer/yay"
        echo -e "  ${CYAN}sudo pacman -S --needed git base-devel${NC}"
        echo -e "  ${CYAN}git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si${NC}"
        exit 1
    fi

    # yay no puede ejecutarse como root; si estamos como root, delegar al usuario real
    if [[ $EUID -eq 0 ]]; then
        local real_user="${SUDO_USER:-${OMARCHY_INSTALL_USER:-}}"
        if [[ -z "$real_user" || "$real_user" == "root" ]]; then
            real_user=$(awk -F: '$3 >= 1000 && $3 < 65000 {print $1; exit}' /etc/passwd 2>/dev/null || true)
        fi
        if [[ -n "$real_user" && "$real_user" != "root" ]]; then
            AUR_HELPER="sudo -u $real_user yay -S --needed --noconfirm"
        else
            error "No se puede determinar el usuario real para ejecutar yay (yay no funciona como root)."
            error "Ejecuta este instalador como usuario normal (sin sudo). El script pedirá permisos cuando los necesite."
            exit 1
        fi
    else
        AUR_HELPER="yay -S --needed --noconfirm"
    fi
}

# Instalar lista de paquetes desde archivo
install_pkg_file() {
    local pkg_file="$1"
    local suite_name="$2"

    if [[ ! -f "$pkg_file" ]]; then
        error "No se encontró el archivo de paquetes: $pkg_file"
        return 1
    fi

    check_aur_helper

    local pkgs=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="$(echo "$line" | sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        if [[ -n "$line" ]]; then
            pkgs+=("$line")
        fi
    done < "$pkg_file"

    if [[ ${#pkgs[@]} -gt 0 ]]; then
        info "Instalando paquetes de ${suite_name} (${#pkgs[@]} paquetes)..."
        $AUR_HELPER "${pkgs[@]}"
        success "${suite_name} instalada exitosamente."
    else
        warn "No hay paquetes para instalar en $pkg_file."
    fi
}
