"""Camada 2 — a fronteira MCP, fina de propósito.

Só três testes, e é intencional: o valor da suíte está na projeção e na política,
que não têm nada a ver com protocolo. Aqui checa-se o que o MODELO vê — nome,
descrição e formato de saída. Sem depender do SDK: `server.py` expõe as duas
funções puras e o adaptador stdio é casca por cima.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import server

pytestmark = pytest.mark.contrato


def test_expoe_exatamente_uma_ferramenta():
    """T42 — a fatia vertical é uma ferramenta. Crescer é decisão registrada."""
    fs = server.listar_ferramentas()
    assert len(fs) == 1
    assert fs[0]["name"] == "o_que_vence"


def test_o_nome_vem_da_pergunta_nao_da_funcao_do_moodle():
    """T43 — §5: `o_que_vence` é bom nome; `get_action_events_by_timesort` não.

    A descrição é o que faz o modelo escolher a ferramenta certa, então ela tem
    de usar o vocabulário de quem pergunta.
    """
    f = server.listar_ferramentas()[0]
    assert "get_action_events" not in f["description"]
    assert any(p in f["description"].lower() for p in ("entrega", "prazo", "vence"))


def test_ferramenta_desconhecida_da_erro_legivel():
    """T44 — Invariante 6 na fronteira: nome errado não devolve vazio."""
    with pytest.raises(Exception) as e:
        server.chamar_ferramenta("apagar_tudo", {})
    assert "apagar_tudo" in str(e.value)
