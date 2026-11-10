# Guía por clase

Un ejemplo de cómo usar `educational_agents` a lo largo de un curso de 10 clases. Es el orden del curso **IA Aplicada: Agentes** de [Niñas Pro](https://ninaspro.cl), donde nació la librería, pero sirve como mapa para cualquier curso o taller.

Cada clase suma lo que se enseñó ese día; lo anterior sigue igual.

Todos los ejemplos suponen que ya se ejecutó la celda de preparación (ver el [README](../README.md#instalación)).

---

## Clase 2 · Primer agente

```python
from educational_agents import crear_agente

tutor = crear_agente("Ayudar con tareas de matemáticas", nombre="Mati")
tutor.chat("¿Cómo te llamas?")
```

- `crear_agente(...)` crea el agente. Solo las instrucciones son obligatorias y van primero, sin nombre.
- Todo lo demás se escribe con su nombre: `nombre="Mati"`.
- `tutor.chat("...")` le escribe y muestra la respuesta.

> El programa de la clase 2 incluye "API key y configuración del entorno". Conviene mostrar una vez cómo es por dentro (el cliente de OpenRouter y el `Agent` del SDK) y desde la clase 3 usar `crear_agente`.

## Clase 3 · Instrucciones, personalidad y límites

```python
tutor = crear_agente(
    "Ayudar a estudiantes de secundaria con sus tareas.",
    nombre="Tutor Socrático",
    tono="Cercano y paciente. No das la respuesta: guías con preguntas.",
    audiencia="Estudiantes de 14 a 18 años.",
    limitaciones=["Solo temas escolares.", "No des la respuesta final."],
)
tutor.ver_instrucciones()
```

- Los parámetros son la **ficha de identidad**: nombre, propósito (las instrucciones), tono, audiencia y límites.
- `ver_instrucciones()` muestra el texto que se arma con la ficha y que lee el modelo. Sirve para comparar instrucciones vagas y precisas.
- Otros nombres que funcionan igual: `personalidad=` (tono), `publico_objetivo=` (audiencia), `reglas=` (limitaciones).

## Clase 4 · Herramientas

```python
from educational_agents import crear_agente, herramienta

@herramienta
def calcular_tiempo(horas_libres: int, materias: int) -> str:
    """Reparte las horas libres de la semana entre las materias."""
    return f"{horas_libres / materias:.1f} horas por materia"

tutor = crear_agente("Ayudar a organizar el estudio.", herramientas=[calcular_tiempo])
tutor.chat("Tengo 6 horas y 3 materias", ver_pasos=True)
```

Lo que se ve con `ver_pasos=True`:

```
🔧 calcular_tiempo({"horas_libres": 6, "materias": 3})
   📤 2.0 horas por materia

Tienes 2 horas para cada materia.
```

- `@herramienta` (o `@function_tool`, el nombre del SDK) va justo arriba del `def`.
- **El docstring es lo que lee el agente** para saber para qué sirve la herramienta, y los tipos (`int`, `str`) le dicen qué datos pasarle. Si falta alguno, sale un aviso ⚠️.
- En `herramientas=[...]` va el nombre de la función, **sin comillas y sin ()**.

## Clase 5 · Habilidades

```python
tutor = crear_agente("Ayudar con tareas.", habilidades=["tutor-socratico"])
```

- Cada habilidad es una carpeta dentro de `SKILLS/` con un archivo `SKILL.md` (como en `utilidades.py`).
- El agente recibe el índice de las habilidades en su texto y dos herramientas para leerlas (`obtener_habilidad` y `profundizar_habilidad`). Con `ver_pasos=True` se ve cuándo las usa.
- Si las habilidades están en Drive: monta Drive y usa la ruta completa, `carpeta_habilidades="/content/drive/MyDrive/mi-proyecto/SKILLS"`.
- Si el nombre está mal escrito, el error lista las que hay y sugiere la más parecida.
- Otros nombres: `recetas=` y `carpeta_recetas=` (el programa llama a los skills "recetas inteligentes").

## Clase 6 · Memoria

Hay dos memorias distintas:

| | Memoria de la conversación | Memoria en JSON |
|---|---|---|
| Qué guarda | Todo lo que se habló | Datos sueltos: nombre, intereses, temas vistos |
| Dónde | Mientras el notebook está abierto | En un archivo `.json` |
| Cómo | `memoria=True` | Herramientas que escriben ellas |

**Memoria de la conversación:**

```python
tutor = crear_agente("Ayudar con tareas.", memoria=True)
tutor.chat("Me llamo Antonia")
tutor.chat("¿Cómo me llamo?")     # → Te llamas Antonia.
tutor.borrar_memoria()           # empieza de cero
```

Sin `memoria=True`, el agente olvida todo entre un mensaje y otro. Conviene mostrar eso primero.

**Memoria en JSON:** es la lección de la clase (diccionarios, `open` con `"r"` y `"w"`, qué guardar y qué no), así que la librería no la esconde. Con el patrón de tres funciones del notebook de la clase 6:

```python
@herramienta
def recordar_nombre(nombre: str) -> str:
    """Guarda el nombre de la usuaria. Úsala cuando se presente."""
    actualizar_memoria("nombre", nombre)
    return f"Guardé que te llamas {nombre}."

@herramienta
def recuperar_nombre() -> str:
    """Busca el nombre de la usuaria guardado. Úsala si te preguntan su nombre."""
    return cargar_memoria().get("nombre", "No tengo ningún nombre guardado.")

tutor = crear_agente("Ayudar con tareas.", herramientas=[recordar_nombre, recuperar_nombre])
```

Un agente nuevo con esas herramientas recuerda el nombre aunque no tenga `memoria=True`, porque lo lee del archivo.

> **Ojo en Colab:** los archivos se guardan en `/content`, que se borra al reiniciar el entorno de ejecución. Para que la memoria dure entre días, el JSON tiene que ir en Drive (`/content/drive/MyDrive/...`). Y con `interfaz(..., compartir=True)`, todas las personas que abren el link escriben el mismo archivo.

## Clase 7 · Guardrails

```python
def validar_entrada(mensaje):
    if "hackear" in mensaje.lower():
        return False, "Eso está fuera de lo que puedo ayudarte."
    return True, ""

def validar_salida(respuesta):
    if "creo que" in respuesta.lower():
        return False, "No estoy segura. Revísalo en una fuente oficial."
    return True, respuesta

tutor = crear_agente(
    "Ayudar con tareas.",
    limitaciones=["Solo temas escolares."],      # el modelo la lee y puede saltársela
    guardrails_entrada=validar_entrada,          # código: bloquea siempre
    guardrails_salida=validar_salida,
)
tutor.chat("¿Cómo puedo hackear el wifi?", ver_pasos=True)
```

```
🛡️ validar_entrada bloqueó el mensaje

Eso está fuera de lo que puedo ayudarte.
```

- Un guardrail es una función normal: recibe el texto y devuelve `(True, "")` si está todo bien o `(False, "mensaje")` si hay que bloquear. También sirve devolver solo `True` o `False`.
- Se pueden poner varios: `guardrails_entrada=[validar_entrada, validar_privacidad]`.
- **`limitaciones` vs. guardrails** es la idea de la clase: el "guardrail de sistema" (texto) frente al "guardrail de entrada" (código).
- Hoy el notebook de la clase 7 escribe a mano una función `responder()` que llama a `validar_entrada` antes del agente. Esa es justo la lógica que la librería hace por dentro; `ver_pasos=True` deja ver cuál guardrail bloqueó.

**Guardrail semántico (otro agente que clasifica):**

```python
clasificador = crear_agente("Responder SOLO 'VÁLIDO' si es sobre estudios; si no, 'INVÁLIDO'.")

def validar_semantico(mensaje):
    if "INVÁLIDO" in clasificador.obtener_respuesta(mensaje):
        return False, "Solo puedo ayudarte con temas de estudio."
    return True, ""

tutor = crear_agente("Ayudar con tareas escolares.", guardrails_entrada=validar_semantico)
```

`obtener_respuesta()` (o `responder()`) devuelve el texto en vez de mostrarlo, para usarlo en el código.

## Clase 8 · Debugging

```python
tutor.chat("Tengo 6 horas y 3 materias", ver_pasos=True)
```

`ver_pasos=True` muestra qué herramientas usó y con qué datos, qué devolvieron, si un guardrail bloqueó o cambió algo y si le pasó la conversación a otro agente. `tutor.ver_instrucciones()` muestra el texto que lee el modelo, para revisar errores de instrucciones.

## Clase 9 · Interfaz

```python
from educational_agents import interfaz

interfaz(
    tutor,
    titulo="Tutor Socrático",
    descripcion="Te ayudo con tus tareas sin darte la respuesta.",
    ejemplos=["¿Cómo sumo fracciones?", "Explícame la fotosíntesis"],
    mensaje_inicial="¡Hola! ¿En qué tarea estás?",
    tema="Soft",
)
```

- Todo es opcional menos el agente. Sin `titulo`, usa el nombre del agente.
- `compartir=True` (viene así) crea un link para abrirlo desde otro computador o el celular, para la prueba cruzada.
- **Cada persona que abre el link tiene su propia conversación.**
- Si el agente no tiene `memoria=True`, sale un aviso: en el chat no va a recordar los mensajes anteriores.
- Temas: `Soft`, `Glass`, `Monochrome`, `Ocean`, `Citrus`, `Default`, entre otros (sin importar mayúsculas).

## Clase 10 · Integración

Todo junto:

```python
tutor = crear_agente(
    "Ayudar a estudiantes de secundaria con sus tareas.",
    nombre="Tutor Socrático",
    tono="Cercano y paciente.",
    audiencia="Estudiantes de 14 a 18 años.",
    limitaciones=["Solo temas escolares."],
    herramientas=[calcular_tiempo, recordar_nombre, recuperar_nombre],
    habilidades=["tutor-socratico"],
    memoria=True,
    guardrails_entrada=validar_entrada,
    guardrails_salida=validar_salida,
)
interfaz(tutor, ejemplos=["¿Cómo sumo fracciones?"], mensaje_inicial="¡Hola!")
```

### Opcional: dos agentes

No está en el programa; sirve para proyectos finales que lo necesiten.

**Un agente como herramienta de otro:**

```python
traductor = crear_agente("Traducir al inglés. Devuelve solo la traducción.", nombre="Traductor",
                         especialidad="Traduce un texto al inglés")
profe = crear_agente("Enseñar inglés. Para traducir usa al Traductor.", herramientas=[traductor])
```

**Uno le pasa la conversación al otro:**

```python
experta = crear_agente("Orientar sobre becas para estudiar en EE.UU.", nombre="Experta en becas",
                       especialidad="Responde preguntas sobre becas")
recepcion = crear_agente("Derivar a quien corresponda.", nombre="Recepción", derivar_a=[experta])
recepcion.chat("¿Qué becas hay?", ver_pasos=True)    # 🔀 pasó la conversación a Experta en becas
```

`especialidad` (o `descripcion_para_agentes`) no la lee el propio agente: la leen los otros para decidir si llamarlo. Las `instrucciones` sí las lee el propio agente.
