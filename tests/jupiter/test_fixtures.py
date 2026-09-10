"""T1-T3: a suíte não pode passar verde sem as fixtures que diz testar.

O raciocínio veio da suíte irmã do Moodle e vale igual aqui: um skip por
fixture ausente deixa a suíte verde noutra máquina SEM TER TESTADO NADA.
É o Invariante 6 aplicado à própria suíte.
"""
import pathlib

import pytest

from tests.git import esta_ignorado
from tests.jupiter.conftest import FATIA, FIXTURES, RAIZ, caminho

pytestmark = pytest.mark.politica


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_t1_fixture_da_fatia_existe_e_nao_esta_vazia(chave):
    p = caminho(chave)
    assert p.is_file(), (
        f"fixture da fatia ausente: {p}\n"
        "Ausência é FALHA, não skip: um skip aqui deixaria a suíte verde "
        "numa máquina sem fixture nenhuma."
    )
    assert p.stat().st_size > 0, f"fixture vazia: {p}"


def test_t2_nenhum_caminho_absoluto_de_maquina():
    fonte = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    for agulha in ("/Users/", "/home/", "C:\\", "/private/tmp"):
        assert agulha not in fonte, (
            f"caminho absoluto de máquina no conftest: {agulha!r}. As fixtures "
            "têm que ser resolvidas a partir da posição do arquivo."
        )
    assert FIXTURES == RAIZ / "fixtures" / "jupiter"


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_t3_fatia_nao_depende_de_arquivo_fora_do_git(chave):
    p = caminho(chave)
    assert not esta_ignorado(p, RAIZ), (
        f"{p.name} está no .gitignore. A suíte não pode depender de arquivo que "
        "outra máquina não tem — é o caso de html-obterTurma-*.html, deixado "
        "fora da fatia de propósito (§2 do spec)."
    )
