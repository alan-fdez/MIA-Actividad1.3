import os
from dotenv import load_dotenv
from atproto import Client

load_dotenv()

BSKY_IDENTIFIER = os.getenv("BSKY_IDENTIFIER")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")


def conectar_bluesky():
    cliente = Client()
    perfil = cliente.login(BSKY_IDENTIFIER, BSKY_PASSWORD)
    print(f"Sesión iniciada en Bluesky como @{perfil.handle}")
    return cliente
