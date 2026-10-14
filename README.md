# SDD Config

Kit de configuración para trabajar con **Spec-Driven Development (SDD)** usando [Spec Kit](https://github.com/github/spec-kit) dentro de un entorno reproducible de **Devbox**.

## ¿Qué es SDD?

**Spec-Driven Development** (Desarrollo Guiado por Especificaciones) es una metodología en la que la **especificación** es la fuente de verdad del proyecto, y el código es su resultado. En vez de escribir código directamente (o con prompts sueltos a un agente de IA), se sigue un flujo estructurado:

1. **Constitución**: principios y reglas del proyecto.
2. **Especificación**: *qué* se quiere construir y *por qué*.
3. **Plan técnico**: *cómo* se construirá (stack, arquitectura).
4. **Tareas**: lista de pasos concretos y ordenados.
5. **Implementación**: el agente de IA ejecuta las tareas.

Esto hace el trabajo con agentes de IA más predecible, revisable y fácil de mantener.

## ¿Qué es Devbox?

[Devbox](https://www.jetify.com/devbox) es una herramienta de Jetify que crea **entornos de desarrollo aislados y reproducibles** a partir de un archivo `devbox.json`. Usa [Nix](https://nixos.org/) por debajo, pero sin que tengas que aprender Nix: declaras los paquetes que necesitas (Python, uv, git, etc.) y todos los miembros del equipo obtienen exactamente las mismas versiones, sin ensuciar el sistema.

## Contenido del entorno

`devbox.json` define:

| Elemento | Descripción |
|---|---|
| `python@3.12` | Python 3.12 |
| `uv@latest` | Gestor de paquetes y herramientas de Python |
| `git@latest` | Necesario para Spec Kit |
| `init_hook` | Al entrar al shell instala `specify-cli` (Spec Kit) si aún no está disponible |
| `env` | Instala las herramientas de `uv` dentro de `.devbox/uv/`, sin tocar tu `~/.local` |
| script `check` | Atajo para ejecutar `specify check` |

`devbox.lock` fija las versiones exactas; se debe versionar en git.

## Requisitos previos

- Linux, macOS o Windows con **WSL2** (este proyecto se probó en WSL2).
- **curl** y **git** instalados en el sistema.
- **Nix** (lo instala Devbox si no lo tienes, ver abajo).
- **Devbox**.
- Un agente de IA compatible con Spec Kit (por ejemplo Claude Code, GitHub Copilot, Gemini CLI, Cursor, etc.).

### Instalar Devbox

```bash
curl -fsSL https://get.jetify.com/devbox | bash
devbox version
```

Si Nix no está instalado, Devbox ofrecerá instalarlo la primera vez que lo uses.

## Uso paso a paso

1. **Clonar el repositorio**

   ```bash
   git clone <url-del-repo> sdd-config
   cd sdd-config
   ```

2. **Entrar al entorno de Devbox**

   ```bash
   devbox shell
   ```

   La primera vez descarga los paquetes e instala `specify-cli`. Las siguientes entradas son casi inmediatas.

3. **Verificar la instalación**

   ```bash
   specify --help
   devbox run check   # revisa que las herramientas necesarias estén presentes
   ```

4. **Inicializar un proyecto SDD**

   ```bash
   specify init mi-proyecto          # proyecto nuevo
   # o, dentro de un proyecto existente:
   specify init . --here
   ```

   El asistente te pedirá elegir el agente de IA que usarás.

5. **Seguir el flujo SDD** desde tu agente de IA con los comandos que Spec Kit genera:

   | Comando | Función |
   |---|---|
   | `/speckit.constitution` | Definir los principios del proyecto |
   | `/speckit.specify` | Describir qué construir (la especificación) |
   | `/speckit.plan` | Definir el plan técnico |
   | `/speckit.tasks` | Generar la lista de tareas |
   | `/speckit.implement` | Implementar las tareas |

   Los nombres exactos pueden variar según la versión de Spec Kit y el agente; revisa la salida de `specify init`.

6. **Salir del entorno**: `exit` o `Ctrl+D`.

## Comandos útiles de Devbox

```bash
devbox shell            # entrar al entorno
devbox run <script>     # ejecutar un script definido en devbox.json
devbox add <paquete>    # agregar un paquete
devbox rm <paquete>     # quitar un paquete
devbox update           # actualizar y regenerar devbox.lock
```

## Solución de problemas

- **`specify: command not found`**: dentro de `devbox shell`, ejecuta `uv tool install specify-cli`.
- **Actualizar Spec Kit**: `uv tool upgrade specify-cli`.
- **Devbox pide instalar Nix**: acepta; es un requisito de Devbox.
- **Entorno corrupto**: borra `.devbox/` y vuelve a ejecutar `devbox shell`.

## Referencias

- [Documentación de Devbox](https://www.jetify.com/docs/devbox/)
- [Spec Kit](https://github.com/github/spec-kit)
- [uv](https://docs.astral.sh/uv/)
