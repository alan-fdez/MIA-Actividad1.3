import importlib.util
from pathlib import Path
from atproto import models

RUTA_SCRIPT = Path(__file__).resolve().parent.parent / "1_3_Fernandez_Diosdado_Alan.py"
spec = importlib.util.spec_from_file_location("analizador", RUTA_SCRIPT)
analizador = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analizador)


def crear_record(texto, enlaces=()):
    datos = texto.encode("utf-8")
    facetas = []
    for enlace in enlaces:
        inicio = datos.find(enlace.encode("utf-8"))
        facetas.append(models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(byte_start=inicio, byte_end=inicio + len(enlace.encode("utf-8"))),
            features=[models.AppBskyRichtextFacet.Link(uri=f"https://{enlace}")],
        ))
    return models.AppBskyFeedPost.Record(text=texto, created_at="2026-11-23T00:00:00Z", facets=facetas or None)


def test_elimina_enlace_marcado_como_faceta():
    record = crear_record("Out now on PS5: play.st/abc123", ["play.st/abc123"])
    assert analizador.limpiar_texto(record) == "Out now on PS5:"


def test_respeta_posiciones_en_bytes_con_emojis():
    record = crear_record("🎮🔥 New trailer: play.st/xyz now", ["play.st/xyz"])
    assert analizador.limpiar_texto(record) == "New trailer: now"


def test_elimina_url_http_sin_faceta():
    record = crear_record("Read more at https://blog.playstation.com/news today")
    assert analizador.limpiar_texto(record) == "Read more at today"


def test_elimina_emojis_y_normaliza_espacios():
    record = crear_record("  Over 1 billion home runs ⚾💥\n\nNext up:   MLB  ")
    assert analizador.limpiar_texto(record) == "Over 1 billion home runs Next up: MLB"


def test_post_con_solo_enlace_queda_vacio():
    record = crear_record("play.st/solo", ["play.st/solo"])
    assert analizador.limpiar_texto(record) == ""


POSTS = [
    {"fecha": "2026-11-20T23:07:14.280Z", "texto": "GTA VI is here 🎉 play.st/GTAVIPS5",
     "texto_limpio": "GTA VI is here",
     "multimedia": [{"tipo": "video", "url": "https://video.bsky.app/a/playlist.m3u8",
                     "miniatura": "https://video.bsky.app/a/thumbnail.jpg", "alt": "", "ancho": 1920, "alto": 1080}],
     "likes": 103, "reposts": 8, "respuestas": 22, "citas": 0},
    {"fecha": "2026-11-23T15:01:32.949Z", "texto": "Black Friday Deals: play.st/4ePZnW5",
     "texto_limpio": "Black Friday Deals:",
     "multimedia": [{"tipo": "imagen", "url": "https://cdn.bsky.app/img/feed_fullsize/b",
                     "miniatura": "https://cdn.bsky.app/img/feed_thumbnail/b", "alt": "Ends 11/30", "ancho": 1080, "alto": 1080}],
     "likes": 28, "reposts": 0, "respuestas": 9, "citas": 1},
]


def test_prompt_incluye_contexto_del_perfil():
    prompt = analizador.construir_prompt("playstation.com", POSTS)
    assert "@playstation.com" in prompt
    assert "2 publicaciones" in prompt


def test_prompt_incluye_cada_post_con_fecha_y_metricas():
    prompt = analizador.construir_prompt("playstation.com", POSTS)
    assert "[2026-11-20] likes=103 reposts=8 respuestas=22 citas=0 | multimedia: video | GTA VI is here" in prompt
    assert ("[2026-11-23] likes=28 reposts=0 respuestas=9 citas=1 | multimedia: imagen (alt: Ends 11/30) "
            "| Black Friday Deals:") in prompt


def test_prompt_usa_texto_limpio_y_no_el_original():
    prompt = analizador.construir_prompt("playstation.com", POSTS)
    assert "play.st" not in prompt
    assert "🎉" not in prompt


def test_prompt_pide_las_ocho_secciones():
    prompt = analizador.construir_prompt("playstation.com", POSTS)
    secciones = ["Resumen del perfil", "Temas principales", "Tono y sentimiento", "Tipo de contenido",
                 "Engagement", "Frecuencia de publicación", "Público objetivo", "Conclusiones y recomendaciones"]
    for seccion in secciones:
        assert seccion in prompt


def test_prompt_sigue_el_orden_contexto_feed_estadisticas_formato():
    prompt = analizador.construir_prompt("playstation.com", POSTS)
    assert (prompt.index("Eres un analista") < prompt.index("PUBLICACIONES:")
            < prompt.index("ESTADÍSTICAS CALCULADAS:") < prompt.index("Redacta en español"))


def test_calcular_estadisticas():
    estadisticas = analizador.calcular_estadisticas(POSTS)
    assert "Total de publicaciones: 2" in estadisticas
    assert "Periodo: del 2026-11-20 al 2026-11-23 (4 días)" in estadisticas
    assert "Frecuencia media: 0.50 publicaciones al día" in estadisticas
    assert "Publicaciones de tipo 'video': 1, interacciones medias 133.0 (mínimo 133, máximo 133)" in estadisticas
    assert "Publicaciones de tipo 'imagen': 1, interacciones medias 38.0 (mínimo 38, máximo 38)" in estadisticas


PROPORCION_CUADRADA = models.AppBskyEmbedDefs.AspectRatio(width=1080, height=1080)


def test_extrae_imagenes_con_alt_y_proporcion():
    embed = models.AppBskyEmbedImages.View(images=[
        models.AppBskyEmbedImages.ViewImage(alt="Ends 11/30", fullsize="https://img/full", thumb="https://img/thumb",
                                            aspect_ratio=PROPORCION_CUADRADA),
    ])
    assert analizador.extraer_multimedia(embed) == [{
        "tipo": "imagen", "url": "https://img/full", "miniatura": "https://img/thumb",
        "alt": "Ends 11/30", "ancho": 1080, "alto": 1080,
    }]


def test_extrae_todas_las_imagenes_de_una_galeria():
    embed = models.AppBskyEmbedGallery.View(items=[
        models.AppBskyEmbedGallery.ViewImage(alt="", fullsize=f"https://img/{i}", thumbnail=f"https://thumb/{i}",
                                             aspect_ratio=PROPORCION_CUADRADA)
        for i in range(3)
    ])
    multimedia = analizador.extraer_multimedia(embed)
    assert len(multimedia) == 3
    assert [m["miniatura"] for m in multimedia] == ["https://thumb/0", "https://thumb/1", "https://thumb/2"]


def test_extrae_video_sin_alt_ni_proporcion():
    embed = models.AppBskyEmbedVideo.View(cid="bafy", playlist="https://video/playlist.m3u8",
                                          thumbnail="https://video/thumbnail.jpg", alt=None, aspect_ratio=None)
    assert analizador.extraer_multimedia(embed) == [{
        "tipo": "video", "url": "https://video/playlist.m3u8", "miniatura": "https://video/thumbnail.jpg",
        "alt": "", "ancho": None, "alto": None,
    }]


def test_extrae_multimedia_de_una_cita_con_imagenes():
    imagenes = models.AppBskyEmbedImages.View(images=[
        models.AppBskyEmbedImages.ViewImage(alt="", fullsize="https://img/full", thumb="https://img/thumb"),
    ])
    embed = models.AppBskyEmbedRecordWithMedia.View.model_construct(media=imagenes)
    assert [m["tipo"] for m in analizador.extraer_multimedia(embed)] == ["imagen"]


def test_post_sin_embed_no_tiene_multimedia():
    assert analizador.extraer_multimedia(None) == []


def test_describir_multimedia():
    imagen = {"tipo": "imagen", "alt": ""}
    assert analizador.describir_multimedia([]) == "sin multimedia"
    assert analizador.describir_multimedia([{"tipo": "video", "alt": ""}]) == "video"
    assert analizador.describir_multimedia([imagen, imagen, imagen]) == "imagen x3"
    assert analizador.describir_multimedia([{"tipo": "imagen", "alt": "Ends 11/30"}]) == "imagen (alt: Ends 11/30)"


def test_prompt_marca_los_posts_sin_texto():
    post = dict(POSTS[0], texto_limpio="")
    prompt = analizador.construir_prompt("playstation.com", [post])
    assert "| multimedia: video | (sin texto)" in prompt
