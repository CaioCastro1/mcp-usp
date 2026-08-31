"""T38-T40: canário contra uspdigital.usp.br.

DUAS requisições reais por execução, no máximo, escolhidas à mão. Nenhum
laço, nenhuma enumeração de sigla: o §7 do recon pede a gentileza, e o §8
registra que 26 requisições sem 429 NÃO provam que não haja rate limit.

Compara CHAVES, nunca valores — valor muda por semestre sem que nada
tenha quebrado.
"""
import os

import pytest

from usp_mcp.jupiter import cliente, dwr

pytestmark = pytest.mark.live

MOTIVO = (
    "canário ao vivo desligado. Exporte USP_MCP_LIVE=1 para bater em "
    "uspdigital.usp.br. O §1.1 do SPEC1 registra que o sandbox não alcança a "
    "rede da USP: este teste só roda no terminal do dono."
)

ao_vivo = pytest.mark.skipif(os.environ.get("USP_MCP_LIVE") != "1", reason=MOTIVO)


def _chamar_de_verdade(sigla):
    corpo = dwr.serializar(
        metodo="obter",
        consulta="pubObterDisciplina",
        params={"coddis": sigla, "verdis": 0},
    )
    return cliente.transporte_http(
        f"{cliente.URL_BASE}/ControlePublicoDWR.obter.dwr",
        corpo,
        {"Content-Type": "text/plain", "User-Agent": cliente.AGENTE},
    )


@ao_vivo
def test_t38_forma_da_resposta_real_bate_com_a_fixture(psi3323):
    status, texto = _chamar_de_verdade("PSI3323")
    assert status == 200

    vivo = dwr.decodificar(texto)
    esperado = dwr.decodificar(psi3323)
    assert sorted(vivo) == sorted(esperado), (
        "as chaves de pubObterDisciplina mudaram: ou a fixture está velha, ou "
        "a API mudou de forma. Compare e atualize com decisão registrada no §9."
    )


@ao_vivo
def test_t39_sigla_inexistente_ainda_e_erro_no_corpo_com_200():
    status, texto = _chamar_de_verdade("ZZZ9999")
    assert status == 200, "o Jupiter sinaliza erro no CORPO, não no status"
    with pytest.raises(dwr.JupiterErro):
        dwr.decodificar(texto)


def test_t40_skip_diz_o_motivo_por_escrito():
    # A diferença entre "não rodou" e "não rodou, e aqui está por quê" é o
    # Invariante 6 aplicado à própria suíte.
    if os.environ.get("USP_MCP_LIVE") == "1":
        pytest.skip("canário ligado; este teste cobre o caminho desligado")
    assert "USP_MCP_LIVE=1" in MOTIVO
    assert "uspdigital" in MOTIVO
    assert len(MOTIVO) > 80
