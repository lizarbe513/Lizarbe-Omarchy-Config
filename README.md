# Omarchy - Lizarbe Theme & Suite

Sistema completo de personalización, herramientas y catálogo de software para **Omarchy** (Arch Linux / Hyprland), diseñado para la línea de computadoras **Lizarbe** y orientado a la creatividad visual, modelado 3D, desarrollo de software, ofimática y sincronización móvil.

---

## Características Principales

- **Interfaz TUI Nativa (`lizarbe`)**: Panel interactivo de gestión del sistema accesible tanto desde la terminal como desde el Centro de Aplicaciones (`Super + Espacio`). Abre directamente en ventana flotante, centrada y en formato vertical (680x960 px), sin parpadeos ni paso previo por mosaico.
- **Monitor de Actualizaciones del Equipo**: Monitoreo en tiempo real del estado del sistema, commits locales y remotos en GitHub, hooks de Pacman y actualización con un solo clic.
- **Sincronización Móvil con KDE Connect**: Módulo completo para enlazar smartphones (Android / iOS), detección y apertura automática de puertos en el cortafuegos (UFW 1714-1764), herramientas de prueba (ping, alarma acústica) y apertura de la GUI en ventana flotante unificada.
- **Gestor Visual de Software y Utilidades**: Catálogo de aplicaciones con diseño de tarjetas sobrias (estilo Meca), clasificando programas disponibles e instalados con botones de acción directa.
- **Temas Lizarbe Nativos (Dark & Light)**:
  - `Lizarbe` (modo oscuro): Paleta charcoal/OLED con acentos en rojo técnico y wallpapers pixel art.
  - `Lizarbe Light` (modo claro): Fondo estilo papel milimetrado y dibujo técnico CAD (Whiteprint).
  - Configuración modular para Quickshell (`shell.bar`, `shell.menu`, `shell.launcher`, `shell.lock`).
- **Iconos y Estilo GTK**: Pack de iconos globales `Lizarbe-Red` y tema GTK `Darky`.
- **Diseño Sobrio y Rendimiento**: Paleta monocromática elegante, botones 3D Unicode con biselado, caché optimizada para navegación fluida y sin emojis.

---

## Instalación

Centro Lizarbe se instala como paquete desde el repositorio de Lizarbe (viene preinstalado en la ISO Lizarbe):

```bash
sudo pacman -S lizarbe-centro     # o el metapaquete completo: sudo pacman -S lizarbe
```

Para desarrollo, desde el código fuente: `./install.sh` (las suites de software) y `./lizarbe` (la línea de comandos).

El instalador te permitirá seleccionar interactivamente qué suites deseas habilitar en el equipo.

---

## Panel TUI del Sistema (`lizarbe`)

Puedes abrir el panel interactivo en cualquier momento presionando `Super + Espacio` y buscando **Lizarbe Theme & Suite**, o ejecutando en tu terminal:

```bash
lizarbe
```

### Secciones del Panel:

#### 1. Sistema Lizarbe
- **Actualizaciones**: Monitor del estado de la máquina frente al repositorio oficial en GitHub. Muestra versión local, commit activo, sincronización remota y estado de los hooks automáticos. Permite actualizar el sistema de inmediato.
- **Tema y Estilo**: Selector visual de temas mediante tarjetas de 3 líneas (Lizarbe Dark, Lizarbe Light y temas base de Omarchy), selector de fondos de pantalla, estilo de Starship prompt e iconos.
- **Personalización**: Ajustes de dotfiles, terminales, reglas de ventanas en Hyprland y corrección de comportamientos del sistema.

#### 2. Software y Apps
- **Utilidades**: Catálogo de programas auxiliares (como Zen Browser y LocalSend) organizados en tarjetas: los paquetes pendientes de instalación se resaltan en la parte superior con el botón `[  Instalar ]`, y los ya instalados se atenúan con la opción de desinstalación.
- **KDE Connect**:
  - Control y reinicio del demonio del servicio (`kdeconnectd`).
  - Detección del cortafuegos: Si `ufw` está activo, detecta si los puertos 1714-1764 están bloqueados y ofrece la acción `[ Abrir Puertos ]` con un solo clic.
  - Herramientas: `Abrir GUI` (abre la aplicación oficial en ventana flotante, centrada y del mismo tamaño de 680x960), `Probar Conexión (Ping)` y `Hacer Sonar mi Teléfono`.
  - Dispositivos detectados en la red Wi-Fi local en tiempo real con indicador y botón `[ Vinculado ]`.
  - Gestión del paquete oficial de KDE Connect.
- **Apps Creativas (2D)**: Ilustración, animación y diseño vectorial.
- **Apps Dev y Office**: Modelado 3D, desarrollo de software, ofimática y multimedia.
- **Suites Lizarbe**: Instalación y desinstalación por bloques modulares completos.

#### 3. Mantenimiento
- **Desinstalación**: Opciones guiadas para revertir temas, desinstalar aplicaciones o restablecer la configuración base de Omarchy.

---

## Navegación y Controles del Panel TUI

El panel soporta navegación híbrida tanto por teclado como por ratón:

| Control / Atajo | Acción |
|---|---|
| `j` / `Flecha Abajo` | Mover cursor hacia abajo |
| `k` / `Flecha Arriba` | Mover cursor hacia arriba |
| `h` / `Flecha Izquierda` | Ir al panel izquierdo (Barra lateral) o reducir valores |
| `l` / `Flecha Derecha` | Ir al contenido o incrementar valores |
| `b` / `Backspace` | Atajo rápido para volver al panel lateral izquierdo |
| `Enter` / `Espacio` | Activar opción, presionar botón o abrir selector desplegable |
| `+` / `-` | Ajustar opciones numéricas o ciclar selectores |
| `m` | Abrir menú contextual flotante para la opción seleccionada |
| `q` / `Esc` | Salir de la aplicación o cerrar ventana modal/menú |
| `Clic izquierdo` | Seleccionar categorías, presionar botones o activar tarjetas |
| `Rueda del ratón` | Desplazamiento vertical rápido por el contenido |

---

## Suites y Aplicaciones Incluidas

### 1. Base del Sistema & Temas Lizarbe (`scripts/install-core.sh`)
- Temas Omarchy `Lizarbe` y `Lizarbe Light` en `/usr/share/omarchy/themes/`.
- Pack de iconos `Lizarbe-Red` en `/usr/share/icons/`.
- Navegador web `Zen Browser` predeterminado.
- Tema GTK `Darky` en `/usr/share/themes/`.
- Herramientas: `fastfetch` con isotipo Lizarbe, `starship`, `nwg-look`, `htop`, `kdeconnect`.
- Reglas de Hyprland en `~/.config/hypr/looknfeel.lua` para ventanas flotantes de herramientas.

### 2. Creatividad 2D (`scripts/install-2d.sh`)
- **Krita**: Pintura digital e ilustración profesional.
- **LibreSprite**: Animación y pixel art.
- **Inkscape**: Diseño y vectores.
- **Pinta**: Retoque rápido y ligero de imágenes.

### 3. Creatividad 3D, CAD & Motores (`scripts/install-3d.sh`)
- **Blender**: Modelado 3D, escultura y animación.
- **FreeCAD**: Modelado paramétrico y piezas mecánicas/CAD.
- **Blockbench**: Modelado low-poly y vóxeles.
- **Godot**: Motor de desarrollo de videojuegos 2D/3D.

### 4. Desarrollo & Construcción de Software (`scripts/install-dev.sh`)
- **Visual Studio Code**: Editor de código principal.
- **Git** y **Lazygit**: Control de versiones ágil en terminal.
- **Docker** y **Lazydocker**: Contenedores y servicios locales.

### 5. Ofimática & Productividad (`scripts/install-office.sh`)
- **genOffice**: Suite ofimática moderna potenciada por IA (Genspark).
- **ONLYOFFICE Desktop**: Suite ofimática offline compatible con formatos MS Office.
- **LibreOffice**: Suite ofimática estándar.
- **Obsidian**: Notas interconectadas y gestión de proyectos en Markdown.
- **Xournal++**: Notas manuscritas y bocetos con tableta digitalizadora.

### 6. Multimedia & Audio/Video (`scripts/install-multimedia.sh`)
- **Kdenlive**: Edición de video multipista profesional.
- **Shotcut**: Editor de video rápido y ligero.
- **OBS Studio**: Grabación de pantalla y transmisión.
- **Audacity**: Edición y grabación de audio.

---

## Opciones de Instalación Automatizada (Flags)

Para automatizar la instalación en nuevas máquinas sin interacción manual:

| Comando | Descripción |
|---|---|
| `./install.sh --all` | Instala todas las suites (incluyendo herramientas 3D) |
| `./install.sh --no-3d` | **Recomendado para portátiles sin gráfica dedicada** (instala todo excepto 3D) |
| `./install.sh --core-only` | Solo tema, iconos, branding y dotfiles base (paquete `lizarbe-tema`) |
| `./install.sh --2d` | Solo la suite de Creatividad 2D & Pixel Art |
| `./install.sh --3d` | Solo la suite de Modelado 3D & CAD |
| `./install.sh --dev` | Solo herramientas de desarrollo y contenedores |
| `./install.sh --office` | Solo ofimática, notas y productividad |
| `./install.sh --multimedia` | Solo edición de audio y video |
| `./install.sh --webapps` | Solo accesos integrados (WhatsApp, YouTube) |

También se pueden ejecutar los instaladores de cada suite por separado:
```bash
bash scripts/install-core.sh
bash scripts/install-2d.sh
bash scripts/install-dev.sh
```

---

## Comandos CLI de la Herramienta `lizarbe`

Además de la interfaz visual, el comando `lizarbe` ofrece utilidades por consola:

```bash
# Abrir la interfaz gráfica TUI
lizarbe

# Consultar versión local y estado frente al repositorio remoto
lizarbe status

# Actualizar el tema a la última versión disponible en GitHub
lizarbe update

# Re-aplicar dotfiles, reglas de ventana, iconos y configuración de usuario
lizarbe apply

# Ver ayuda general
lizarbe help
```

### Actualización Automática del Sistema
Lizarbe se entrega como paquetes pacman (`lizarbe-*`) desde el repositorio de Lizarbe, así que se actualiza junto con el sistema con `omarchy update`. Después de cada actualización, `lizarbe-doctor` revisa y repara la integración con Omarchy (menú, reglas de ventana, hooks).

---

## Desinstalación y Reversión

Para retirar componentes o restaurar el tema oficial de Omarchy:

```bash
# Asistente interactivo guiado:
lizarbe uninstall
# o: ./uninstall.sh

# Mediante argumentos directos:
lizarbe uninstall --theme-only    # Elimina los temas Lizarbe, iconos y restaura el tema base
lizarbe uninstall --apps-only     # Remueve las aplicaciones instaladas conservando los temas
lizarbe uninstall --all           # Elimina todo el entorno Lizarbe y restaura el estado original
```
