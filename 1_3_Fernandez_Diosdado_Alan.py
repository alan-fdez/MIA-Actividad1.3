import os
import re
import emoji
from dotenv import load_dotenv
from atproto import Client, models

load_dotenv()

BSKY_IDENTIFIER = os.getenv("BSKY_IDENTIFIER")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

PERFIL = "playstation.com"
NUM_POSTS = 50


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
