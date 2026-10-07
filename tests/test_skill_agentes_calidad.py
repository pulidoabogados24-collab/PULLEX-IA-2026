"""Skill y subagentes de calidad de respuesta (PUL-018): formato, rutas citadas y reglas de .gitignore."""
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / ".claude" / "skills" / "pullex-response-intelligence" / "SKILL.md"
AGENTES = {n: RAIZ / ".claude" / "agents" / f"{n}.md" for n in ("hermes", "argos", "minerva")}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-⛿✀-➿]")


def _frontmatter(ruta: Path) -> dict:
    t = ruta.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    assert m, f"{ruta.name} sin frontmatter"
    return dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)


def test_skill_tiene_nombre_y_descripcion():
    fm = _frontmatter(SKILL)
    assert fm["name"].strip() == "pullex-response-intelligence"
    assert len(fm["description"].strip()) > 80


@pytest.mark.parametrize("nombre", sorted(AGENTES))
def test_agentes_bien_formados(nombre):
    fm = _frontmatter(AGENTES[nombre])
    assert fm["name"].strip() == nombre
    assert len(fm["description"].strip()) > 60
    tools = {t.strip() for t in fm["tools"].split(",")}
    assert tools <= {"Read", "Grep", "Glob", "Bash"}
    assert "Write" not in tools and "Edit" not in tools  # los críticos informan, no modifican el repositorio


def test_la_skill_apunta_a_archivos_que_existen():
    t = SKILL.read_text(encoding="utf-8")
    rutas = set(re.findall(r"`((?:docs|prompts|evaluacion|tests|\.claude)/[\w\-./]+\.\w+)`", t))
    assert rutas
    # el archivo de estado se crea en el último commit de PUL-018; el resto debe existir ya
    faltan = [r for r in rutas if not (RAIZ / r).exists() and "PUL-018-prompt-y-evaluaciones" not in r]
    assert faltan == []


@pytest.mark.parametrize("ruta", [SKILL, *AGENTES.values()], ids=lambda p: p.name)
def test_sin_emojis_ni_universidades(ruta):
    t = ruta.read_text(encoding="utf-8")
    assert not EMOJI.search(t)
    assert not re.search(r"externado|javeriana|del rosario|nacional de colombia|de los andes|universidad libre", t, re.I)


def test_gitignore_versiona_skills_y_agentes_pero_no_el_resto_de_claude():
    def ignorado(ruta: str) -> bool:
        r = subprocess.run(["git", "check-ignore", "-q", ruta], cwd=RAIZ)
        return r.returncode == 0
    if not (RAIZ / ".git").exists():
        pytest.skip("sin repositorio git")
    assert not ignorado(".claude/skills/pullex-response-intelligence/SKILL.md")
    assert not ignorado(".claude/agents/hermes.md")
    assert ignorado(".claude/worktrees/pul-018/app.py")
    assert ignorado(".claude/settings.local.json")
    assert ignorado(".claude/proyecto-datos/memoria.md")
