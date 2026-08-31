"""Camada 3 — canário. Fala com a USP de verdade, e só quando mandam.

Existe por um motivo que o resto da suíte não cobre: a fixture é de 28/08/2026 e
congela. Sem esta camada, a USP pode mudar a API por baixo e a suíte continua
verde enquanto o servidor real quebra.

Regra de Ouro (§3.1): UMA função, escolhida à mão, uma chamada por execução.
Nada aqui itera sobre lista de funções — um sweep sobre as 447 passa por
`start_attempt` e `submit_for_grading` com a credencial do dono.
"""
from __future__ import annotations

import os

import pytest

from tests.moodle.conftest import ARQUIVO_ENV
from usp_mcp.moodle import politica
from usp_mcp.moodle.cliente import ClienteMoodle

pytestmark = [pytest.mark.live, pytest.mark.contrato]


@pytest.fixture(scope="module")
def cliente_real():
    token = os.environ.get("MOODLE_TOKEN")
    if not token:
        # Duas causas distintas, duas curas distintas (Invariante 6). A versão
        # anterior desta mensagem mandava copiar o .env.example para quem já
        # tinha o .env preenchido — o conftest é que não carregava o arquivo.
        if ARQUIVO_ENV is None:
            pytest.fail(
                "USP_MCP_LIVE=1 mas MOODLE_TOKEN está vazio, e nenhum .env foi "
                "encontrado (nem na raiz da suíte, nem no checkout principal). "
                "Copie .env.example para .env (§8 do SPEC1)."
            )
        pytest.fail(
            f"USP_MCP_LIVE=1 mas MOODLE_TOKEN está vazio. O .env FOI encontrado "
            f"em {ARQUIVO_ENV} e carregado — então a chave está ausente ou vazia "
            "lá dentro. Não é o arquivo que falta (§8 do SPEC1)."
        )
    return ClienteMoodle(
        token=token,
        url=os.environ.get("MOODLE_URL", "https://edisciplinas.usp.br"),
    )


def test_a_forma_da_resposta_real_ainda_bate_com_a_fixture(cliente_real, eventos_brutos):
    """T50 — o canário. Uma chamada, e compara só a FORMA.

    Não compara conteúdo de propósito: os eventos mudam todo dia, e um teste que
    falha por isso é ruído que ninguém lê depois da terceira vez.
    """
    vivo = cliente_real.chamar(
        "core_calendar_get_action_events_by_timesort", limitnum=5
    )
    assert set(vivo) == set(eventos_brutos)
    if vivo["events"]:
        esperadas = set(eventos_brutos["events"][0])
        obtidas = set(vivo["events"][0])
        faltando = esperadas - obtidas
        assert not faltando, f"campos sumiram da API desde 28/08/2026: {sorted(faltando)}"


def test_a_camada_live_so_alcanca_a_allowlist():
    """T51 — a Regra de Ouro guardada por asserção, não por boa intenção."""
    assert politica.ALLOWLIST == frozenset(
        {"core_calendar_get_action_events_by_timesort"}
    )
