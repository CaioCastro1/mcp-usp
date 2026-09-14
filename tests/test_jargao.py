"""J1: o que sai do processo não cita o SPEC.

"§9 do SPEC1", "Invariante 2", "medido em 14/09" são referências para quem MANTÉM
o projeto. Para quem usa a ferramenta — o modelo, o usuário — são palavras sem
referente: não ajudam a agir e custam tokens. Docstring e comentário continuam
livres; a regra é só para string literal, que é o que chega ao fio.

A varredura é por AST, como o R40/T43 (import de topo): o primeiro `Expr` string
de módulo, classe e função é docstring e fica de fora. Comentário não está na AST.
"""
import ast
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "usp_mcp"

PROIBIDOS = (
    "§", "Invariante", "SPEC1", "Medido em", "medido em",
    "Fase 1", "Fase 2", "Regra de Ouro",
)

pytestmark = pytest.mark.politica


def _docstrings(arvore: ast.Module) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = getattr(no, "body", [])
            if (
                corpo
                and isinstance(corpo[0], ast.Expr)
                and isinstance(corpo[0].value, ast.Constant)
                and isinstance(corpo[0].value.value, str)
            ):
                ids.add(id(corpo[0].value))
    return ids


def strings_que_saem(caminho: pathlib.Path):
    """(linha, texto) de toda string literal que NÃO é docstring."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    docstrings = _docstrings(arvore)
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings:
            yield no.lineno, no.value


ARQUIVOS = sorted(p.relative_to(RAIZ) for p in PACOTE.rglob("*.py"))


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=str)
def test_j1_nenhuma_string_que_sai_do_processo_cita_o_spec(arquivo):
    achados = [
        (linha, palavra, texto.strip()[:80])
        for linha, texto in strings_que_saem(RAIZ / arquivo)
        for palavra in PROIBIDOS
        if palavra in texto
    ]
    assert not achados, (
        f"{arquivo}: referência de projeto em string que o modelo/usuário lê. "
        "Tire a referência e mantenha o fato:\n  "
        + "\n  ".join(f"linha {l}: {p!r} em {t!r}" for l, p, t in achados)
    )


def test_j1b_a_varredura_pega_string_e_ignora_docstring(tmp_path):
    # Sabotagem controlada: sem isto, um bug na varredura deixaria J1 verde sem ver nada.
    fonte = tmp_path / "x.py"
    fonte.write_text(
        '"""Docstring com §9 e Invariante 2 — permitida."""\n'
        "def f():\n"
        '    """Também docstring, §1."""\n'
        '    return "negado (Invariante 2)"\n',
        encoding="utf-8",
    )
    achados = [(l, t) for l, t in strings_que_saem(fonte) if any(p in t for p in PROIBIDOS)]
    assert achados == [(4, "negado (Invariante 2)")]
