"""Pruebas sin conexión: no llaman al modelo (usan una key falsa)."""
import os
import re
from pathlib import Path

os.environ["OPENROUTER_API_KEY"] = "sk-or-falsa-para-pruebas"

import gradio as gr
import pytest
from agents import GuardrailFunctionOutput, input_guardrail

import ninaspro
from ninaspro import (ErrorEnTuAgente, abrir_chat, crear_agente, function_tool, herramienta,
                      interface, interfaz)
from ninaspro import agentes as n

RAIZ = Path(__file__).resolve().parent.parent
SKILLS = Path(__file__).resolve().parent / "SKILLS"


@herramienta
def calcular(a: int, b: int) -> int:
    """Suma dos números."""
    return a + b


def validar(mensaje):
    return True, ""


def error_de(funcion):
    with pytest.raises(ErrorEnTuAgente) as e:
        funcion()
    return str(e.value)


experta = crear_agente("Orientar sobre becas", nombre="Experta")

# Cada nombre que se puede escribir -> (parámetro principal, valor de prueba)
SINONIMOS = {
    "instructions": ("instrucciones", "Ayudar"), "proposito": ("instrucciones", "Ayudar"),
    "propósito": ("instrucciones", "Ayudar"),
    "name": ("nombre", "Tuti"),
    "handoff_description": ("descripcion_para_agentes", "Becas"),
    "especialidad": ("descripcion_para_agentes", "Becas"),
    "cuando_usarme": ("descripcion_para_agentes", "Becas"),
    "descripción_para_agentes": ("descripcion_para_agentes", "Becas"),
    "tone": ("tono", "Cercano"), "personalidad": ("tono", "Cercano"),
    "audience": ("audiencia", "Teens"), "publico_objetivo": ("audiencia", "Teens"),
    "público_objetivo": ("audiencia", "Teens"),
    "rules": ("limitaciones", "Solo escolar"), "reglas": ("limitaciones", "Solo escolar"),
    "limitación": ("limitaciones", "Solo escolar"), "regla": ("limitaciones", "Solo escolar"),
    "tools": ("herramientas", [calcular]), "herramienta": ("herramientas", [calcular]),
    "skills": ("habilidades", ["x"]), "recetas": ("habilidades", ["x"]),
    "skills_folder": ("carpeta_habilidades", "S"), "carpeta_recetas": ("carpeta_habilidades", "S"),
    "memory": ("memoria", True), "recordar": ("memoria", True),
    "memoria_de_sesion": ("memoria", True), "memoria_de_sesión": ("memoria", True),
    "input_guardrails": ("guardrails_entrada", validar),
    "filtro_entrada": ("guardrails_entrada", validar),
    "filtros_entrada": ("guardrails_entrada", validar),
    "guardrail_entrada": ("guardrails_entrada", validar),
    "output_guardrails": ("guardrails_salida", validar),
    "filtro_salida": ("guardrails_salida", validar),
    "handoffs": ("derivar_a", [experta]), "transferir_a": ("derivar_a", [experta]),
    "temperature": ("temperatura", 0.3), "creatividad": ("temperatura", 0.3),
    "variedad": ("temperatura", 0.3), "Temperatura": ("temperatura", 0.3),
}


@pytest.mark.parametrize("escrito", SINONIMOS)
def test_cada_sinonimo_llega_a_su_parametro(escrito):
    principal, valor = SINONIMOS[escrito]
    p, como = n._resolver("crear_agente", n._INDICE_AGENTE, {escrito: valor})
    assert p == {principal: valor}
    assert como == {principal: escrito}


def test_agente_creado_solo_con_sinonimos():
    a = crear_agente(instructions="Ayudar con tareas", name="Tuti", personalidad="Cercana",
                     publico_objetivo="Teens", reglas=["Solo escolar"], tools=[calcular],
                     recordar=True, filtro_entrada=validar, creatividad=0.4,
                     especialidad="Ayuda con tareas", transferir_a=[experta])
    assert a.name == "Tuti"
    assert a._memoria is True
    assert a.model_settings.temperature == 0.4
    assert a.handoff_description == "Ayuda con tareas"
    assert len(a.handoffs) == 1
    assert "# Tono e identidad\nCercana" in a.instructions
    assert "# Limitaciones\n- Solo escolar" in a.instructions
    assert a._entrada == [validar]


@pytest.mark.parametrize("nombres", [
    {"habilidades": ["tutor-prueba"], "carpeta_habilidades": SKILLS},
    {"recetas": ["tutor-prueba"], "carpeta_recetas": SKILLS},
    {"skills": "tutor-prueba", "skills_folder": SKILLS},
])
def test_habilidades_con_cada_nombre(nombres):
    a = crear_agente("Ayudar", **nombres)
    assert "tutor-prueba" in a.instructions
    assert {"obtener_habilidad", "profundizar_habilidad"} <= {t.name for t in a.tools}


def test_ficha_dice_que_el_nombre_es_del_agente():
    # Con "Te llamas X", el modelo respondía "Te llamas X" a "¿cómo me llamo?"
    a = crear_agente("Ayudar", nombre="Mati")
    assert "Tu nombre es Mati. Es tu nombre como agente" in a.instructions


@pytest.mark.parametrize("crear, esperado", [
    (lambda: crear_agente("x", tono="a", personalidad="b"), "Escribiste tono= y personalidad="),
    (lambda: crear_agente("x", instructions="y"), "dos veces"),
    (lambda: crear_agente("x", limitasiones="y"), "¿Quisiste decir limitaciones=?"),
    (lambda: crear_agente("x", descripcion="y"), "descripcion_para_agentes"),
    (lambda: crear_agente("x", recordar="si"), "recordar tiene que ser True o False"),
    (lambda: crear_agente("x", memoria="no"), "memoria tiene que ser True o False"),
    (lambda: crear_agente("x", creatividad=5), "creatividad va de 0 a 1"),
    (lambda: crear_agente("x", model="gpt"), "ya viene listo"),
    (lambda: crear_agente("Tutor", "Ayudar"), "Solo las instrucciones van sin nombre"),
    (lambda: crear_agente(), "Faltan las instrucciones"),
    (lambda: crear_agente("x", herramientas=["calcular"]), "entre comillas"),
    (lambda: crear_agente("x", herramientas=[3]), "sin ()"),   # lo que queda tras calcular(1, 2)
    (lambda: crear_agente("x", derivar_a=["Experta"]), "recibe agentes"),
    (lambda: crear_agente("x", habilidades=["tutor-pruebaa"], carpeta_habilidades=SKILLS),
     "¿Quisiste decir 'tutor-prueba'?"),
    (lambda: crear_agente("x", habilidades=["a"], carpeta_habilidades="/no/existe"),
     "No existe la carpeta"),
])
def test_errores_en_espanol(crear, esperado):
    assert esperado in error_de(crear)


def test_guardrail_con_formato_del_sdk():
    @input_guardrail
    async def g_sdk(ctx, agent, inp):
        return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)

    assert "formato del SDK" in error_de(lambda: crear_agente("x", input_guardrails=[g_sdk]))


@pytest.mark.parametrize("guardrail, esperado", [
    (lambda m: None, "no devolvió nada"),
    (lambda m: "ok", "tiene que devolver (True"),
])
def test_guardrail_mal_escrito(guardrail, esperado):
    a = crear_agente("x", guardrails_entrada=guardrail)
    assert esperado in error_de(lambda: a.obtener_respuesta("hola"))


def test_guardrail_bloquea_sin_llamar_al_modelo():
    a = crear_agente("x", guardrails_entrada=lambda m: (False, "No puedo ayudarte con eso."))
    assert a.obtener_respuesta("hackear") == "No puedo ayudarte con eso."
    assert a._avisos == ["🛡️ <lambda> bloqueó el mensaje"]


def test_metodos_con_varios_nombres():
    A = n.Agente
    assert A.responder is A.obtener_respuesta and A.respond is A.obtener_respuesta
    assert A.olvidar is A.borrar_memoria and A.clear_memory is A.borrar_memoria
    assert A.show_instructions is A.ver_instrucciones
    assert function_tool is herramienta
    assert interface is interfaz and abrir_chat is interfaz
    p, _ = n._resolver("chat", n._INDICE_CHAT, {"verbose": True})
    assert p == {"ver_pasos": True}


def test_chat_con_true_sin_nombre():
    a = crear_agente("x")
    assert "ver_pasos va con su nombre" in error_de(lambda: a.chat("hola", True))


def test_tab_y_repr_muestran_solo_lo_del_curso():
    a = crear_agente("x", nombre="Tutor")
    assert sorted(dir(a)) == sorted(["chat", "obtener_respuesta", "borrar_memoria",
                                     "ver_instrucciones", "nombre"])
    assert repr(a) == "<Agente 'Tutor'. Escríbele con .chat(\"hola\")>"


@pytest.fixture
def gradio_falso(monkeypatch):
    capturado = {}

    class ChatInterfaceFalso:
        def __init__(self, fn, **kw):
            capturado.update(kw)

        def launch(self, **kw):
            capturado["launch"] = kw

    monkeypatch.setattr(gr, "ChatInterface", ChatInterfaceFalso)
    return capturado


def test_interfaz_con_sinonimos(gradio_falso):
    a = crear_agente("x", memoria=True)
    abrir_chat(a, title="Hola", description="Desc", examples=["x"], bienvenida="¡Hola!",
               colores="ocean", share=False)
    assert gradio_falso["title"] == "Hola"
    assert gradio_falso["description"] == "Desc"
    assert gradio_falso["examples"] == ["x"]
    assert gradio_falso["launch"]["share"] is False
    assert type(gradio_falso["launch"]["theme"]).__name__ == "Ocean"


@pytest.mark.parametrize("llamar, esperado", [
    (lambda a: interfaz(a, tema="Soft", theme="Glass"), "Escribiste tema= y theme="),
    (lambda a: interfaz(a, tema="rosado"), "No existe el tema 'rosado'"),
    (lambda a: interfaz("tutor"), "interfaz recibe un agente"),
])
def test_interfaz_errores(gradio_falso, llamar, esperado):
    a = crear_agente("x")
    assert esperado in error_de(lambda: llamar(a))


TABLAS = [(n._NOMBRES_AGENTE, n.crear_agente), (n._NOMBRES_INTERFAZ, n.interfaz),
          (n._NOMBRES_CHAT, n.Agente.chat)]
NOMBRES_DOCUMENTADOS = [(nombre, funcion) for tabla, funcion in TABLAS
                        for principal, sinonimos in tabla.items() if principal != "opciones_gradio"
                        for nombre in [principal, *sinonimos]]
METODOS = ["obtener_respuesta", "responder", "respond", "borrar_memoria", "olvidar",
           "clear_memory", "ver_instrucciones", "show_instructions", "abrir_chat", "interface"]


@pytest.mark.parametrize("nombre, funcion", NOMBRES_DOCUMENTADOS)
def test_la_documentacion_nombra_cada_sinonimo(nombre, funcion):
    """Si se agrega un nombre en el código, tiene que quedar en los tres lugares de ayuda."""
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert f"`{nombre}`" in readme or f"`{nombre}=" in readme, "falta en el README"
    assert re.search(rf"\b{nombre}\b", ninaspro.__doc__ or "", re.I), "falta en help(ninaspro)"
    assert re.search(rf"\b{nombre}\b", funcion.__doc__ or ""), f"falta en {funcion.__name__}?"


@pytest.mark.parametrize("metodo", METODOS)
def test_readme_nombra_cada_metodo(metodo):
    assert f"`{metodo}()`" in (RAIZ / "README.md").read_text(encoding="utf-8")


def test_ningun_nombre_sirve_para_dos_parametros():
    # _indice() levanta RuntimeError si hay un choque; si cargó, no lo hay.
    assert len(n._INDICE_AGENTE) > 100
