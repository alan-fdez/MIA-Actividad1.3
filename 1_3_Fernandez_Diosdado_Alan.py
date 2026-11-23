import os
import re
import emoji
from collections import Counter
from datetime import datetime, timezone
from dotenv import load_dotenv
from atproto import Client, models
from pymongo import MongoClient
from groq import Groq
from bson import json_util

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
NOMBRE_SALIDA = "1_3_Fernandez_Diosdado_Alan"


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


def crear_media(tipo, url, miniatura, alt, proporcion):
    return {
        "tipo": tipo,
        "url": url,
        "miniatura": miniatura,
        "alt": alt or "",
        "ancho": proporcion.width if proporcion else None,
        "alto": proporcion.height if proporcion else None,
    }


def extraer_multimedia(embed):
    if isinstance(embed, models.AppBskyEmbedRecordWithMedia.View):
        return extraer_multimedia(embed.media)
    if isinstance(embed, models.AppBskyEmbedImages.View):
        return [crear_media("imagen", img.fullsize, img.thumb, img.alt, img.aspect_ratio) for img in embed.images]
    if isinstance(embed, models.AppBskyEmbedGallery.View):
        return [crear_media("imagen", img.fullsize, img.thumbnail, img.alt, img.aspect_ratio) for img in embed.items]
    if isinstance(embed, models.AppBskyEmbedVideo.View):
        return [crear_media("video", embed.playlist, embed.thumbnail, embed.alt, embed.aspect_ratio)]
    return []


def obtener_feed(cliente, actor, limite):
    respuesta = cliente.get_author_feed(actor=actor, limit=limite, filter="posts_no_replies")
    posts = []
    for elemento in respuesta.feed:
        if elemento.reason is not None:
            continue
        post = elemento.post
        texto_limpio = limpiar_texto(post.record)
        multimedia = extraer_multimedia(post.embed)
        if not texto_limpio and not multimedia:
            continue
        posts.append({
            "uri": post.uri,
            "fecha": post.record.created_at,
            "texto": post.record.text,
            "texto_limpio": texto_limpio,
            "multimedia": multimedia,
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


def describir_multimedia(multimedia):
    if not multimedia:
        return "sin multimedia"
    tipos = Counter(m["tipo"] for m in multimedia)
    descripcion = ", ".join(f"{tipo} x{n}" if n > 1 else tipo for tipo, n in tipos.items())
    alts = [m["alt"] for m in multimedia if m["alt"]]
    if alts:
        descripcion += f" (alt: {' / '.join(alts)})"
    return descripcion


def construir_prompt(actor, posts):
    contexto = (
        "Eres un analista experto en redes sociales y marketing digital. "
        f"A continuación tienes las {len(posts)} publicaciones más recientes del perfil @{actor} "
        "en la red social Bluesky. Cada línea incluye la fecha, las métricas de interacción "
        "(likes, reposts, respuestas y citas), el contenido multimedia adjunto (imágenes o vídeos, "
        "con su texto alternativo si lo tiene) y el texto de la publicación."
    )
    feed = "\n".join(
        f"[{p['fecha'][:10]}] likes={p['likes']} reposts={p['reposts']} "
        f"respuestas={p['respuestas']} citas={p['citas']} | multimedia: {describir_multimedia(p['multimedia'])} "
        f"| {p['texto_limpio'] or '(sin texto)'}"
        for p in posts
    )
    formato = (
        "Redacta en español un informe de análisis del perfil con estas secciones:\n"
        "1. Resumen del perfil\n"
        "2. Temas principales (con un porcentaje aproximado de cada uno)\n"
        "3. Tono y sentimiento general\n"
        "4. Tipo de contenido (promoción, noticias, interacción con la comunidad...) y uso de imágenes y vídeos\n"
        "5. Engagement: qué tipo de publicaciones obtienen más interacción, incluyendo si las que llevan "
        "vídeo o imagen funcionan mejor\n"
        "6. Frecuencia de publicación\n"
        "7. Público objetivo\n"
        "8. Conclusiones y recomendaciones\n"
        "Basa todas las afirmaciones únicamente en los datos proporcionados. "
        "No cites frases literales que no aparezcan en las publicaciones. "
        "No describas lo que muestran las imágenes o vídeos más allá de su texto alternativo, "
        "ya que no puedes verlos. "
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
    return respuesta.choices[0].message.content.replace("**", "")


def guardar_analisis(coleccion, documento_id, analisis):
    with open(f"{NOMBRE_SALIDA}.txt", "w", encoding="utf-8") as fichero:
        fichero.write(analisis)
    coleccion.update_one(
        {"_id": documento_id},
        {"$set": {"analisis": {
            "modelo": MODELO,
            "fecha": datetime.now(timezone.utc),
            "texto": analisis,
        }}},
    )
    documento = coleccion.find_one({"_id": documento_id})
    with open(f"{NOMBRE_SALIDA}.json", "w", encoding="utf-8") as fichero:
        fichero.write(json_util.dumps(documento, indent=2, ensure_ascii=False))
    print(f"Análisis guardado en {NOMBRE_SALIDA}.txt, en MongoDB y en {NOMBRE_SALIDA}.json")


if __name__ == "__main__":
    cliente_bsky = conectar_bluesky()
    posts = obtener_feed(cliente_bsky, PERFIL, NUM_POSTS)
    print(f"Posts obtenidos de @{PERFIL}: {len(posts)}")
    coleccion, documento_id = guardar_feed_mongo(PERFIL, posts)
    analisis = analizar_con_groq(construir_prompt(PERFIL, posts))
    guardar_analisis(coleccion, documento_id, analisis)
