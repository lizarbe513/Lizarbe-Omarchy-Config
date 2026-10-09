# Centro Lizarbe

Panel de **Lizarbe** para Omarchy: identidad del equipo, catálogo de software por suites y
estado de las actualizaciones. Este repositorio produce dos paquetes del repositorio de Lizarbe:

| Paquete | Qué trae |
| :--- | :--- |
| `lizarbe-centro` | El **Centro Lizarbe** (TUI en Python) y la línea de comandos `lizarbe`. |
| `lizarbe-tema` | Temas de Omarchy `lizarbe` (oscuro), `lizarbe-light` (claro), `lizarbe-arena` (arena + rojo) y `minecraft` (Overworld de día, claro); iconos `Lizarbe-Red`; tema GTK `Darky`; branding, fastfetch y starship; `lizarbe-apply-user`. |

Los dos vienen preinstalados en la ISO de Lizarbe y se actualizan con `omarchy update`
(se publican desde [Lizarbe-Paquetes](https://github.com/lizarbe513/Lizarbe-Paquetes) a partir de
las etiquetas `vX.Y.Z` de este repositorio).

---

## El panel

Se abre desde el menú de Omarchy (**Centro Lizarbe**), desde el lanzador o con `lizarbe`.

| Sección | Qué hace |
| :--- | :--- |
| **Actualizaciones** | Versiones instaladas de los paquetes de Lizarbe frente a las del repositorio, y actualizar el sistema (`omarchy update`). |
| **Iconos y GTK** | Iconos Lizarbe-Red y tema GTK Darky. |
| **Personalización** | Fastfetch, Starship y branding de Lizarbe. |
| **Utilidades** | Zen Browser, LocalSend y otras herramientas (instalar / quitar con un clic). |
| **KDE Connect** | Servicio, cortafuegos (puertos 1714-1764), prueba de conexión y dispositivos. |
| **Apps creativas** · **Dev y Office** | Catálogo por aplicación. |
| **Suites Lizarbe** | Instalar o quitar suites completas (abajo). |
| **Desinstalación** | Revertir el tema o retirar componentes. |

La configuración de Hyprland, la barra y los temas está en las apps de
[Lizarbe-Ajustes](https://github.com/lizarbe513/Lizarbe-Ajustes) (Escritorio, Widgets y Estudio de temas).

Teclado: `↑↓`/`j k` moverse, `←→`/`h l` cambiar de panel o de valor, `Enter`/`Espacio` activar,
`m` menú contextual, `q`/`Esc` salir. Con el ratón: clic, clic derecho y rueda.

## Suites de software

| Suite | Aplicaciones |
| :--- | :--- |
| **Creatividad 2D** | Krita, LibreSprite, Inkscape, Pinta |
| **3D, CAD y motores** | Blender, FreeCAD, Blockbench, Godot |
| **Desarrollo** | Visual Studio Code, Git y Lazygit, Docker y Lazydocker |
| **Ofimática** | ONLYOFFICE, LibreOffice, Obsidian, Xournal++ |
| **Multimedia** | Kdenlive, Shotcut, OBS Studio, Audacity |
| **Webapps** | WhatsApp, YouTube |

Las listas de paquetes están en `packages/` y los instaladores en `scripts/install-*.sh`.

## Línea de comandos

```bash
lizarbe                         # abre el panel
lizarbe status                  # versiones de los paquetes de Lizarbe (y si hay nuevas)
lizarbe update                  # actualiza el sistema y Lizarbe (omarchy update)
lizarbe apply                   # vuelve a aplicar iconos, branding y configuración de usuario
lizarbe install [--2d|--3d|--dev|--office|--multimedia|--webapps|--no-3d|--all]
lizarbe uninstall [--theme-only|--apps-only|--all]
lizarbe help
```

## Desarrollo

```bash
./lizarbe                       # ejecuta el panel desde el código
python -m unittest discover -s tests
```

- `lizarbe` — línea de comandos (bash).
- `lizarbe_tui/` — panel: `cli.py`, `ui/` (dibujo y teclado/ratón), `core/` (sistema, temas,
  Hyprland), `i18n/` (textos en inglés; el español es el texto original).
- `scripts/`, `packages/` — instaladores y listas de las suites.
- `themes/`, `icons/`, `config/` — contenido del paquete `lizarbe-tema`.
