"""El trabajador sólo extrae texto soportado; nunca publica archivos."""
from scripts.ingestar_contenidos_drive import extraer, PLAIN


def test_texto_basico_se_indexa_por_fragmentos():
    fragmentos = extraer(("A" * 6600).encode("utf-8"), "text/plain")
    assert len(fragmentos) == 2
    assert all(0 < len(texto) <= 6000 for _, texto in fragmentos)


def test_mime_desconocido_no_lee_contenido():
    assert extraer(b"datos", "application/octet-stream") == []


def test_elimina_caracter_nulo_no_valido_en_postgres():
    texto = extraer(b"primera\x00segunda", "text/plain")
    assert texto == [("texto", "primerasegunda")]


def test_fragmentos_limitados():
    assert len(extraer(("x" * 20000).encode(), "text/plain", max_fragmentos=2)) == 2
