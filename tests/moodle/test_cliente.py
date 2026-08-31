"""Camada 2 — o cliente: transporte, política na fronteira, e erro legível.

LIMITAÇÃO DECLARADA, e ela decide o que estes testes podem afirmar: a Fase 1 só
capturou respostas bem-sucedidas. Não existe fixture de erro do Moodle. Logo,
estes testes asseguram o CONTRATO DESTA CAMADA — o que ela devolve dado um erro
— e nunca a forma exata do erro do Moodle, que continua não verificada. Capturar
um `invalidtoken` real é barato e seguro (token propositalmente inválido, não
toca na conta) e está no backlog, fora desta fatia.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import cliente as mod_cliente
from usp_mcp.moodle.cliente import ClienteMoodle
from usp_mcp.moodle.erros import (
    ErroMoodle,
    FuncaoBloqueada,
    MoodleIndisponivel,
    RespostaIlegivel,
    TokenInvalido,
)

pytestmark = pytest.mark.contrato

TOKEN_FALSO = "0123456789abcdef0123456789abcdef"


def _cliente(transporte):
    return ClienteMoodle(
        token=TOKEN_FALSO, url="https://exemplo.invalid", transporte=transporte
    )


def test_a_politica_e_aplicada_na_fronteira_do_cliente():
    """T21 — Invariante 2 não é conselho: nada sai sem passar pela política.

    Se a checagem morasse só na camada de ferramenta, qualquer código novo que
    usasse o cliente direto contornaria a allowlist.
    """
    chamou = []
    c = _cliente(lambda **kw: chamou.append(kw) or {})
    with pytest.raises(FuncaoBloqueada):
        c.chamar("mod_assign_submit_for_grading", assignmentid=1)
    assert chamou == [], "requisição foi emitida apesar do bloqueio"


def test_read_only_por_padrao_mesmo_com_a_flag():
    """T22 — Invariante 1: a flag não abre o §2.2, nem por dentro do cliente."""
    c = ClienteMoodle(
        token=TOKEN_FALSO, url="https://exemplo.invalid",
        transporte=lambda **kw: {}, permitir_escrita=True,
    )
    with pytest.raises(FuncaoBloqueada):
        c.chamar("mod_quiz_start_attempt", quizid=1)


def test_token_invalido_diz_o_que_fazer():
    """T23 — Invariante 6. Mensagem acionável, não stack trace."""
    resposta = {
        "exception": "moodle_exception",
        "errorcode": "invalidtoken",
        "message": "Token inválido",
    }
    c = _cliente(lambda **kw: resposta)
    with pytest.raises(TokenInvalido) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    texto = str(e.value).lower()
    assert "token" in texto
    assert "§8" in str(e.value) or ".env" in texto, "não diz como renovar"


def test_erro_cru_do_moodle_e_repassado_legivel_nao_engolido():
    """T24 — Invariante 6: não engolir erro cru da API."""
    resposta = {
        "exception": "webservice_access_exception",
        "errorcode": "accessexception",
        "message": "Acesso negado",
    }
    c = _cliente(lambda **kw: resposta)
    with pytest.raises(ErroMoodle) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    assert "accessexception" in str(e.value)


def test_resposta_nao_json_nao_vira_keyerror():
    """T25 — HTTP 200 com HTML de manutenção é o caso real mais comum."""
    def transporte(**kw):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")
    with pytest.raises(RespostaIlegivel):
        _cliente(transporte).chamar("core_calendar_get_action_events_by_timesort")


def test_indisponibilidade_de_rede_vira_erro_legivel():
    """T26 — timeout e recusa de conexão dizem que o serviço não respondeu."""
    def transporte(**kw):
        raise TimeoutError("timed out")
    with pytest.raises(MoodleIndisponivel) as e:
        _cliente(transporte).chamar("core_calendar_get_action_events_by_timesort")
    assert "edisciplinas" in str(e.value).lower() or "moodle" in str(e.value).lower()


def test_token_ausente_falha_na_construcao_com_instrucao():
    """T27 — falhar cedo, com a instrução do README."""
    with pytest.raises(ErroMoodle) as e:
        ClienteMoodle(token="", url="https://exemplo.invalid", transporte=lambda **kw: {})
    assert ".env" in str(e.value)


def test_o_token_nunca_aparece_em_erro_nem_em_repr():
    """T28 — Invariante 3. O modo mais fácil de vazar um segredo é numa exceção.

    Cobre as quatro superfícies por onde ele escapa: mensagem de erro, repr, str
    e o dicionário de atributos que um logger despeja.
    """
    c = _cliente(lambda **kw: {"exception": "x", "errorcode": "y", "message": "z"})
    assert TOKEN_FALSO not in repr(c)
    assert TOKEN_FALSO not in str(c)
    assert TOKEN_FALSO not in str(vars(c))
    with pytest.raises(ErroMoodle) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    assert TOKEN_FALSO not in str(e.value)
    assert TOKEN_FALSO not in repr(e.value)


def test_o_token_vai_no_corpo_e_nunca_na_url():
    """T29 — segredo em query string vaza para log de proxy e histórico."""
    visto = {}
    c = _cliente(lambda **kw: visto.update(kw) or {"events": []})
    c.chamar("core_calendar_get_action_events_by_timesort")
    assert TOKEN_FALSO not in visto.get("url", "")
    assert visto["dados"]["wstoken"] == TOKEN_FALSO


def test_uma_invocacao_emite_uma_requisicao():
    """T30 — Regra de Ouro do §3.1, no código e não só na disciplina humana."""
    n = []
    c = _cliente(lambda **kw: n.append(1) or {"events": []})
    c.chamar("core_calendar_get_action_events_by_timesort")
    assert len(n) == 1


def test_o_cliente_nao_tem_metodo_que_itere_funcoes():
    """T31 — a Regra de Ouro escrita como ausência de capacidade.

    Um sweep sobre as 447 funções passa por `submit_for_grading` e
    `start_attempt` com o token do dono. A defesa mais confiável é não existir
    o método que faria isso.
    """
    proibidos = {"chamar_varias", "sweep", "varrer", "todas_as_funcoes", "descobrir"}
    assert not (proibidos & set(dir(ClienteMoodle)))
    assert not hasattr(mod_cliente, "listar_funcoes_disponiveis")
