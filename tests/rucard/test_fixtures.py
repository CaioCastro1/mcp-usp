"""R1-R4: a suíte não pode passar verde sem as fixtures que diz testar.

Herdado das duas suítes irmãs, e vale igual aqui: um skip por fixture ausente
deixa a suíte verde noutra máquina SEM TER TESTADO NADA. É o Invariante 6
aplicado à própria suíte.
"""
import datetime
import pathlib
import subprocess

import pytest

from tests.rucard.conftest import (
    FATIA,
    FIXTURES,
    RAIZ,
    SEMANA_FASE1,
    SEMANA_SEGUINTE,
    caminho,
    carregar,
)

pytestmark = pytest.mark.politica


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_r1_fixture_da_fatia_existe_e_nao_esta_vazia(chave):
    p = caminho(chave)
    assert p.is_file(), (
        f"fixture da fatia ausente: {p}\n"
        "Ausência é FALHA, não skip: um skip aqui deixaria a suíte verde numa "
        "máquina sem fixture nenhuma."
    )
    assert p.stat().st_size > 0, f"fixture vazia: {p}"


def test_r2_nenhum_caminho_absoluto_de_maquina():
    fonte = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    for agulha in ("/Users/", "/home/", "C:\\", "/private/tmp"):
        assert agulha not in fonte, (
            f"caminho absoluto de máquina no conftest: {agulha!r}. As fixtures "
            "têm que ser resolvidas a partir da posição do arquivo."
        )
    assert FIXTURES == RAIZ / "fixtures" / "rucard"


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_r3_fatia_nao_depende_de_arquivo_fora_do_git(chave):
    p = caminho(chave)
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(p)], cwd=RAIZ, capture_output=True
    )
    assert r.returncode == 1, (
        f"{p.name} está no .gitignore. A suíte não pode depender de arquivo que "
        "outra máquina não tem. (O cardápio é dado público: nada aqui precisa "
        "de higienização, ao contrário do Moodle.)"
    )


def test_r4_o_par_de_semanas_e_do_mesmo_ru_em_semanas_diferentes():
    # É este par que torna R15 possível: cache de uma semana + pergunta de
    # outra. Sem ele, "o cache valida a semana" seria teste de mock.
    primeira = carregar("menu_6")
    segunda = carregar("menu_6_semana_seguinte")

    datas_1 = [d["date"] for d in primeira["meals"]]
    datas_2 = [d["date"] for d in segunda["meals"]]

    assert (datas_1[0], datas_1[-1]) == SEMANA_FASE1
    assert (datas_2[0], datas_2[-1]) == SEMANA_SEGUINTE
    assert not set(datas_1) & set(datas_2), "as duas semanas se sobrepõem"

    # Segunda-feira nas duas, e 7 dias: a API devolve seg→dom (§1.2).
    for datas in (datas_1, datas_2):
        assert len(datas) == 7
        primeiro = datetime.datetime.strptime(datas[0], "%d/%m/%Y").date()
        assert primeiro.weekday() == 0, f"{datas[0]} não é segunda-feira"


def test_r4b_as_duas_grafias_de_fechado_estao_representadas_na_fatia():
    # O §1.2 e a nota da Fase 1 registram: RU 6 devolve "Fechado", RUs 7/8/9
    # devolvem "FECHADO". Se a fatia só tivesse uma grafia, R28 seria decoração.
    grafias = set()
    for chave in ("menu_6", "menu_7", "menu_8", "menu_9"):
        for dia in carregar(chave)["meals"]:
            for refeicao in ("lunch", "dinner"):
                bruto = dia[refeicao]["menu"].strip()
                if bruto.lower() == "fechado":
                    grafias.add(bruto)
    assert {"Fechado", "FECHADO"} <= grafias, (
        f"a fatia só tem as grafias {sorted(grafias)}. A comparação "
        "case-insensitive precisa das duas para ser exercitada de verdade."
    )
