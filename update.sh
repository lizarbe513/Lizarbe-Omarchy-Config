#!/usr/bin/env bash
# ==============================================================================
# Script de Actualización Rápida para el Tema Lizarbe & Dotfiles en Omarchy
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

info "=== Actualizando Tema Lizarbe & Configuraciones en la Raíz del Sistema ==="
ensure_sudo

# 1. Obtener últimos cambios del repositorio si es un clon de Git
if [[ -d "$SCRIPT_DIR/.git" ]] && command -v git &>/dev/null; then
    info "Descargando actualizaciones desde GitHub (git pull)..."
    git -C "$SCRIPT_DIR" pull --ff-only || {
        warn "No se pudo realizar git pull automático (posibles cambios locales). Continuando con la aplicación..."
    }
fi

# 2. Actualizar temas nativos Lizarbe (Dark y Light) en /usr/share/omarchy/themes/
info "Actualizando temas Lizarbe (Dark y Light) en /usr/share/omarchy/themes/..."
$SUDO mkdir -p "/usr/share/omarchy/themes"
$SUDO rm -rf "/usr/share/omarchy/themes/lizarbe" "/usr/share/omarchy/themes/lizarbe-light"
$SUDO cp -r "$SCRIPT_DIR/config/omarchy/themes/lizarbe" "/usr/share/omarchy/themes/"
$SUDO cp -r "$SCRIPT_DIR/config/omarchy/themes/lizarbe-light" "/usr/share/omarchy/themes/"
$SUDO chmod -R a+rX "/usr/share/omarchy/themes/lizarbe" "/usr/share/omarchy/themes/lizarbe-light"
rm -rf "$HOME/.config/omarchy/themes/lizarbe" "$HOME/.config/omarchy/themes/lizarbe-light"

# 3. Actualizar branding a nivel global y de usuario
if [[ -d "$SCRIPT_DIR/config/omarchy/branding" ]]; then
    info "Actualizando branding personalizado en el sistema..."
    $SUDO mkdir -p "/usr/share/omarchy/branding" "/etc/omarchy/branding"
    $SUDO cp -r "$SCRIPT_DIR/config/omarchy/branding/"* "/usr/share/omarchy/branding/" 2>/dev/null || true
    $SUDO cp -r "$SCRIPT_DIR/config/omarchy/branding/"* "/etc/omarchy/branding/" 2>/dev/null || true
    $SUDO chmod -R a+rX "/usr/share/omarchy/branding" "/etc/omarchy/branding" 2>/dev/null || true
    mkdir -p "$HOME/.config/omarchy/branding"
    cp -r "$SCRIPT_DIR/config/omarchy/branding/"* "$HOME/.config/omarchy/branding/"
fi

# 4. Actualizar configuración de Fastfetch y Starship
info "Actualizando configuración de terminal, Starship y Fastfetch..."
$SUDO mkdir -p "/etc/xdg/fastfetch"
$SUDO cp -r "$SCRIPT_DIR/config/fastfetch/"* "/etc/xdg/fastfetch/"
$SUDO chmod -R a+rX "/etc/xdg/fastfetch"

if [[ -f "$SCRIPT_DIR/config/starship.toml" ]]; then
    $SUDO cp "$SCRIPT_DIR/config/starship.toml" "/etc/starship.toml"
    $SUDO chmod a+r "/etc/starship.toml"
fi

if [[ -d "/etc/skel" ]]; then
    $SUDO mkdir -p "/etc/skel/.config/fastfetch"
    $SUDO cp -r "$SCRIPT_DIR/config/fastfetch/"* "/etc/skel/.config/fastfetch/" 2>/dev/null || true
    [[ -f "$SCRIPT_DIR/config/starship.toml" ]] && $SUDO cp "$SCRIPT_DIR/config/starship.toml" "/etc/skel/.config/" 2>/dev/null || true
fi

mkdir -p "$HOME/.config/fastfetch"
cp -r "$SCRIPT_DIR/config/fastfetch/"* "$HOME/.config/fastfetch/"
[[ -f "$SCRIPT_DIR/config/starship.toml" ]] && cp "$SCRIPT_DIR/config/starship.toml" "$HOME/.config/"

# 5. Actualizar pack de iconos Lizarbe-Red
if [[ -d "$SCRIPT_DIR/icons/Lizarbe-Red" ]]; then
    info "Actualizando iconos Lizarbe-Red en /usr/share/icons/..."
    $SUDO mkdir -p "/usr/share/icons"
    $SUDO cp -r "$SCRIPT_DIR/icons/Lizarbe-Red" "/usr/share/icons/"
    $SUDO chmod -R a+rX "/usr/share/icons/Lizarbe-Red"
    if command -v gtk-update-icon-cache &>/dev/null; then
        $SUDO gtk-update-icon-cache -f "/usr/share/icons/Lizarbe-Red" >/dev/null 2>&1 || true
    fi
    mkdir -p "$HOME/.local/share/icons" "$HOME/.icons"
    ln -sf "/usr/share/icons/Lizarbe-Red" "$HOME/.local/share/icons/Lizarbe-Red" 2>/dev/null || true
    ln -sf "/usr/share/icons/Lizarbe-Red" "$HOME/.icons/Lizarbe-Red" 2>/dev/null || true
    if [[ -d "$HOME/Projects" ]] && command -v gio &>/dev/null; then
        gio set -t string "$HOME/Projects" metadata::custom-icon-name folder-projects 2>/dev/null || true
    fi
fi

# 6. Actualizar tema GTK Darky en /usr/share/themes/
if [[ -d "$SCRIPT_DIR/themes/Darky" ]]; then
    info "Actualizando tema GTK Darky en /usr/share/themes/..."
    $SUDO mkdir -p "/usr/share/themes"
    $SUDO cp -r "$SCRIPT_DIR/themes/Darky" "/usr/share/themes/"
    $SUDO chmod -R a+rX "/usr/share/themes/Darky"
    mkdir -p "$HOME/.local/share/themes"
    ln -sf "/usr/share/themes/Darky" "$HOME/.local/share/themes/Darky" 2>/dev/null || true
    # Limpiar posibles enlaces en gtk-4.0 para que GTK4 responda dinámicamente a los temas de Omarchy
    for f in "$HOME/.config/gtk-4.0/gtk.css" "$HOME/.config/gtk-4.0/gtk-dark.css" "$HOME/.config/gtk-4.0/assets"; do
        if [[ -L "$f" && "$(readlink -f "$f" 2>/dev/null)" == *Darky* ]]; then
            rm -f "$f"
        fi
    done
fi

# 7. Asegurar que Zen Browser siga como predeterminado si está instalado
if command -v zen-browser &>/dev/null && command -v omarchy-default-browser &>/dev/null; then
    omarchy-default-browser zen >/dev/null 2>&1 || true
fi

# 8. Refrescar tema de forma nativa a través de Omarchy
if command -v omarchy &>/dev/null; then
    local_current=""
    if command -v omarchy-theme-current &>/dev/null; then
        local_current=$(omarchy-theme-current 2>/dev/null || echo "")
    else
        local_current=$(omarchy theme current 2>/dev/null || echo "")
    fi

    if [[ "$local_current" == "lizarbe-light" ]]; then
        info "Recargando tema Lizarbe Light en vivo..."
        omarchy theme set lizarbe-light || true
    elif [[ "$local_current" =~ [Ll]izarbe ]]; then
        info "Recargando tema Lizarbe en vivo..."
        omarchy theme set lizarbe || true
    fi
fi

# 9. Actualizar la aplicación TUI/CLI 'lizarbe', entrada de escritorio y hooks en el sistema
if [[ -f "$SCRIPT_DIR/lizarbe" ]]; then
    info "Actualizando binarios y TUI de la aplicación 'lizarbe'..."
    if [[ "$SCRIPT_DIR" != "/opt/Lizarbe-Omarchy-Theme" && -d "/opt/Lizarbe-Omarchy-Theme" && -d "$SCRIPT_DIR/lizarbe_tui" ]]; then
        $SUDO rm -rf "/opt/Lizarbe-Omarchy-Theme/lizarbe_tui"
        $SUDO cp -r "$SCRIPT_DIR/lizarbe_tui" "/opt/Lizarbe-Omarchy-Theme/"
        [[ -f "$SCRIPT_DIR/lizarbe.desktop" ]] && $SUDO cp -f "$SCRIPT_DIR/lizarbe.desktop" "/opt/Lizarbe-Omarchy-Theme/"
    fi
    $SUDO mkdir -p "/usr/local/bin" "$HOME/.local/bin"
    $SUDO cp -p "$SCRIPT_DIR/lizarbe" "/usr/local/bin/lizarbe"
    cp -f "$SCRIPT_DIR/lizarbe" "$HOME/.local/bin/lizarbe"
    $SUDO ln -sf "/usr/local/bin/lizarbe" "/usr/local/bin/lizarbe-tui" 2>/dev/null || true
    ln -sf "$HOME/.local/bin/lizarbe" "$HOME/.local/bin/lizarbe-tui" 2>/dev/null || true
    [[ -f "$SCRIPT_DIR/lizarbe-update" ]] && $SUDO cp -p "$SCRIPT_DIR/lizarbe-update" "/usr/local/bin/lizarbe-update"
    [[ -f "$SCRIPT_DIR/lizarbe-apply-user" ]] && $SUDO cp -p "$SCRIPT_DIR/lizarbe-apply-user" "/usr/local/bin/lizarbe-apply-user"
    $SUDO chmod 755 "/usr/local/bin/lizarbe" "/usr/local/bin/lizarbe-tui" 2>/dev/null || true
    chmod 755 "$HOME/.local/bin/lizarbe" "$HOME/.local/bin/lizarbe-tui" 2>/dev/null || true
    [[ -f "/usr/local/bin/lizarbe-update" ]] && $SUDO chmod 755 "/usr/local/bin/lizarbe-update"
    [[ -f "/usr/local/bin/lizarbe-apply-user" ]] && $SUDO chmod 755 "/usr/local/bin/lizarbe-apply-user"
    if [[ -f "$SCRIPT_DIR/lizarbe.desktop" ]]; then
        mkdir -p "$HOME/.local/share/applications"
        cp -f "$SCRIPT_DIR/lizarbe.desktop" "$HOME/.local/share/applications/lizarbe.desktop"
        $SUDO mkdir -p "/usr/share/applications"
        $SUDO cp -f "$SCRIPT_DIR/lizarbe.desktop" "/usr/share/applications/lizarbe.desktop"
        $SUDO chmod 644 "/usr/share/applications/lizarbe.desktop"
    fi

    # Reglas de ventana flotante en su propio archivo (no en looknfeel.lua)
    [[ -f "$SCRIPT_DIR/lizarbe-hypr-rules" ]] && bash "$SCRIPT_DIR/lizarbe-hypr-rules" || true
    [[ -f "$SCRIPT_DIR/lizarbe-hypr-rules" ]] && $SUDO cp -p "$SCRIPT_DIR/lizarbe-hypr-rules" "/usr/local/bin/lizarbe-hypr-rules" || true

    # Actualizar hook post-update
    mkdir -p "$HOME/.config/omarchy/hooks/post-update.d"
    cat << 'EOF' > "$HOME/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook"
#!/bin/bash
# Hook prioritario post-update para actualizar tema Lizarbe
if command -v lizarbe &>/dev/null; then
    lizarbe update --non-interactive || true
elif [[ -x /usr/local/bin/lizarbe ]]; then
    /usr/local/bin/lizarbe update --non-interactive || true
elif command -v lizarbe-update &>/dev/null; then
    lizarbe-update --non-interactive || true
fi
EOF
    chmod 755 "$HOME/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook"

    if [[ -d "/etc/skel" ]]; then
        $SUDO mkdir -p "/etc/skel/.config/omarchy/hooks/post-update.d"
        $SUDO cp -p "$HOME/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook" "/etc/skel/.config/omarchy/hooks/post-update.d/00-lizarbe-update.hook" 2>/dev/null || true
    fi

    # Se retira el hook de pacman de versiones anteriores (corría como root).
    $SUDO rm -f "/etc/pacman.d/hooks/00-lizarbe-update.hook" 2>/dev/null || true
fi

echo ""
success "=============================================================="
success " ¡Tema Lizarbe y dotfiles actualizados en la raíz con éxito!"
success "=============================================================="
