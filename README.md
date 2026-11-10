# ninaspro

Agentes de IA en 2 líneas para el curso **IA Aplicada: Agentes** de Niñas Pro.

```python
from ninaspro import crear_agente

tutor = crear_agente("Ayudar con tareas de matemáticas", nombre="Tutor")
tutor.chat("¿Me ayudas con 3/4 + 1/2?")
```

> **Estado: prototipo (v0.1.0).** Probado con Python 3.12, openai-agents 0.24 y Gradio 6.31, fuera de Colab. Falta probarlo en un Colab real y decidir cómo llega la key (ver [Pendiente](#pendiente)).

## Contenido

- [Por qué existe](#por-qué-existe)
- [Instalación](#instalación)
- [Uso rápido](#uso-rápido)
- [Guía por clase](#guía-por-clase) (detalle en [`docs/guia-por-clase.md`](docs/guia-por-clase.md))
- [Varios nombres para lo mismo](#varios-nombres-para-lo-mismo)
- [Qué lee el modelo y qué no](#qué-lee-el-modelo-y-qué-no)
- [Cuando algo sale mal](#cuando-algo-sale-mal)
- [Ayuda dentro de Colab](#ayuda-dentro-de-colab)
- [Para profes y tutoras](#para-profes-y-tutoras) (detalle en [`docs/para-profes.md`](docs/para-profes.md))
- [Desarrollo](#desarrollo)
- [Pendiente](#pendiente)

## Por qué existe

En el curso, cada notebook empezaba con unas 25 líneas de preparación: instalar, crear el cliente de OpenRouter, elegir el modelo, desactivar el tracing, montar Drive y cambiar de carpeta. Esas líneas se copiaban de clase en clase y eran donde más fallaba todo:

- **Dos celdas de configuración con modelos distintos** en el mismo notebook (clase 7: Mistral y después Haiku; clase 9: un modelo gratis y después Haiku). Quien ejecutaba en orden quedaba con el modelo equivocado.
- **`drive.mount` + `os.chdir` con una ruta fija**, distinta en cada notebook. Sin acceso a esa carpeta, no corría nada.
- **La plantilla de proyecto no corría tal cual:** definía `skills = [...]` pero usaba `habilidades`, y el modelo no tenía el prefijo del proveedor.
- **`Runner.run` exige `await`,** y `Runner.run_sync` falla en Colab.
- **Gradio con `global memoria`:** con `share=True` se mezclaban las conversaciones de todas las personas que abrían el link.
- **La key se pegaba a mano** en cada notebook.

La idea de `ninaspro` es que **el notebook muestre solo lo que se enseña ese día**. Todo lo demás vive en la librería. Por debajo sigue siendo un `Agent` del [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), así que `Runner.run(tutor, "hola")` funciona igual, para quien quiera ver cómo es por dentro.

Además:

- **Cada clase suma un parámetro**, el que se enseñó ese día. Lo que todavía no se enseña viene apagado (por ejemplo, `memoria` hasta la clase 6).
- **Los errores salen en español, en una línea, y dicen cómo arreglarlos.** Se revisa todo al crear el agente, no recién al conversar.
- **Cada cosa acepta varios nombres** (inglés, español técnico, español educativo).

## Instalación

En Colab, la primera celda de cada notebook (la celda de preparación):

```python
#@title Preparación (ejecútala primero)
!pip install -q git+https://github.com/nifalconi/ninaspro
%env OPENROUTER_API_KEY=sk-or-...
```

- Instala `ninaspro` y sus dependencias: `openai-agents` y `gradio`.
- **La key** va por ahora en esa misma celda. Cómo esconderla es una decisión pendiente. Nunca subas una key a este repositorio.
- Con `#@title`, Colab muestra la celda con un título y se puede ocultar el código. Ver [`docs/para-profes.md`](docs/para-profes.md).
- Necesita Python 3.10 o más nuevo (Colab ya lo cumple).

En tu computador, para desarrollar:

```bash
git clone https://github.com/nifalconi/ninaspro
cd ninaspro
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[pruebas]"
pytest
```

## Uso rápido

```python
from ninaspro import crear_agente, herramienta, interfaz

# Crear el agente: solo las instrucciones son obligatorias
tutor = crear_agente(
    "Ayudar a estudiantes de secundaria con sus tareas.",
    nombre="Tutor Socrático",
    tono="Cercano y paciente. No das la respuesta: guías con preguntas.",
    audiencia="Estudiantes de 14 a 18 años.",
    limitaciones=["Solo temas escolares.", "No des la respuesta final."],
)

tutor.chat("¿Me ayudas con 3/4 + 1/2?")                  # conversa y muestra la respuesta
tutor.chat("¿Me ayudas con 3/4 + 1/2?", ver_pasos=True)  # además muestra qué hizo
respuesta = tutor.obtener_respuesta("hola")               # te entrega el texto para guardarlo
tutor.ver_instrucciones()                                 # el texto que lee el modelo
tutor.borrar_memoria()                                    # olvida la conversación

interfaz(tutor, ejemplos=["¿Cómo sumo fracciones?"])      # página de chat (clase 9)
```

El notebook [`ejemplos/ejemplo_curso.ipynb`](ejemplos/ejemplo_curso.ipynb) recorre todas las clases. Se abre directo en Colab con [este link](https://colab.research.google.com/github/nifalconi/ninaspro/blob/main/ejemplos/ejemplo_curso.ipynb).

## Guía por clase

| Clase | Tema | Lo que se agrega |
|---|---|---|
| 2 | Primer agente | `crear_agente("instrucciones", nombre="...")` y `tutor.chat("hola")` |
| 3 | Instrucciones y personalidad | `tono=`, `audiencia=`, `limitaciones=` y `tutor.ver_instrucciones()` |
| 4 | Herramientas | `@herramienta` arriba de la función y `herramientas=[mi_funcion]` |
| 5 | Habilidades | `habilidades=["mi-habilidad"]` (carpeta `SKILLS/`) |
| 6 | Memoria | `memoria=True`. La memoria en JSON la escriben ellas como herramientas |
| 7 | Guardrails | `guardrails_entrada=validar_entrada`, `guardrails_salida=validar_salida` |
| 8 | Debugging | `tutor.chat("...", ver_pasos=True)` |
| 9 | Interfaz | `interfaz(tutor, titulo=, descripcion=, ejemplos=, mensaje_inicial=)` |
| 10 | Integración | Todo junto. Opcional: dos agentes (`herramientas=[otro]`, `derivar_a=[otro]`) |

Código y explicación de cada clase: [`docs/guia-por-clase.md`](docs/guia-por-clase.md).

## Varios nombres para lo mismo

Cada parámetro y cada función se puede escribir de varias formas: en inglés (como en el OpenAI Agents SDK), en español técnico (el de las presentaciones) o en español educativo. Todas hacen lo mismo.

- La ayuda de Colab muestra el nombre **en negrita**, y en cada parámetro lista los demás: `tono (también: personalidad, tone)`.
- Todos se aceptan **con o sin tilde, con mayúsculas y en singular o plural**: `propósito`, `limitación`, `herramienta`, `Tono`.
- Si escribes dos nombres de lo mismo a la vez (por ejemplo `tono=` y `personalidad=`), sale un error que dice que dejes solo uno.

### `crear_agente(...)`

| Inglés | Español técnico | Español educativo | Otros nombres |
|---|---|---|---|
| `instructions` ✓ | **`instrucciones`** | — | `proposito` |
| `name` ✓ | **`nombre`** | — | — |
| `handoff_description` ✓ | **`descripcion_para_agentes`** | `especialidad` | `cuando_usarme` |
| `tone` | **`tono`** | `personalidad` | — |
| `audience` | **`audiencia`** | `publico_objetivo` | — |
| `rules` | **`limitaciones`** | `reglas` | — |
| `tools` ✓ | **`herramientas`** | — | — |
| `skills` | **`habilidades`** | `recetas` | — |
| `skills_folder` | **`carpeta_habilidades`** | `carpeta_recetas` | — |
| `memory` | **`memoria`** | `recordar` | `memoria_de_sesion` |
| `input_guardrails` ✓* | **`guardrails_entrada`** | `filtro_entrada` | — |
| `output_guardrails` ✓* | **`guardrails_salida`** | `filtro_salida` | — |
| `handoffs` ✓ | **`derivar_a`** | `transferir_a` | — |
| `temperature` ✓ | **`temperatura`** | `creatividad` | `variedad` |

### Lo que se hace con el agente

| Inglés | Español técnico | Español educativo | Otros nombres |
|---|---|---|---|
| `chat()` | **`chat()`** | `chat()` | — |
| `respond()` | **`obtener_respuesta()`** | `responder()` | — |
| `clear_memory()` | **`borrar_memoria()`** | `olvidar()` | — |
| `verbose=True` | **`ver_pasos=True`** | — | — |
| `show_instructions()` | **`ver_instrucciones()`** | — | — |
| `@function_tool` ✓ | **`@herramienta`** | — | — |

### `interfaz(...)`

| Inglés | Español técnico | Español educativo | Otros nombres |
|---|---|---|---|
| `interface()` | **`interfaz()`** | `abrir_chat()` | — |
| `title` | **`titulo`** | — | — |
| `description` | **`descripcion`** | — | — |
| `examples` | **`ejemplos`** | — | — |
| `welcome` | **`mensaje_inicial`** | `bienvenida` | — |
| `theme` | **`tema`** | `colores` | — |
| `share` | **`compartir`** | — | — |

✓ Existe con ese nombre en el OpenAI Agents SDK (`temperature` va dentro de `ModelSettings`; `@function_tool` es su decorador). Los demás nombres en inglés no son del SDK: `Agent(tone=...)` no existe allá.

\* Mismo nombre que en el SDK, pero distinto formato. En el curso un guardrail es una función normal que recibe el texto y devuelve `(True, "")` si está todo bien o `(False, "mensaje")` si hay que bloquear. Si alguien pasa un guardrail hecho con `@input_guardrail` del SDK, sale un error que lo explica.

### Ojo con algunas palabras

- **`reglas`** es otro nombre de `limitaciones` (texto que el modelo lee). En la clase 7, "implementa tres reglas" se refiere a guardrails (código). Si algo se tiene que bloquear siempre, va en `guardrails_entrada` o `guardrails_salida`.
- **`memoria` / `recordar` y `borrar_memoria()` / `olvidar()`** son la memoria de la conversación (memoria de sesión). No tienen que ver con las herramientas que guardan datos en un JSON (`recordar_nombre`, `olvidar_dato`), que se escriben en la clase 6.
- **`creatividad`**: la temperatura no hace al modelo más creativo, hace sus respuestas más variadas (con 0 responde casi siempre igual). Por eso también existe `variedad`.

## Qué lee el modelo y qué no

El `Agent` del SDK tiene **un solo campo de texto** (`instructions`) para todo lo que lee el modelo, y campos aparte para lo que hace el programa. `crear_agente` arma ese texto con la ficha de identidad de la clase 3:

```
# Nombre
Tu nombre es Tutor Socrático. Es tu nombre como agente, no el de la persona que te escribe.

# Propósito
Ayudar a estudiantes de secundaria con sus tareas.

# Tono e identidad
Cercano y paciente. No das la respuesta: guías con preguntas.

# Audiencia
Estudiantes de 14 a 18 años.

# Limitaciones
- Solo temas escolares.
- No des la respuesta final.
```

| Parámetro | ¿Quién lo usa? |
|---|---|
| `instrucciones`, `tono`, `audiencia`, `limitaciones` | El modelo lo lee (va al texto de arriba) |
| `nombre` | Los dos: el modelo lo lee y el programa lo usa (título de la interfaz, nombre como herramienta) |
| `habilidades` | Los dos: el índice va al texto y los archivos se leen con herramientas |
| `descripcion_para_agentes` | Lo leen **los otros agentes**, para saber cuándo llamar a este. El propio agente no la ve |
| `herramientas` | El programa. El modelo solo ve el nombre y el docstring de cada una |
| `memoria`, `guardrails_*`, `derivar_a`, `temperatura` | El programa. El modelo no los lee |

Por eso **`limitaciones` y guardrails no son lo mismo**: las limitaciones son reglas escritas que el modelo puede saltarse ("guardrail de sistema"); un guardrail es código que bloquea siempre ("guardrail de entrada"). Es la diferencia que se enseña en la clase 7.

## Cuando algo sale mal

Los errores de `ninaspro` se muestran en una línea, en español, con la línea de la celda donde está el problema:

```
❌ (línea 2 de tu celda) crear_agente no tiene limitasiones=. ¿Quisiste decir limitaciones=?
```

| Lo que escribió | Lo que ve |
|---|---|
| `crear_agente("Tutor", "Ayudar…")` | Solo las instrucciones van sin nombre. Lo demás se escribe con su nombre… |
| `memoria="no"` | memoria tiene que ser True o False (sin comillas), no 'no'. |
| `herramientas=["calcular_tiempo"]` | En herramientas pusiste 'calcular_tiempo' entre comillas. Escríbela sin comillas… |
| `herramientas=[calcular_tiempo(6, 3)]` | En herramientas va el nombre de la función, sin (). |
| `tono="…", personalidad="…"` | Escribiste tono= y personalidad=, que son lo mismo. Deja solo uno. |
| `model="gpt-4"` | En crear_agente no se usa model=. El modelo ya viene listo: no hace falta ponerlo. |
| Habilidad mal escrita | No encontré la habilidad 'tutor-socratik' en SKILLS. ¿Quisiste decir 'tutor-socratico'? Las que hay son: … |
| Guardrail sin el `return` final | 'validar_entrada' no devolvió nada. ¿Te faltó el return True, "" del final? |
| `interfaz(tutor, tema="rosado")` | No existe el tema 'rosado'. Puedes usar: Citrus, Cyberpunk, Default, … |
| La key no sirve | No pude conectarme con el modelo: la key no funciona. Avísale a tu profe. |

También hay avisos (⚠️) que no detienen la celda: una herramienta sin docstring o sin tipos en sus parámetros, o una interfaz con un agente sin `memoria=True`.

## Ayuda dentro de Colab

La ayuda sale del código ya cargado: la celda de preparación tiene que haberse ejecutado antes.

- **Al escribir `crear_agente(`** o **pasar el mouse** sobre el nombre: la firma y la explicación de cada parámetro, con un ejemplo.
- **`crear_agente?`** abre la ayuda en un panel; **`help(ninaspro)`** muestra la tabla de nombres.
- **`tutor.` + Tab** muestra solo lo del curso: `chat`, `obtener_respuesta`, `borrar_memoria`, `ver_instrucciones`, `nombre`.
- Si una celda termina en `tutor`, se ve `<Agente 'Tutor'. Escríbele con .chat("hola")>`.

## Para profes y tutoras

En [`docs/para-profes.md`](docs/para-profes.md): cómo armar la celda de preparación, la key, cómo actualizar la librería, dónde poner las habilidades, qué pasa con el `ninaspro.py` de la clase 2 y los problemas más comunes.

## Desarrollo

```
src/ninaspro/__init__.py   lo que se importa y la ayuda de help(ninaspro)
src/ninaspro/agentes.py    todo el funcionamiento
docs/                      guía por clase y guía para profes
ejemplos/                  notebook de ejemplo para Colab
tests/                     pruebas sin conexión (pytest)
```

- **Las pruebas no llaman al modelo** (usan una key falsa): `pytest`.
- **Para agregar un nombre nuevo** a un parámetro: súmalo en `_NOMBRES_AGENTE` (o `_NOMBRES_INTERFAZ`) en `agentes.py`, en el docstring de esa función, en la tabla de `__init__.py` y en este README. `tests/test_nombres.py` falla si falta en alguno de esos lugares, o si un nombre sirve para dos parámetros.
- **Reglas de diseño:** lo pedagógico manda; errores en español, al crear el agente, en una línea y diciendo cómo se arreglan; nada de fallas silenciosas; nada de jerga del SDK en el código de la alumna; español de Latinoamérica.

Detalles técnicos que conviene saber antes de tocar el código:

- **asyncio:** Colab ya tiene un event loop corriendo, así que `Runner.run_sync` falla. Todo corre en un loop propio en un hilo aparte, y siempre el mismo, porque el cliente de OpenAI guarda conexiones atadas a su loop.
- **Gradio:** la memoria va por `request.session_hash`, una por persona que abre el link. En Gradio 6, el tema va en `launch()`.
- **Errores cortos:** `ErrorEnTuAgente` se registra con `get_ipython().set_custom_exc(...)` al importar. `__tracebackhide__` solo no acorta los tracebacks.
- **Ayuda:** `crear_agente.__signature__` es una firma limpia en el orden en que se enseña; `Agente.__dir__` limita lo que muestra Tab.

## Pendiente

- **Probarlo en un Colab real:** la instalación desde GitHub, la ayuda al pasar el mouse y el error en una línea.
- **La key:** decidir cómo llega (Secretos de Colab, una casilla, o dentro de la librería).
- **Nombre del módulo:** el `ninaspro.py` de la clase 2 (repo `ninas-pro-agentes`) se llama igual. No conviene usar los dos en la misma sesión de Colab.
