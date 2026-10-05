# 08 — Dependencias y cadena de suministro

## Python (producción)

| Paquete | Antes | Ahora | Nota |
|---|---|---|---|
| fastapi | `>=0.110.0` (sin fijar) | `==0.142.1` | Probada. |
| uvicorn | `>=0.29.0` | `==0.54.0` | Probada. |
| anthropic | `>=0.40.0` | `==1.9.0` | Probada con el doble de pruebas; **NOT VERIFIED** contra la API real en esta iteración (no hay clave en el entorno de auditoría). |
| python-dotenv | `>=1.0.0` | `==1.2.3` | — |
| chromadb, voyageai | comentadas | comentadas | RAG inactivo. |

`requirements.lock` guarda el árbol completo (22 paquetes) de una instalación limpia en Python 3.11, la misma versión que declara `runtime.txt`.

**`pip-audit`** (base de datos PyPI/OSV, 30-sep-2026): `requirements.txt` → *No known vulnerabilities found*; `requirements.lock` → *No known vulnerabilities found*.

## JavaScript (CDN)

| Librería | Antes | Ahora | Nota |
|---|---|---|---|
| DOMPurify | 3.0.9, sin SRI | 3.4.16 + SRI sha512 | La 3.0.9 está dentro del rango de los avisos públicos CVE-2024-45801 y CVE-2024-47875 (corregidos en 3.1.3). |
| marked | 12.0.2, sin SRI | 12.0.2 + SRI sha512 | Se mantiene la versión (la 18.x cambia la API; su salida pasa siempre por DOMPurify). |

Las huellas SRI se tomaron de la API de cdnjs y se comprobaron localmente contra los archivos descargados (coinciden).

## Hallazgos de código (búsqueda estática)

| Búsqueda | Resultado |
|---|---|
| `TODO` / `FIXME` / `HACK` | 0 en código; solo en documentación de planificación. |
| Claves de API reales (`sk-ant-…`, `re_…`) | 0. Solo marcadores `xxxx` en `.env.example`. |
| Contraseñas en código | 0 en el paquete. La antigua clave de admin por defecto (retirada en julio) figura en el diagnóstico del Proyecto de Claude; si se usó alguna vez en un despliegue real, **debe considerarse comprometida y rotarse**. |
| Llaves privadas / archivos de llave | `app_secret.key` en el zip entregado → eliminado (SEC-05). |
| `eval`, `new Function`, `document.write` | 0. |
| Ejecución de comandos (`subprocess`, `os.system`) | 0. |
| SQL por concatenación | 0. |
| Modo depuración / trazas al usuario | No hay `debug=True`; las trazas al usuario se eliminaron (SEC-15). |
| URLs inseguras | `http://www.secretariasenado.gov.co` (enlace informativo en el modo degradado). INFO. |

## Pendiente

Escaneo automático en cada cambio (GitHub Actions: `pytest`, `pip-audit`, detector de secretos tipo gitleaks), SBOM (CycloneDX: `pip-audit -f cyclonedx-json`) y revisión de licencias. No se configuró CI porque no hay acceso al repositorio remoto desde este entorno.
