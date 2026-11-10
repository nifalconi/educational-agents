# Para profes y tutoras

Cómo preparar los notebooks del curso con `ninaspro` y qué hacer cuando algo falla.

## La celda de preparación

Es la primera celda de cada notebook. Las alumnas la ejecutan y no la tocan:

```python
#@title Preparación (ejecútala primero)
!pip install -q git+https://github.com/nifalconi/ninaspro
%env OPENROUTER_API_KEY=sk-or-...
```

- **`#@title`** hace que Colab muestre la celda como un formulario con título. Con doble clic sobre el título se oculta o se muestra el código.
- **Tiene que ejecutarse antes que todo lo demás.** Si no, `from ninaspro import ...` falla, y la ayuda al pasar el mouse no aparece (sale del código ya cargado).
- **No hace falta montar Drive ni cambiar de carpeta** para crear un agente. Solo se necesita Drive si las habilidades o los archivos JSON están ahí.
- Tarda lo que tarda `pip` en instalar `openai-agents` y `gradio` (en Colab, del orden de un minuto).

## La key

- Por ahora va en la celda de preparación con `%env`. Quien abra el notebook la puede ver, así que conviene que tenga un **límite de gasto** en OpenRouter y rotarla al terminar el curso.
- La librería la lee de la variable `OPENROUTER_API_KEY`. Cambiar cómo llega (Secretos de Colab, una casilla para escribirla, o dentro de la librería) no obliga a tocar el resto de los notebooks.
- Si la key no funciona, la alumna ve: *"No pude conectarme con el modelo: la key no funciona. Avísale a tu profe."*
- **Nunca subas la key a este repositorio** ni la pegues en la documentación.

## El modelo

Está fijo en la librería (`anthropic/claude-haiku-5.5` por OpenRouter, que es con el que funciona la key del curso). Si una alumna escribe `model=` o `modelo=`, ve que *"el modelo ya viene listo"*. Para cambiarlo para todo el curso se cambia `MODELO_CURSO` en `src/ninaspro/agentes.py`.

## Actualizar la librería

- Un entorno de ejecución nuevo de Colab instala la versión que esté en GitHub en ese momento.
- En una sesión que ya estaba abierta, la versión vieja sigue cargada. Para forzar la nueva:

  ```python
  !pip install -q --force-reinstall --no-deps git+https://github.com/nifalconi/ninaspro
  ```

  y después **Entorno de ejecución → Reiniciar sesión**, y volver a ejecutar la celda de preparación.
- Un cambio en el repositorio cambia lo que corren las alumnas en la próxima clase. Antes de subirlo, corre las pruebas (`pytest`) y prueba el notebook de ejemplo en un Colab.

## Habilidades (`SKILLS/`)

- `habilidades=["tutor-socratico"]` busca `SKILLS/tutor-socratico/SKILL.md` en la carpeta actual del notebook.
- Si las habilidades están en Drive: montar Drive y pasar la ruta completa, `carpeta_habilidades="/content/drive/MyDrive/mi-proyecto/SKILLS"`. Ya no hace falta `os.chdir`.
- La ruta se fija al crear el agente: un `os.chdir` posterior no rompe las herramientas.

## El `ninaspro.py` de la clase 2

La clase 2 descarga otro archivo que también se llama `ninaspro.py` (repositorio `ninas-pro-agentes`, con `catalogo_gratis()`, `usar_modelos()` y `usar_plan_b()`). Como el módulo tiene el mismo nombre, **no conviene usar los dos en la misma sesión de Colab**: el archivo descargado en la carpeta del notebook tapa a la librería instalada.

## Problemas comunes

| Lo que pasa | Qué hacer |
|---|---|
| `ModuleNotFoundError: No module named 'ninaspro'` | No se ejecutó la celda de preparación. Ejecutarla y repetir. |
| "Falta la key del curso" | Falta la línea `%env OPENROUTER_API_KEY=...` o no se ejecutó. |
| "la key no funciona" | La key está mal copiada, venció o se acabó el saldo. Revisarla en OpenRouter. |
| "Hay muchas consultas al mismo tiempo" | Límite de OpenRouter con todo el curso conectado. Esperar un minuto; la librería ya reintenta sola 5 veces. |
| No aparece la ayuda al pasar el mouse | La celda de preparación no se ejecutó en esta sesión. |
| El chat no recuerda lo anterior | El agente se creó sin `memoria=True`. |
| La memoria en JSON se perdió al otro día | El archivo estaba en `/content`, que Colab borra al reiniciar. Guardarlo en Drive. |
| En la interfaz, dos personas ven datos de la otra | Comparten el mismo archivo JSON de memoria. La memoria de la conversación (`memoria=True`) sí es una por persona. |
| Una alumna copió código de un notebook viejo (`Agent(...)`, `Runner.run`) | Sigue funcionando: el agente es un `Agent` del SDK. Pero `instructions=`, `name=`, `tools=` también se aceptan en `crear_agente`. |

## Qué no hace la librería (a propósito)

- **No escribe la memoria en JSON** (es la lección de la clase 6).
- **No escribe los guardrails** (es la lección de la clase 7). Solo los conecta con el agente.
- **No esconde las herramientas**: las alumnas escriben sus funciones; la librería solo avisa si falta el docstring o los tipos.
