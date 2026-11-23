import os
import re
import emoji
from datetime import datetime, timezone
from dotenv import load_dotenv
from atproto import Client, models
from pymongo import MongoClient
from groq import Groq

load_dotenv()

BSKY_IDENTIFIER = os.getenv("BSKY_IDENTIFIER")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")
MONGO_URI = os.getenv("MONGO_URI")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MONGO_DB = "bluesky_db"
MONGO_COLECCION = "feeds"

PERFIL = "playstation.com"
NUM_POSTS = 50
MODELO = "openai/gpt-oss-120b"


def conectar_bluesky():
    cliente = Client()
    perfil = cliente.login(BSKY_IDENTIFIER, BSKY_PASSWORD)
    print(f"Sesión iniciada en Bluesky como @{perfil.handle}")
    return cliente


def limpiar_texto(record):
    texto = record.text.encode("utf-8")
    enlaces = []
    for faceta in record.facets or []:
        if any(isinstance(f, models.AppBskyRichtextFacet.Link) for f in faceta.features):
            enlaces.append((faceta.index.byte_start, faceta.index.byte_end))
    for inicio, fin in sorted(enlaces, reverse=True):
        texto = texto[:inicio] + texto[fin:]
    texto = texto.decode("utf-8")
    texto = re.sub(r"https?://\S+", "", texto)
    texto = emoji.replace_emoji(texto, replace="")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def obtener_feed(cliente, actor, limite):
    respuesta = cliente.get_author_feed(actor=actor, limit=limite, filter="posts_no_replies")
    posts = []
    for elemento in respuesta.feed:
        if elemento.reason is not None:
            continue
        post = elemento.post
        texto_limpio = limpiar_texto(post.record)
        if not texto_limpio:
            continue
        posts.append({
            "uri": post.uri,
            "fecha": post.record.created_at,
            "texto": post.record.text,
            "texto_limpio": texto_limpio,
            "likes": post.like_count,
            "reposts": post.repost_count,
            "respuestas": post.reply_count,
            "citas": post.quote_count,
        })
    return posts


def guardar_feed_mongo(actor, posts):
    cliente = MongoClient(MONGO_URI)
    coleccion = cliente[MONGO_DB][MONGO_COLECCION]
    documento = {
        "perfil": actor,
        "fecha_extraccion": datetime.now(timezone.utc),
        "num_posts": len(posts),
        "posts": posts,
    }
    resultado = coleccion.insert_one(documento)
    print(f"Feed guardado en MongoDB con _id {resultado.inserted_id}")
    return coleccion, resultado.inserted_id


def construir_prompt(actor, posts):
    contexto = (
        "Eres un analista experto en redes sociales y marketing digital. "
        f"A continuación tienes las {len(posts)} publicaciones más recientes del perfil @{actor} "
        "en la red social Bluesky. Cada línea incluye la fecha, las métricas de interacción "
        "(likes, reposts, respuestas y citas) y el texto de la publicación."
    )
    feed = "\n".join(
        f"[{p['fecha'][:10]}] likes={p['likes']} reposts={p['reposts']} "
        f"respuestas={p['respuestas']} citas={p['citas']} | {p['texto_limpio']}"
        for p in posts
    )
    formato = (
        "Redacta en español un informe de análisis del perfil con estas secciones:\n"
        "1. Resumen del perfil\n"
        "2. Temas principales (con un porcentaje aproximado de cada uno)\n"
        "3. Tono y sentimiento general\n"
        "4. Tipo de contenido (promoción, noticias, interacción con la comunidad...)\n"
        "5. Engagement: qué tipo de publicaciones obtienen más interacción\n"
        "6. Frecuencia de publicación\n"
        "7. Público objetivo\n"
        "8. Conclusiones y recomendaciones\n"
        "Basa todas las afirmaciones únicamente en los datos proporcionados. "
        "Escribe en texto plano, sin formato Markdown, con los títulos de sección en mayúsculas."
    )
    return f"{contexto}\n\nPUBLICACIONES:\n{feed}\n\n{formato}"


def analizar_con_groq(prompt):
    cliente = Groq(api_key=GROQ_API_KEY)
    respuesta = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        max_completion_tokens=8192,
    )
    print(f"Análisis generado con {MODELO} ({respuesta.usage.total_tokens} tokens)")
    return respuesta.choices[0].message.content
