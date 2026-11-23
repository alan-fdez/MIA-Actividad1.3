import os
from dotenv import load_dotenv
from atproto import Client

load_dotenv()

BSKY_IDENTIFIER = os.getenv("BSKY_IDENTIFIER")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

PERFIL = "playstation.com"
NUM_POSTS = 100


def conectar_bluesky():
    cliente = Client()
    perfil = cliente.login(BSKY_IDENTIFIER, BSKY_PASSWORD)
    print(f"Sesión iniciada en Bluesky como @{perfil.handle}")
    return cliente


def obtener_feed(cliente, actor, limite):
    respuesta = cliente.get_author_feed(actor=actor, limit=limite, filter="posts_no_replies")
    posts = []
    for elemento in respuesta.feed:
        if elemento.reason is not None:
            continue
        post = elemento.post
        posts.append({
            "uri": post.uri,
            "fecha": post.record.created_at,
            "texto": post.record.text,
            "likes": post.like_count,
            "reposts": post.repost_count,
            "respuestas": post.reply_count,
            "citas": post.quote_count,
        })
    return posts
