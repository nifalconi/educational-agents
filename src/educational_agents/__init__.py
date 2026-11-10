"""educational_agents: agentes de IA en 2 líneas, para aprender y enseñar.

    from educational_agents import crear_agente, interfaz
    tutor = crear_agente("Ayudar con tareas de matemáticas", nombre="Tutor")
    tutor.chat("¿me ayudas con fracciones?")
    interfaz(tutor)

Cada parámetro acepta varios nombres: en inglés (como el OpenAI Agents SDK),
en español técnico y en español educativo. También valen con o sin tilde y en
singular o plural. La ayuda muestra el nombre técnico (en MAYÚSCULA abajo).

  crear_agente(...)
    Inglés                Técnico                    Educativo          Otros nombres
    instructions          INSTRUCCIONES              -                  proposito
    name                  NOMBRE                     -                  -
    handoff_description   DESCRIPCION_PARA_AGENTES   especialidad       cuando_usarme
    tone                  TONO                       personalidad       -
    audience              AUDIENCIA                  publico_objetivo   -
    rules                 LIMITACIONES               reglas             -
    tools                 HERRAMIENTAS               -                  -
    skills                HABILIDADES                recetas            -
    skills_folder         CARPETA_HABILIDADES        carpeta_recetas    -
    memory                MEMORIA                    recordar           memoria_de_sesion
    input_guardrails      GUARDRAILS_ENTRADA         filtro_entrada     -
    output_guardrails     GUARDRAILS_SALIDA          filtro_salida      -
    handoffs              DERIVAR_A                  transferir_a       -
    temperature           TEMPERATURA                creatividad        variedad
    model                 MODELO                     -                  -

  Con el agente
    chat()                CHAT()                     chat()             -
    respond()             OBTENER_RESPUESTA()        responder()        -
    clear_memory()        BORRAR_MEMORIA()           olvidar()          -
    verbose=True          VER_PASOS=True             -                  -
    show_instructions()   VER_INSTRUCCIONES()        -                  -
    @function_tool        @HERRAMIENTA               -                  -

  interfaz(...)
    interface()           INTERFAZ()                 abrir_chat()       -
    title                 TITULO                     -                  -
    description           DESCRIPCION                -                  -
    examples              EJEMPLOS                   -                  -
    welcome               MENSAJE_INICIAL            bienvenida         -
    theme                 TEMA                       colores            -
    share                 COMPARTIR                  -                  -

Por defecto usa anthropic/claude-haiku-5.5 en OpenRouter. Para cambiarlo:
conectar(modelo="openai/gpt-4o-mini") o crear_agente(..., modelo="...").

Más ayuda: crear_agente?   interfaz?   herramienta?   conectar?   tutor.chat?
"""

from .agentes import (Agente, ErrorEnTuAgente, abrir_chat, conectar, crear_agente,
                      function_tool, herramienta, interface, interfaz, reporte_interaccion)

__version__ = "0.1.0"

__all__ = ["crear_agente", "interfaz", "abrir_chat", "interface", "herramienta",
           "function_tool", "conectar", "reporte_interaccion", "ErrorEnTuAgente", "Agente"]
