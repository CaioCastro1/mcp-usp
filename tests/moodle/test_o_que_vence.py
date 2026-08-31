"""Camada 2 — a ferramenta: a pergunta do §5, respondida em uma chamada.

O caso que motiva metade destes testes é real e está no §9 de 28/08: o
`MOODLE_USERID` estava preenchido com o número USP em vez do userid interno, e
`get_users_courses` devolvia lista vazia. Um "não tem nada para entregar" que era
na verdade "você perguntou errado". É exatamente o que o Invariante 6 proíbe.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from usp_mcp.moodle.erros import ErroMoodle
from usp_mcp.moodle.o_que_vence import o_que_vence

pytestmark = pytest.mark.contrato

SP = timezone(timedelta(hours=-3))


class ClienteFalso:
    """Duplo do cliente. Registra o que foi pedido e devolve o que mandarem."""

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro = resposta, erro
        self.chamadas = []

    def chamar(self, funcao, **params):
        self.chamadas.append((funcao, params))
        if self.erro:
            raise self.erro
        return self.resposta


def test_responde_em_uma_chamada_de_ferramenta(eventos_brutos):
    """T32 — critério 2 do §5: uma chamada do ponto de vista do modelo."""
    c = ClienteFalso(eventos_brutos)
    o_que_vence(c, dias=14)
    assert len(c.chamadas) == 1
    assert c.chamadas[0][0] == "core_calendar_get_action_events_by_timesort"


def test_a_janela_pedida_vira_parametro_e_nao_filtro_local(eventos_brutos):
    """T33 — filtrar depois de baixar 528 kB não economiza nada."""
    c = ClienteFalso(eventos_brutos)
    agora = datetime(2026, 8, 31, 12, 0, tzinfo=SP)
    o_que_vence(c, dias=7, agora=agora)
    params = c.chamadas[0][1]
    assert int(params["timesortfrom"]) == int(agora.timestamp())
    assert int(params["timesortto"]) == int((agora + timedelta(days=7)).timestamp())


def test_a_janela_e_declarada_na_saida(eventos_brutos):
    """T34 — Invariante 7: sem limite silencioso.

    "Não tem nada até domingo" e "não tem nada nos próximos 7 dias" são respostas
    diferentes, e o usuário não consegue distinguir se a janela não aparece.
    """
    r = o_que_vence(ClienteFalso(eventos_brutos), dias=7)
    assert "7" in r.texto and "dias" in r.texto.lower()


def test_truncamento_e_declarado(eventos_brutos):
    """T35 — Invariante 7: se paginou, amostrou ou cortou, a saída diz."""
    muitos = {"events": eventos_brutos["events"] * 3}
    r = o_que_vence(ClienteFalso(muitos), dias=14, limite=10)
    assert r.truncado is True
    assert "10" in r.texto
    assert any(p in r.texto.lower() for p in ("mostrando", "truncad", "primeir"))


def test_sem_truncamento_nao_mente_dizendo_que_truncou(eventos_brutos):
    """T36 — o par do anterior: o aviso não pode ser decorativo."""
    r = o_que_vence(ClienteFalso({"events": eventos_brutos["events"][:3]}), dias=14)
    assert r.truncado is False


def test_lista_vazia_nao_vira_nao_tem_nada():
    """T37 — o bug do §9 de 28/08, virado teste.

    Zero evento é resposta legítima, mas tem de vir rotulado com POR QUE está
    vazio, para não ser confundido com credencial errada.
    """
    r = o_que_vence(ClienteFalso({"events": []}), dias=7)
    assert r.vazio_por == "sem_eventos_no_periodo"
    assert "próximos 7 dias" in r.texto.lower() or "7 dias" in r.texto.lower()


def test_erro_de_credencial_nao_e_apresentado_como_lista_vazia():
    """T38 — o outro lado do mesmo bug: falha tem de propagar, não virar zero."""
    c = ClienteFalso(erro=ErroMoodle("token recusado"))
    with pytest.raises(ErroMoodle):
        o_que_vence(c, dias=7)


def test_a_saida_e_texto_curto_nao_json_cru(eventos_brutos):
    """T39 — critério 3 do §5: cabe em pouco contexto.

    O ponto inteiro da ferramenta. 528 kB entram, e o que chega ao modelo tem de
    caber em poucos milhares de caracteres.
    """
    r = o_que_vence(ClienteFalso(eventos_brutos), dias=30)
    assert len(r.texto) < 4_000
    assert not r.texto.lstrip().startswith(("{", "["))


def test_a_saida_diz_o_que_nao_sabe(eventos_brutos):
    """T40 — Invariante 6 na resposta ao usuário, não só na estrutura interna."""
    r = o_que_vence(ClienteFalso(eventos_brutos), dias=30)
    assert "presencial" in r.texto.lower()


def test_nenhuma_escrita_e_emitida_nem_com_a_flag(eventos_brutos, monkeypatch):
    """T41 — Invariante 1 na ferramenta, não só no cliente."""
    monkeypatch.setenv("USP_MCP_ALLOW_WRITES", "1")
    c = ClienteFalso(eventos_brutos)
    o_que_vence(c, dias=14)
    assert [f for f, _ in c.chamadas] == ["core_calendar_get_action_events_by_timesort"]


def test_o_teto_da_api_e_pedido_explicitamente(eventos_brutos):
    """T53 — Invariante 7 do lado do TRANSPORTE, e não só da saída.

    Bug real, achado em 31/08/2026 chamando a API de verdade: sem `limitnum`, o
    Moodle devolve **20** eventos e não diz que parou. A mesma janela de 365
    dias devolveu 20 sem o parâmetro e 30 com `limitnum=50`. Dez entregas
    sumiam, e a ferramenta reportava `truncado=False`.

    A suíte não pegava porque o cliente falso devolve o que o teste mandar — o
    corte acontecia do lado do Moodle. Por isso a asserção é sobre o PARÂMETRO
    ENVIADO, que é onde o defeito morava.
    """
    c = ClienteFalso(eventos_brutos)
    o_que_vence(c, dias=30)
    params = c.chamadas[0][1]
    assert int(params["limitnum"]) == 50, "voltou a confiar no default de 20"


def test_bater_no_teto_da_api_e_declarado(eventos_brutos):
    """T54 — o par do anterior: pedir o teto não basta, tem de dizer quando bate.

    Se o Moodle devolve exatamente o que pedimos, NÃO dá para saber se existe
    mais depois — a API não informa. "Não tem mais nada" e "parei de contar em
    50" são respostas diferentes, e presumir a primeira é o erro que o
    Invariante 7 proíbe.
    """
    no_teto = {"events": (eventos_brutos["events"] * 2)[:50]}
    r = o_que_vence(ClienteFalso(no_teto), dias=365)
    assert r.truncado is True
    assert "50" in r.texto
    assert "máximo" in r.texto.lower() or "teto" in r.texto.lower()


def test_abaixo_do_teto_nao_inventa_aviso(eventos_brutos):
    """T55 — e o aviso não pode ser decorativo: 35 eventos não bateram em nada."""
    r = o_que_vence(ClienteFalso(eventos_brutos), dias=30)
    assert r.truncado is False
    assert "máximo" not in r.texto.lower()
