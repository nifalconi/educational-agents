"""Todo el funcionamiento de educational_agents: crear_agente, interfaz, herramienta y avisos.

La tabla de nombres y la guía de uso están en el docstring del paquete
(help(educational_agents)) y en el README del repositorio.
"""

import asyncio
import difflib
import inspect
import os
import re
import threading
import unicodedata
from pathlib import Path

import openai
from agents import (Agent, FunctionTool, InputGuardrail, MaxTurnsExceeded, ModelSettings,
                    OpenAIChatCompletionsModel, OutputGuardrail, Runner,
                    set_default_openai_client, set_tracing_disabled)
from agents import function_tool as _function_tool_sdk
from openai import AsyncOpenAI

MODELO_POR_DEFECTO = "anthropic/claude-haiku-5.5"   # rápido, barato y bueno usando herramientas
URL_POR_DEFECTO = "https://openrouter.ai/api/v1"     # OpenRouter: una sola key para muchos modelos

_estado = {"client": None, "loop": None, "modelo": MODELO_POR_DEFECTO}
_CARPETA_PAQUETE = os.path.dirname(os.path.abspath(__file__))


class ErrorEnTuAgente(Exception):
    """Algo en cómo se creó o se usa el agente. El mensaje dice cómo arreglarlo."""


_ARGUMENTO_SIN_NOMBRE = {
    "crear_agente": "Solo las instrucciones van sin nombre. Lo demás se escribe con su nombre, "
                    "por ejemplo: crear_agente(\"Ayudar con tareas\", nombre=\"Tutor\")",
    "interfaz": "Después del agente, lo demás va con su nombre: interfaz(tutor, titulo=\"Mi tutor\")",
    "chat": "Después del mensaje, ver_pasos va con su nombre: tutor.chat(\"hola\", ver_pasos=True)",
    "obtener_respuesta": "obtener_respuesta recibe solo el mensaje: "
                         "tutor.obtener_respuesta(\"hola\")",
}
_ARGUMENTO_SIN_NOMBRE.update(abrir_chat=_ARGUMENTO_SIN_NOMBRE["interfaz"],
                             interface=_ARGUMENTO_SIN_NOMBRE["interfaz"],
                             responder=_ARGUMENTO_SIN_NOMBRE["obtener_respuesta"],
                             respond=_ARGUMENTO_SIN_NOMBRE["obtener_respuesta"])


def _traducir_type_error(mensaje):
    """'crear_agente() takes from 0 to 1 positional arguments...' -> el aviso en español.

    Devuelve None si el TypeError no es de una función de esta librería.
    """
    encontrado = re.match(r"^(?:Agente\.)?(\w+)\(\) takes .* positional arguments? but", mensaje)
    return _ARGUMENTO_SIN_NOMBRE.get(encontrado.group(1)) if encontrado else None


def _mostrar_error_corto(shell, etype, evalue, tb, tb_offset=None):
    """En Colab/Jupyter, nuestros errores se muestran en una línea, sin el traceback
    de adentro de esta librería (que no ayuda a una alumna)."""
    if issubclass(etype, TypeError):
        traducido = _traducir_type_error(str(evalue))
        if traducido is None:   # un TypeError cualquiera: se muestra como siempre
            shell.showtraceback((etype, evalue, tb), tb_offset=tb_offset)
            return None
        evalue = traducido
    linea = None
    while tb is not None:
        if not tb.tb_frame.f_code.co_filename.startswith(_CARPETA_PAQUETE):
            linea = tb.tb_lineno
        tb = tb.tb_next
    donde = f"(línea {linea} de tu celda) " if linea else ""
    print(f"❌ {donde}{evalue}")


try:
    from IPython import get_ipython
    if get_ipython() is not None:
        get_ipython().set_custom_exc((ErrorEnTuAgente, TypeError), _mostrar_error_corto)
except ImportError:
    pass


# --- Varios nombres para lo mismo ---------------------------------------------
# El primero de cada lista es el nombre que muestra la ayuda; el resto son
# sinónimos (inglés del SDK, español educativo, otros). Además se aceptan con o
# sin tilde, con mayúsculas y en singular o plural.

_NOMBRES_AGENTE = {
    "instrucciones": ["instructions", "proposito"],
    "nombre": ["name"],
    "descripcion_para_agentes": ["handoff_description", "especialidad", "cuando_usarme"],
    "tono": ["tone", "personalidad"],
    "audiencia": ["audience", "publico_objetivo"],
    "limitaciones": ["rules", "reglas"],
    "herramientas": ["tools"],
    "habilidades": ["skills", "recetas"],
    "carpeta_habilidades": ["skills_folder", "carpeta_recetas"],
    "memoria": ["memory", "recordar", "memoria_de_sesion"],
    "guardrails_entrada": ["input_guardrails", "filtro_entrada"],
    "guardrails_salida": ["output_guardrails", "filtro_salida"],
    "derivar_a": ["handoffs", "transferir_a"],
    "temperatura": ["temperature", "creatividad", "variedad"],
    "modelo": ["model"],
}
_NOMBRES_CHAT = {"ver_pasos": ["verbose"]}
_NOMBRES_INTERFAZ = {
    "titulo": ["title"],
    "descripcion": ["description"],
    "ejemplos": ["examples"],
    "mensaje_inicial": ["welcome", "bienvenida"],
    "tema": ["theme", "colores"],
    "compartir": ["share"],
    "opciones_gradio": [],   # avanzado: se pasa tal cual a demo.launch()
}
_ESPECIALES_AGENTE = {
    "model_settings": "Los ajustes del modelo ya vienen listos. Para la temperatura usa temperatura=.",
    "descripcion": "Aquí se llama descripcion_para_agentes= (o especialidad=). "
                   "descripcion= es para el texto de interfaz().",
}


def _slug(texto):
    """'Experta en becas' -> 'experta_en_becas' (sin tildes ni espacios)."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", sin_tildes).strip("_").lower() or "agente"


def _variantes(nombre):
    """limitaciones -> limitacion; herramienta -> herramientas; filtro_entrada -> filtros_entrada."""
    base = _slug(nombre)
    variantes = {base}
    partes = base.split("_")
    for i, parte in enumerate(partes):
        if len(parte) < 3:
            continue
        if parte.endswith("es") and len(parte) > 4:
            otras = [parte[:-2], parte[:-1]]
        elif parte.endswith("s"):
            otras = [parte[:-1]]
        else:
            otras = [parte + "s", parte + "es"]
        for otra in otras:
            variantes.add("_".join(partes[:i] + [otra] + partes[i + 1:]))
    return variantes


def _indice(tabla):
    """{nombre_principal: [sinónimos]} -> {cualquier_forma: nombre_principal}."""
    indice = {}
    for principal, sinonimos in tabla.items():
        for nombre in [principal, *sinonimos]:
            for forma in _variantes(nombre):
                if indice.setdefault(forma, principal) != principal:
                    raise RuntimeError(f"'{forma}' sirve para dos parámetros")
    return indice


_INDICE_AGENTE = _indice(_NOMBRES_AGENTE)
_INDICE_CHAT = _indice(_NOMBRES_CHAT)
_INDICE_INTERFAZ = _indice(_NOMBRES_INTERFAZ)


def _escritos(funcion, valores, otros_nombres):
    """Lo que escribió la alumna: los parámetros que cambió más los otros nombres.

    `valores` son los locals() de la función; un parámetro con su valor por
    defecto cuenta como no escrito.
    """
    escritos = {}
    for nombre, defecto in (funcion.__kwdefaults__ or {}).items():
        valor = valores[nombre]
        if not (valor is defecto or (type(valor) is type(defecto) and valor == defecto)):
            escritos[nombre] = valor
    escritos.update(otros_nombres)
    return escritos


def _resolver(funcion, indice, escritos, especiales=None):
    """Traduce lo que escribió la alumna a los nombres principales.

    Devuelve ({principal: valor}, {principal: nombre_que_escribió}).
    """
    __tracebackhide__ = True
    valores, como = {}, {}
    for clave, valor in escritos.items():
        limpia = _slug(clave)
        principal = indice.get(limpia)
        if principal is None:
            if especiales and limpia in especiales:
                raise ErrorEnTuAgente(f"En {funcion} no se usa {clave}=. {especiales[limpia]}")
            pista = difflib.get_close_matches(limpia, list(indice), n=1, cutoff=0.6)
            raise ErrorEnTuAgente(
                f"{funcion} no tiene {clave}=."
                + (f" ¿Quisiste decir {indice[pista[0]]}=?" if pista else
                   f" Puedes usar: {', '.join(sorted(set(indice.values())))}."))
        if principal in como:
            raise ErrorEnTuAgente(
                f"Escribiste {como[principal]}= y {clave}=, que son lo mismo. Deja solo uno.")
        valores[principal] = valor
        como[principal] = clave
    return valores, como


# --- Conexión ---------------------------------------------------------------

def conectar(key: str = None, modelo: str = None, url: str = None):
    """Elige la key, el modelo o el proveedor de todos los agentes. Es opcional.

    ```python
    conectar(modelo="openai/gpt-4o-mini")
    ```

    Si no la llamas, se conecta sola: usa la key de `OPENROUTER_API_KEY` y el
    modelo Claude Haiku (`anthropic/claude-haiku-5.5`) en OpenRouter.

    - `key`: la key del proveedor. Si no la pones, se lee de `OPENROUTER_API_KEY`.
    - `modelo`: el modelo de los agentes que crees después. Los nombres están
      en openrouter.ai/models. Ej: `"openai/gpt-4o-mini"`
    - `url`: otro proveedor compatible con la API de OpenAI, en vez de
      OpenRouter. Ej: `"https://api.openai.com/v1"`
    """
    __tracebackhide__ = True
    key = key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ErrorEnTuAgente(
            "Falta la key. Ejecuta primero la celda de preparación del comienzo.")
    if modelo is not None:
        if not isinstance(modelo, str) or not modelo.strip():
            raise ErrorEnTuAgente("modelo tiene que ser un texto. Ej: modelo=\"openai/gpt-4o-mini\"")
        _estado["modelo"] = modelo.strip()
    client = AsyncOpenAI(base_url=url or URL_POR_DEFECTO, api_key=key, max_retries=5)
    set_default_openai_client(client)
    set_tracing_disabled(True)
    _estado["client"] = client
    return client


def _modelo(nombre):
    client = _estado["client"] or conectar()
    return OpenAIChatCompletionsModel(model=nombre, openai_client=client)


# --- asyncio sin que la alumna lo vea ---------------------------------------
# Colab ya tiene un event loop corriendo, así que Runner.run_sync falla ahí.
# Corremos todo en un loop propio, en un hilo aparte, y siempre el MISMO loop:
# el cliente de OpenAI guarda conexiones atadas al loop donde se abrieron.

def _correr(coro):
    if _estado["loop"] is None:
        loop = asyncio.new_event_loop()
        threading.Thread(target=loop.run_forever, daemon=True).start()
        _estado["loop"] = loop
    return asyncio.run_coroutine_threadsafe(coro, _estado["loop"]).result()


def _mensaje_error(e):
    """Traduce los errores de conexión a algo que una alumna pueda resolver."""
    if isinstance(e, ErrorEnTuAgente):
        return str(e)
    if isinstance(e, openai.AuthenticationError):
        return "No pude conectarme con el modelo: la key no funciona. Avísale a tu profe."
    if isinstance(e, openai.NotFoundError) or (
            isinstance(e, openai.BadRequestError) and "valid model" in str(e)):
        return ("Ese modelo no existe o no está permitido con esta key. Revisa el nombre, "
                "o quita modelo= para usar el de siempre.")
    if isinstance(e, openai.RateLimitError):
        return "Hay muchas consultas al mismo tiempo. Espera un minuto y vuelve a intentar."
    if isinstance(e, openai.APIConnectionError):
        return "No hay conexión con el modelo. Revisa tu internet y vuelve a intentar."
    if isinstance(e, MaxTurnsExceeded):
        return ("El agente dio demasiadas vueltas usando herramientas sin terminar. "
                "Revisa que tus herramientas devuelvan algo útil.")
    return f"Ocurrió un error inesperado ({type(e).__name__}). Intenta de nuevo."


# --- Habilidades (las mismas de utilidades.py) ------------------------------

def _portada(carpeta, habilidad):
    """Lee nombre y descripción del frontmatter de SKILL.md."""
    nombre, desc = habilidad, "Descripción no disponible"
    try:
        texto = (carpeta / habilidad / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return f"- {nombre}: {desc}"
    partes = texto.split("---", 2)
    cabecera = partes[1] if len(partes) >= 3 else texto
    for linea in cabecera.splitlines():
        if ":" in linea:
            clave, valor = (x.strip() for x in linea.split(":", 1))
            if clave.lower() in ("name", "nombre", "title"):
                nombre = valor
            elif "desc" in clave.lower():
                desc = valor
    return f"- {nombre}: {desc}"


def _herramientas_habilidades(carpeta):
    @_function_tool_sdk
    def obtener_habilidad(habilidad: str) -> str:
        """Retorna las instrucciones de la habilidad de nombre `habilidad`.

        Args:
            habilidad: nombre de la habilidad a usar.
        """
        return (carpeta / habilidad / "SKILL.md").read_text(encoding="utf-8").strip()

    @_function_tool_sdk
    def profundizar_habilidad(habilidad: str, ruta: str) -> str:
        """Retorna el archivo `ruta` dentro de la habilidad `habilidad`.

        Args:
            habilidad: nombre de la habilidad.
            ruta: archivo a leer, por ejemplo "referencias/ejemplos.md".
        """
        return (carpeta / habilidad / ruta).read_text(encoding="utf-8").strip()

    return [obtener_habilidad, profundizar_habilidad]


def _revisar_habilidades(habilidades, carpeta_habilidades, como="habilidades"):
    __tracebackhide__ = True
    carpeta = Path(carpeta_habilidades).resolve()   # fija la ruta: un os.chdir después no la rompe
    if not carpeta.is_dir():
        raise ErrorEnTuAgente(
            f"No existe la carpeta '{carpeta_habilidades}' (busqué en {carpeta}). "
            "Si tus habilidades están en Drive, monta Drive y escribe la ruta completa: "
            "carpeta_habilidades='/content/drive/MyDrive/mi-proyecto/SKILLS'")
    hay = sorted(p.name for p in carpeta.iterdir() if (p / "SKILL.md").exists())
    for h in habilidades:
        if not isinstance(h, str):
            ejemplo = hay[0] if hay else "mi-habilidad"
            raise ErrorEnTuAgente(f"{como} recibe nombres entre comillas, como ['{ejemplo}'].")
        if h not in hay:
            pista = difflib.get_close_matches(h, hay, n=1)
            raise ErrorEnTuAgente(
                f"No encontré la habilidad '{h}' en {carpeta_habilidades}."
                + (f" ¿Quisiste decir '{pista[0]}'?" if pista else "")
                + f" Las que hay son: {', '.join(hay) or '(ninguna)'}.")
    return carpeta


# --- Herramientas -------------------------------------------------------------

def herramienta(funcion):
    """Convierte tu función en una herramienta que el agente puede usar.

    ```python
    @herramienta
    def calcular_tiempo(horas_libres: int, materias: int) -> str:
        \"\"\"Reparte las horas libres de la semana entre las materias.\"\"\"
        return f"{horas_libres / materias} horas por materia"
    ```

    - Va justo arriba del `def`, con `@`.
    - El agente lee el docstring (el texto entre comillas triples) para saber
      para qué sirve la herramienta.
    - Los tipos (`int`, `str`) le dicen qué datos pasarle.

    También se puede escribir `@function_tool`, como en el SDK.
    """
    __tracebackhide__ = True
    if isinstance(funcion, FunctionTool):
        return funcion
    if not callable(funcion):
        raise ErrorEnTuAgente("@herramienta va justo arriba de un def.")
    nombre = funcion.__name__
    if not (funcion.__doc__ or "").strip():
        print(f"⚠️  '{nombre}' no tiene docstring: el agente no va a saber para qué sirve. "
              'Agrégale una línea con """...""" debajo del def.')
    sin_tipo = [p for p in inspect.signature(funcion).parameters.values()
                if p.annotation is inspect.Parameter.empty]
    if sin_tipo:
        nombres = ", ".join(p.name for p in sin_tipo)
        sujeto = f"al parámetro {nombres} le falta" if len(sin_tipo) == 1 else \
                 f"a los parámetros {nombres} les falta"
        print(f"⚠️  En '{nombre}', {sujeto} el tipo "
              f"(por ejemplo {sin_tipo[0].name}: int o {sin_tipo[0].name}: str).")
    return _function_tool_sdk(funcion)


function_tool = herramienta   # el nombre del SDK, con los mismos avisos


def _a_herramienta(t, como="herramientas"):
    """Función, @herramienta o agente: todo entra a la misma lista."""
    __tracebackhide__ = True
    if isinstance(t, FunctionTool):
        if not t.description.strip():
            print(f"⚠️  '{t.name}' no tiene docstring: el agente no va a saber para qué sirve.")
        return t
    if isinstance(t, Agent):
        return t.as_tool(tool_name=_slug(t.name),
                         tool_description=t.handoff_description or f"Agente {t.name}")
    if isinstance(t, str) and t.isidentifier():
        raise ErrorEnTuAgente(
            f"En {como} pusiste '{t}' entre comillas. Escríbela sin comillas: {como}=[{t}]")
    if callable(t):
        return herramienta(t)
    raise ErrorEnTuAgente(
        f"En {como} va el nombre de la función, sin (). "
        f"Ejemplo: {como}=[calcular_tiempo], no {como}=[calcular_tiempo()].")


# --- Guardrails ---------------------------------------------------------------

def _pasar_guardrails(guardrails, texto):
    """Usa los guardrails tal como se escriben en la clase 07: texto -> (bool, str).

    Devuelve (ok, texto_final, quien_bloqueo). Aceptan async (como el
    clasificador semántico) y también un True/False solo.
    """
    __tracebackhide__ = True
    for guardrail in guardrails:
        nombre = getattr(guardrail, "__name__", "tu guardrail")
        respuesta = guardrail(texto)
        if asyncio.iscoroutine(respuesta):
            respuesta = _correr(respuesta)
        if respuesta is None:
            raise ErrorEnTuAgente(
                f"'{nombre}' no devolvió nada. ¿Te faltó el return True, \"\" del final?")
        if isinstance(respuesta, bool):
            respuesta = (respuesta, "No puedo ayudarte con eso.")
        if not (isinstance(respuesta, tuple) and len(respuesta) == 2
                and isinstance(respuesta[0], bool)):
            raise ErrorEnTuAgente(
                f"'{nombre}' tiene que devolver (True, \"\") si está todo bien, "
                f"o (False, \"mensaje\") si hay que bloquear. Devolvió: {respuesta!r}")
        ok, alternativo = respuesta
        if not ok:
            return False, alternativo, nombre
    return True, texto, None


# --- El agente --------------------------------------------------------------

def reporte_interaccion(resultado):
    """Qué herramientas llamó el agente y con qué datos (igual que utilidades.py)."""
    lineas = []
    for item in resultado.new_items:
        if item.type == "tool_call_item":
            lineas.append(f"🔧 {item.raw_item.name}({item.raw_item.arguments})")
        elif item.type == "tool_call_output_item":
            lineas.append(f"   📤 {str(item.output)[:200]}")
        elif item.type == "handoff_output_item":
            lineas.append(f"🔀 pasó la conversación a {item.target_agent.name}")
    return "\n".join(lineas) or "(no usó herramientas)"


class Agente(Agent):
    """Tu agente. Se crea con `crear_agente(...)`.

    ```python
    tutor.chat("hola")                           # conversa y muestra la respuesta
    respuesta = tutor.obtener_respuesta("hola")  # te entrega el texto
    tutor.borrar_memoria()                       # empieza de cero (con memoria=True)
    tutor.ver_instrucciones()                    # el texto que lee el modelo
    ```

    ### Otros nombres que funcionan igual
    - `obtener_respuesta()`: `responder()`, `respond()`
    - `borrar_memoria()`: `olvidar()`, `clear_memory()`
    - `ver_instrucciones()`: `show_instructions()`

    Por dentro es un `Agent` del OpenAI Agents SDK, así que
    `Runner.run(tutor, "hola")` también funciona.
    """

    def _turno(self, mensaje, historial=()):
        """Uso interno: devuelve (texto, historial_nuevo, resultado, avisos)."""
        __tracebackhide__ = True
        if not isinstance(mensaje, str):
            raise ErrorEnTuAgente("El mensaje tiene que ir entre comillas: tutor.chat(\"hola\")")
        ok, texto, quien = _pasar_guardrails(getattr(self, "_entrada", []), mensaje)
        if not ok:
            return texto, list(historial), None, [f"🛡️ {quien} bloqueó el mensaje"]
        previo = list(historial) if getattr(self, "_memoria", False) else []
        try:
            resultado = _correr(Runner.run(self, previo + [{"role": "user", "content": mensaje}]))
        except (openai.APIError, MaxTurnsExceeded) as e:
            raise ErrorEnTuAgente(_mensaje_error(e)) from None
        ok, texto, quien = _pasar_guardrails(getattr(self, "_salida", []), resultado.final_output)
        avisos = [] if ok else [f"🛡️ {quien} cambió la respuesta"]
        return texto, resultado.to_input_list(), resultado, avisos

    def obtener_respuesta(self, mensaje: str) -> str:
        """Le escribe al agente y te entrega la respuesta, sin mostrarla.

        ```python
        respuesta = clasificador.obtener_respuesta("¿Cómo sumo fracciones?")
        if "INVÁLIDO" in respuesta:
            print("Está fuera de tema")
        ```

        Sirve para guardar la respuesta en una variable o revisarla en tu
        código (por ejemplo, dentro de un guardrail). Para conversar, usa `chat()`.

        También se llama `responder()` o `respond()`.
        """
        __tracebackhide__ = True
        texto, self._historial, self.ultimo, self._avisos = self._turno(
            mensaje, getattr(self, "_historial", []))
        return texto

    responder = obtener_respuesta
    respond = obtener_respuesta

    def chat(self, mensaje: str = None, *, ver_pasos: bool = False, **otros_nombres):
        """Le escribe un mensaje al agente y muestra su respuesta.

        ```python
        tutor.chat("¿Me ayudas con 3/4 + 1/2?")
        tutor.chat("Tengo 6 horas y 3 materias", ver_pasos=True)
        ```

        - `mensaje`: lo que le quieres decir, entre comillas.
        - `ver_pasos`: `True` para ver qué herramientas usó, con qué datos, y si
          un guardrail bloqueó algo. También se llama `verbose`.

        La respuesta se muestra debajo de la celda. Para guardarla en una
        variable, usa `obtener_respuesta()`.
        """
        __tracebackhide__ = True
        p, _ = _resolver("chat", _INDICE_CHAT, _escritos(Agente.chat, locals(), otros_nombres))
        if mensaje is None:
            raise ErrorEnTuAgente("Falta el mensaje: tutor.chat(\"hola\")")
        texto = self.obtener_respuesta(mensaje)
        if p.get("ver_pasos", False):
            pasos = self._avisos + ([reporte_interaccion(self.ultimo)] if self.ultimo else [])
            print("\n".join(pasos), "\n")
        print(texto)

    def borrar_memoria(self) -> None:
        """Borra lo que el agente recuerda de la conversación: empieza de cero.

        Solo cambia algo si el agente tiene `memoria=True`. No toca los archivos
        JSON de tus herramientas, ni las conversaciones de `interfaz()` (ahí se
        usa el basurero 🗑️).

        También se llama `olvidar()` o `clear_memory()`.
        """
        self._historial = []
        print("✓ Memoria de la conversación borrada")

    olvidar = borrar_memoria
    clear_memory = borrar_memoria

    def ver_instrucciones(self) -> None:
        """Muestra el texto completo que lee el modelo, armado con tu ficha.

        También se llama `show_instructions()`.
        """
        print(self.instructions)

    show_instructions = ver_instrucciones

    @property
    def nombre(self) -> str:
        """El nombre del agente."""
        return self.name

    def __dir__(self):
        # Lo que aparece al escribir tutor. + Tab: solo los nombres principales.
        return ["chat", "obtener_respuesta", "borrar_memoria", "ver_instrucciones", "nombre"]

    def __repr__(self):
        return f"<Agente '{self.name}'. Escríbele con .chat(\"hola\")>"


Agente.__signature__ = inspect.Signature()   # que Agente? no muestre los 16 parámetros del SDK


# --- interfaz -----------------------------------------------------------------

def interfaz(agente: "Agente" = None, *, titulo: str = None, descripcion: str = None,
             ejemplos: list = None, mensaje_inicial: str = None, tema: str = "Soft",
             compartir: bool = True, **otros_nombres):
    """Abre una página de chat para conversar con tu agente y compartirla.

    ```python
    interfaz(tutor, ejemplos=["¿Cómo sumo fracciones?"],
             mensaje_inicial="¡Hola! ¿En qué tarea estás?")
    ```

    Todo es opcional, menos el agente:

    - `titulo`: título del chat. Si no lo pones, usa el nombre del agente.
    - `descripcion`: texto corto bajo el título. Ej: `"Te ayudo con tus tareas."`
    - `ejemplos`: preguntas que aparecen como botones. Ej: `["¿Cómo sumo fracciones?"]`
    - `mensaje_inicial`: lo primero que dice el agente. Ej: `"¡Hola! ¿En qué te ayudo?"`
    - `tema`: los colores. Ej: `"Soft"`, `"Glass"`, `"Ocean"`, `"Monochrome"`
    - `compartir`: `True` (viene así) crea un link para abrir el chat desde otro
      computador o el celular.

    Cada persona que abre el link tiene su propia conversación.

    ### Otros nombres que funcionan igual
    - `interfaz()`: `abrir_chat()`, `interface()`
    - `titulo`: `title`
    - `descripcion`: `description`
    - `ejemplos`: `examples`
    - `mensaje_inicial`: `bienvenida`, `welcome`
    - `tema`: `colores`, `theme`
    - `compartir`: `share`
    """
    __tracebackhide__ = True
    import gradio as gr

    p, como = _resolver("interfaz", _INDICE_INTERFAZ, _escritos(interfaz, locals(), otros_nombres))
    if not isinstance(agente, Agente):
        raise ErrorEnTuAgente("interfaz recibe un agente creado con crear_agente. "
                              "Ejemplo: interfaz(tutor)")
    tema = p.get("tema", "Soft")
    temas = {t.lower(): t for t in dir(gr.themes)
             if t[0].isupper() and isinstance(getattr(gr.themes, t), type)
             and issubclass(getattr(gr.themes, t), gr.themes.Base)}
    if not isinstance(tema, str) or tema.lower() not in temas:
        raise ErrorEnTuAgente(f"No existe el {como.get('tema', 'tema')} {tema!r}. Puedes usar: "
                              + ", ".join(sorted(v for k, v in temas.items() if k != "base")))
    if not getattr(agente, "_memoria", False):
        print("ℹ️  Tu agente no tiene memoria=True: en el chat no va a recordar "
              "los mensajes anteriores.")

    # Una memoria por persona que abre el link (la versión con `global
    # memoria` mezcla las conversaciones de todas).
    memorias = {}

    def responder(mensaje, historial, request: gr.Request):
        clave = getattr(request, "session_hash", None) or "local"
        # Conversación nueva o basurero 🗑️: todavía no hay mensajes de la usuaria
        if not any(isinstance(m, dict) and m.get("role") == "user" for m in historial):
            memorias[clave] = []
        try:
            texto, memorias[clave], _, _ = agente._turno(mensaje, memorias.get(clave, []))
        except Exception as e:
            print("Error:", type(e).__name__, "-", e)
            return _mensaje_error(e)
        return texto

    chatbot = None
    if p.get("mensaje_inicial"):
        chatbot = gr.Chatbot(value=[{"role": "assistant", "content": p["mensaje_inicial"]}])
    demo = gr.ChatInterface(fn=responder, title=p.get("titulo") or agente.name,
                            description=p.get("descripcion") or agente.handoff_description,
                            examples=_como_lista(p.get("ejemplos")) or None, chatbot=chatbot)
    return demo.launch(share=p.get("compartir", True),
                       theme=getattr(gr.themes, temas[tema.lower()])(),
                       **(p.get("opciones_gradio") or {}))


abrir_chat = interfaz
interface = interfaz


# --- crear_agente ---------------------------------------------------------------

def _como_lista(x):
    if x is None:
        return []
    return list(x) if isinstance(x, (list, tuple, set)) else [x]


def _texto(valor, campo):
    """tono y audiencia: un texto, o una lista que se une con comas."""
    __tracebackhide__ = True
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v) for v in valor)
    if not isinstance(valor, str):
        raise ErrorEnTuAgente(f"{campo} tiene que ser un texto entre comillas. "
                              f"Ej: {campo}=\"Cercano y paciente\"")
    return valor.strip()


def _armar_instrucciones(nombre, instrucciones, tono, audiencia, limitaciones):
    """La ficha de identidad de la clase 3, con las secciones de la plantilla del curso."""
    partes = []
    if nombre != "Mi agente":
        partes.append(f"# Nombre\nTu nombre es {nombre}. Es tu nombre como agente, "
                      "no el de la persona que te escribe.")
    partes.append(f"# Propósito\n{instrucciones}")
    if tono:
        partes.append(f"# Tono e identidad\n{tono}")
    if audiencia:
        partes.append(f"# Audiencia\n{audiencia}")
    if limitaciones:
        partes.append("# Limitaciones\n" + "\n".join(f"- {l}" for l in limitaciones))
    return "\n\n".join(partes)


def crear_agente(instrucciones: str = None, *, nombre: str = "Mi agente", tono: str = None,
                 audiencia: str = None, limitaciones: list = None, herramientas: list = None,
                 habilidades: list = None, memoria: bool = False, guardrails_entrada=None,
                 guardrails_salida=None, derivar_a: list = None,
                 descripcion_para_agentes: str = None, temperatura: float = None,
                 carpeta_habilidades: str = "SKILLS", modelo: str = None, **otros_nombres):
    """Crea un agente nuevo. Solo las instrucciones son obligatorias.

    ```python
    tutor = crear_agente("Ayudar con tareas de matemáticas", nombre="Tutor")
    tutor.chat("¿Cuánto es 3/4 + 1/2?")
    ```

    Las instrucciones van primero, sin nombre. Lo demás se escribe con su
    nombre (`nombre="..."`) y se va sumando clase a clase.

    ### Lo que lee tu agente
    - `instrucciones`: qué tiene que hacer. Ej: `"Ayudar con tareas"`
    - `nombre`: cómo se llama. Ej: `"Tutor Socrático"`
    - `tono`: cómo habla. Ej: `"Cercano y paciente"`
    - `audiencia`: con quién habla. Ej: `"Estudiantes de 14 a 18 años"`
    - `limitaciones`: lo que NO debe hacer. Ej: `["Solo temas escolares"]`.
      El modelo se las puede saltar; para bloquear siempre, usa guardrails.

    Todo eso se junta en un solo texto: míralo con `tutor.ver_instrucciones()`.

    ### Lo que puede hacer
    - `herramientas`: funciones (o agentes) que puede usar. Ej: `[calcular_tiempo]`
    - `habilidades`: carpetas dentro de `SKILLS`. Ej: `["tutor-socratico"]`
    - `carpeta_habilidades`: dónde están las habilidades. Por defecto `"SKILLS"`
    - `derivar_a`: agentes a los que les puede pasar la conversación. Ej: `[experta]`
    - `descripcion_para_agentes`: para qué sirve, en una frase. No la lee este
      agente: la leen los otros, para saber cuándo llamarlo.

    ### Controles (el modelo no los lee)
    - `memoria`: `True` para que recuerde la conversación mientras el notebook
      está abierto (no la guarda en un archivo).
    - `guardrails_entrada`: funciones que revisan el mensaje antes de responder.
      Devuelven `(True, "")` o `(False, "aviso")`. Ej: `validar_entrada`
    - `guardrails_salida`: lo mismo, pero revisan la respuesta.
    - `temperatura`: de 0 a 1. Con 0 responde casi siempre igual. Ej: `0.2`
    - `modelo`: otro modelo para este agente. Por defecto, Claude Haiku
      (`anthropic/claude-haiku-5.5`) o el que se eligió con `conectar()`.

    ### Otros nombres que funcionan igual
    - `instrucciones`: `instructions`, `proposito`
    - `nombre`: `name`
    - `tono`: `personalidad`, `tone`
    - `audiencia`: `publico_objetivo`, `audience`
    - `limitaciones`: `reglas`, `rules`
    - `herramientas`: `tools`
    - `habilidades`: `recetas`, `skills`
    - `carpeta_habilidades`: `carpeta_recetas`, `skills_folder`
    - `derivar_a`: `transferir_a`, `handoffs`
    - `descripcion_para_agentes`: `especialidad`, `cuando_usarme`, `handoff_description`
    - `memoria`: `recordar`, `memoria_de_sesion`, `memory`
    - `guardrails_entrada`: `filtro_entrada`, `input_guardrails`
    - `guardrails_salida`: `filtro_salida`, `output_guardrails`
    - `temperatura`: `creatividad`, `variedad`, `temperature`
    - `modelo`: `model`

    Valen con o sin tilde y en singular o plural.
    """
    __tracebackhide__ = True
    p, como = _resolver("crear_agente", _INDICE_AGENTE,
                        _escritos(crear_agente, locals(), otros_nombres), _ESPECIALES_AGENTE)
    if instrucciones is not None:
        if "instrucciones" in p:
            raise ErrorEnTuAgente(
                f"Escribiste las instrucciones dos veces (al principio y con "
                f"{como['instrucciones']}=). Deja solo una.")
        p["instrucciones"] = instrucciones
        como["instrucciones"] = "instrucciones"

    def nombre_de(campo):
        return como.get(campo, campo)

    texto_principal = p.get("instrucciones")
    if not isinstance(texto_principal, str) or not texto_principal.strip():
        raise ErrorEnTuAgente(
            "Faltan las instrucciones: qué tiene que hacer tu agente, entre comillas. "
            "Ej: crear_agente(\"Ayudar con tareas de matemáticas\")")
    texto_principal = texto_principal.strip()
    nombre = p.get("nombre", "Mi agente")
    if not isinstance(nombre, str) or not nombre.strip():
        raise ErrorEnTuAgente(f"{nombre_de('nombre')} tiene que ser un texto. Ej: nombre=\"Tutor\"")
    nombre = nombre.strip()
    memoria = p.get("memoria", False)
    if not isinstance(memoria, bool):
        raise ErrorEnTuAgente(f"{nombre_de('memoria')} tiene que ser True o False "
                              f"(sin comillas), no {memoria!r}.")
    t = p.get("temperatura")
    if t is not None and (isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 1):
        raise ErrorEnTuAgente(f"{nombre_de('temperatura')} va de 0 a 1 (por ejemplo 0.2), no {t!r}.")

    limitaciones = [_texto(l, nombre_de("limitaciones")) for l in _como_lista(p.get("limitaciones"))]
    tono = _texto(p.get("tono"), nombre_de("tono"))
    audiencia = _texto(p.get("audiencia"), nombre_de("audiencia"))
    texto = _armar_instrucciones(nombre, texto_principal, tono, audiencia, limitaciones)

    tools = [_a_herramienta(h, nombre_de("herramientas")) for h in _como_lista(p.get("herramientas"))]

    for campo in ("guardrails_entrada", "guardrails_salida"):
        for g in _como_lista(p.get(campo)):
            if isinstance(g, (InputGuardrail, OutputGuardrail)):
                raise ErrorEnTuAgente(
                    f"En {nombre_de(campo)} pusiste un guardrail con el formato del SDK "
                    "(@input_guardrail / @output_guardrail). En el curso son funciones "
                    "normales que devuelven (True, \"\") o (False, \"mensaje\").")
            if not callable(g):
                raise ErrorEnTuAgente(
                    f"En {nombre_de(campo)} va el nombre de la función, sin (). "
                    f"Ejemplo: {nombre_de(campo)}=validar_entrada")

    derivar = _como_lista(p.get("derivar_a"))
    for d in derivar:
        if not isinstance(d, Agent):
            raise ErrorEnTuAgente(
                f"{nombre_de('derivar_a')} recibe agentes creados con crear_agente "
                f"(sin comillas), no {d!r}. Ej: {nombre_de('derivar_a')}=[experta]")

    habilidades = _como_lista(p.get("habilidades"))
    if habilidades:
        carpeta = _revisar_habilidades(habilidades, p.get("carpeta_habilidades", "SKILLS"),
                                       nombre_de("habilidades"))
        portadas = "\n".join(_portada(carpeta, h) for h in habilidades)
        texto += ("\n\n# Habilidades\n\nUsa `obtener_habilidad` cuando el caso lo amerite "
                  f"y `profundizar_habilidad` para leer sus archivos.\n\n{portadas}")
        tools += _herramientas_habilidades(carpeta)

    nombres = [h.name for h in tools]
    repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
    if repetidos:
        raise ErrorEnTuAgente(
            f"Hay dos herramientas que se llaman '{repetidos[0]}'. Si son agentes, "
            "ponle un nombre distinto a cada uno con nombre=\"...\".")

    descripcion = _texto(p.get("descripcion_para_agentes"), nombre_de("descripcion_para_agentes"))
    if not descripcion:
        descripcion = texto_principal.splitlines()[0][:200]

    modelo = p.get("modelo", _estado["modelo"])
    if not isinstance(modelo, str) or not modelo.strip():
        raise ErrorEnTuAgente(f"{nombre_de('modelo')} tiene que ser un texto. "
                              "Ej: modelo=\"openai/gpt-4o-mini\"")
    modelo = modelo.strip()
    ajustes = {"cache_control": {"type": "ephemeral"}} if modelo.startswith("anthropic/") else None

    agente = Agente(
        name=nombre,
        handoff_description=descripcion,
        instructions=texto,
        model=_modelo(modelo),
        model_settings=ModelSettings(
            temperature=t,
            max_tokens=2048,
            extra_body=ajustes,   # caché de Anthropic: abarata repetir las instrucciones
        ),
        tools=tools,
        handoffs=derivar,
    )
    agente._memoria = memoria
    agente._entrada = _como_lista(p.get("guardrails_entrada"))
    agente._salida = _como_lista(p.get("guardrails_salida"))
    return agente
