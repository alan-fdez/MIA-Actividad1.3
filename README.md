# Bluesky Groq Analyzer

Herramienta en Python que extrae las publicaciones de un perfil de **Bluesky**, limpia su texto, las almacena en **MongoDB** y genera un informe de análisis del perfil mediante un modelo de lenguaje a través de la API de **Groq**.

Proyecto desarrollado para la Actividad 1.3 de la asignatura *Sistemas de Big Data* del Máster en Inteligencia Artificial.

## Características

- **Extracción de datos no estructurados** de Bluesky con el SDK `atproto`: texto, fecha y métricas de interacción (likes, reposts, respuestas y citas) de las publicaciones propias del perfil, excluyendo respuestas y reposts.
- **Limpieza del texto**: eliminación de enlaces (usando las *facets* de Bluesky y una expresión regular de respaldo), emojis y espacios redundantes, conservando también el texto original.
- **Almacenamiento en MongoDB**: un documento por extracción con el perfil, la fecha y todas las publicaciones, lo que permite mantener un historial de análisis.
- **Análisis con LLM**: construcción de un prompt con contexto, publicaciones y formato de respuesta, y generación de un informe en español con 8 secciones (temas, tono, engagement, frecuencia, público objetivo, recomendaciones...).
- **Exportación de resultados**: el informe se guarda en un fichero TXT, se añade al documento de MongoDB y el documento completo se exporta a JSON.

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| [Python 3.12](https://www.python.org/) | Lenguaje del proyecto |
| [uv](https://docs.astral.sh/uv/) | Gestión del entorno virtual y de las dependencias |
| [atproto](https://atproto.blue/) | SDK de Bluesky para Python |
| [Groq](https://console.groq.com/docs) | API de inferencia del modelo de lenguaje (`openai/gpt-oss-120b`) |
| [MongoDB](https://www.mongodb.com/) + [pymongo](https://pymongo.readthedocs.io/) | Almacenamiento de los datos |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Carga de credenciales desde `.env` |
| [emoji](https://pypi.org/project/emoji/) | Eliminación de emojis |
| [pytest](https://docs.pytest.org/) | Pruebas unitarias |

## Requisitos previos

- **Python 3.12** o superior.
- **uv** instalado ([guía de instalación](https://docs.astral.sh/uv/getting-started/installation/)).
- Una instancia de **MongoDB** accesible (local, en Docker o en MongoDB Atlas).
- Una cuenta de **Bluesky** con una **contraseña de aplicación** (*Ajustes > Privacidad y seguridad > Contraseñas de app*).
- Una **API key de Groq**, que se obtiene gratis en [console.groq.com](https://console.groq.com/keys).

## Instalación y configuración

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/alan-fdez/MIA-Actividad1.3.git
   cd MIA-Actividad1.3
   ```

2. **Crear el entorno virtual e instalar las dependencias**

   ```bash
   uv sync
   ```

   `uv sync` crea el entorno virtual `.venv` con Python 3.12 e instala las versiones exactas fijadas en `uv.lock`.

   Alternativa sin uv, usando `requirements.txt`:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # Linux / macOS
   pip install -r requirements.txt
   ```

3. **Configurar las variables de entorno**

   Copia la plantilla y rellénala con tus credenciales:

   ```bash
   cp .env.example .env
   ```

   | Variable | Descripción |
   |---|---|
   | `BSKY_IDENTIFIER` | Handle o email de tu cuenta de Bluesky |
   | `BSKY_PASSWORD` | Contraseña de aplicación de Bluesky |
   | `MONGO_URI` | URL de conexión a tu instancia de MongoDB |
   | `GROQ_API_KEY` | API key de Groq |

   > El fichero `.env` está incluido en `.gitignore` y nunca debe subirse al repositorio.

## Guía de uso

Ejecuta el script principal:

```bash
uv run 1_3_Fernandez_Diosdado_Alan.py
```

Salida esperada:

```
Sesión iniciada en Bluesky como @tu_handle.bsky.social
Posts obtenidos de @playstation.com: 49
Feed guardado en MongoDB con _id 6b04835acd47085f1af1f628
Análisis generado con openai/gpt-oss-120b (4025 tokens)
Análisis guardado en 1_3_Fernandez_Diosdado_Alan.txt, en MongoDB y en 1_3_Fernandez_Diosdado_Alan.json
```

Ficheros generados:

- `1_3_Fernandez_Diosdado_Alan.txt`: informe de análisis generado por el modelo.
- `1_3_Fernandez_Diosdado_Alan.json`: documento de MongoDB completo (perfil, publicaciones y análisis).

Los datos se guardan en la base de datos `bluesky_db`, colección `feeds`.

### Personalización

Las constantes al principio del script permiten adaptar el análisis:

| Constante | Valor por defecto | Descripción |
|---|---|---|
| `PERFIL` | `playstation.com` | Handle del perfil de Bluesky a analizar |
| `NUM_POSTS` | `50` | Número de publicaciones a descargar (máximo 100) |
| `MODELO` | `openai/gpt-oss-120b` | Modelo de Groq utilizado para el análisis |

## Pruebas

El proyecto incluye pruebas unitarias con `pytest` para las funciones de limpieza de texto y construcción del prompt. No requieren conexión a Bluesky, MongoDB ni Groq.

```bash
uv run pytest -v
```

## Estructura del proyecto

```
MIA-Actividad1.3/
├── 1_3_Fernandez_Diosdado_Alan.py     # Script principal
├── 1_3_Fernandez_Diosdado_Alan.txt    # Informe de análisis generado
├── 1_3_Fernandez_Diosdado_Alan.json   # Documento de MongoDB exportado
├── tests/
│   └── test_analizador.py             # Pruebas unitarias
├── .env.example                       # Plantilla de variables de entorno
├── .gitignore
├── .python-version                    # Versión de Python (3.12)
├── pyproject.toml                     # Configuración del proyecto y dependencias
├── uv.lock                            # Versiones exactas de las dependencias
├── requirements.txt                   # Dependencias exportadas para pip
├── LICENSE
└── README.md
```

### Flujo del script

| Función | Descripción |
|---|---|
| `conectar_bluesky()` | Inicia sesión en Bluesky con las credenciales del `.env` |
| `obtener_feed(cliente, actor, limite)` | Descarga las publicaciones propias del perfil y extrae texto, fecha y métricas |
| `limpiar_texto(record)` | Elimina enlaces, emojis y espacios redundantes del texto |
| `guardar_feed_mongo(actor, posts)` | Inserta el feed en MongoDB como un único documento |
| `construir_prompt(actor, posts)` | Genera el prompt: contexto + publicaciones + formato de respuesta |
| `analizar_con_groq(prompt)` | Envía el prompt al modelo de Groq y devuelve el análisis |
| `guardar_analisis(coleccion, documento_id, analisis)` | Guarda el análisis en TXT, lo añade al documento de MongoDB y lo exporta a JSON |

### Estructura del documento en MongoDB

```json
{
  "_id": "ObjectId",
  "perfil": "playstation.com",
  "fecha_extraccion": "ISODate",
  "num_posts": 49,
  "posts": [
    {
      "uri": "at://did:plc:.../app.bsky.feed.post/...",
      "fecha": "2026-11-23T15:01:32.949Z",
      "texto": "Texto original de la publicación",
      "texto_limpio": "Texto tras la limpieza",
      "likes": 28,
      "reposts": 0,
      "respuestas": 9,
      "citas": 1
    }
  ],
  "analisis": {
    "modelo": "openai/gpt-oss-120b",
    "fecha": "ISODate",
    "texto": "Informe generado por el modelo"
  }
}
```

## Cómo contribuir

1. Haz un *fork* del repositorio.
2. Crea una rama para tu cambio: `git checkout -b feat/nueva-funcionalidad`.
3. Realiza tus cambios siguiendo [Conventional Commits](https://www.conventionalcommits.org/es/) (`feat:`, `fix:`, `docs:`, `test:`...).
4. Comprueba que las pruebas pasan: `uv run pytest`.
5. Sube la rama y abre un *Pull Request* describiendo el cambio.

## Autores y agradecimientos

- **Alan Fernández Diosdado** - [@alan-fdez](https://github.com/alan-fdez)

Recursos utilizados:

- [Documentación del SDK atproto para Python](https://atproto.blue/)
- [Documentación de la API de Bluesky](https://docs.bsky.app/)
- [Documentación de la API de Groq](https://console.groq.com/docs)
- [Documentación de pymongo](https://pymongo.readthedocs.io/)

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta el fichero [LICENSE](LICENSE) para más detalles.
