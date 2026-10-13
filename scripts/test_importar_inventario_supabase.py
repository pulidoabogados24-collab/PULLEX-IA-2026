import importlib.util
import json
from pathlib import Path

import pytest


RUTA = Path(__file__).resolve().parent / "importar_inventario_supabase.py"
SPEC = importlib.util.spec_from_file_location("importar_inventario_supabase", RUTA)
modulo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(modulo)


def registro(id="uno", path="Pack Juridico 2/carpeta/modelo.doc"):
    return {"id": id, "path": path, "title": "modelo.doc", "mime": "application/msword",
            "size": "42", "url": "https://drive.google.com/file/d/uno/view"}


def test_inventario_parcial_no_duplica_y_no_publica(tmp_path, capsys):
    ruta = tmp_path / "inventario.jsonl"
    ruta.write_text("\n".join(json.dumps(x) for x in [registro(), registro(),
                    registro("dos", "Pack Juridico 1/otro.doc")]), encoding="utf-8")
    assert modulo.main([str(ruta)]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida == {"archivos_validos": 2,
                      "colecciones": {"PACK JURIDICO 2": 1, "PACK JURIDICO 1": 1},
                      "modo": "simular"}


@pytest.mark.parametrize("cambio", [
    {"path": "Otra unidad/modelo.doc"},
    {"url": "https://evil.example/doc"},
    {"size": "-1"},
])
def test_rechaza_origen_ajeno_o_dato_invalido(cambio):
    dato = registro() | cambio
    with pytest.raises(ValueError):
        modulo.normalizar(dato)
