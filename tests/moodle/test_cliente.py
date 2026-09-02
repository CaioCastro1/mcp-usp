"""Camada 2 — o cliente: transporte, política na fronteira, e erro legível.

LIMITAÇÃO PARCIALMENTE FECHADA em 31/08/2026. A Fase 1 só capturou respostas
bem-sucedidas, então estes testes nasceram assegurando o CONTRATO DESTA CAMADA —
o que ela devolve dado um erro — e nunca a forma exata do erro do Moodle. O
`invalidtoken` real foi capturado desde então (`fixtures/moodle/erro_invalidtoken.json`,
com `wstoken=""`: não usa credencial, não toca conta nenhuma) e T52 abaixo liga
os dois. Os outros modos de falha — `accessexception`, HTML de manutenção,
timeout — seguem sendo contrato de camada, com a forma real não verificada.
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


def test_o_erro_real_do_moodle_vira_TokenInvalido(erro_invalidtoken):
    """T52 — a forma do erro deixou de ser suposição, para este modo de falha.

    Os outros testes de erro montam o dicionário à mão, o que verifica o
    contrato da camada mas não que o Moodle fale desse jeito. Este usa a
    resposta crua capturada de `edisciplinas.usp.br` em 31/08/2026.

    O que a captura desmentiu: o `exception` real é
    `core\\exception\\moodle_exception`, com namespace — não o
    `moodle_exception` pelado que os testes acima supõem. Passa ileso porque o
    cliente casa em `errorcode`, nunca em `exception`; se algum dia alguém
    trocar o critério, este teste é que pega.
    """
    assert erro_invalidtoken["errorcode"] == "invalidtoken"
    c = _cliente(lambda **kw: erro_invalidtoken)
    with pytest.raises(TokenInvalido) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    assert "§8" in str(e.value) or ".env" in str(e.value).lower()
    assert TOKEN_FALSO not in str(e.value)


def test_erro_de_parametro_real_sobe_legivel_e_nao_vira_TokenInvalido(
    erro_invalidparameter,
):
    """T56 — o segundo erro real capturado, e ele NÃO pode virar TokenInvalido.

    `invalidtoken` e `invalidparameter` têm a mesma forma de três chaves. Um
    cliente que casasse por "contém 'invalid'" mandaria você renovar um token
    que está perfeito.
    """
    c = _cliente(lambda **kw: erro_invalidparameter)
    with pytest.raises(ErroMoodle) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    assert not isinstance(e.value, TokenInvalido)
    assert "invalidparameter" in str(e.value)


def test_errorcode_nem_sempre_e_um_codigo(erro_limite_fora_da_faixa):
    """T57 — fato da API que contraria o nome do campo (§9, 31/08/2026).

    Medido: `limitnum=-5` devolve `errorcode` valendo a FRASE
    "Limit must be between 1 and 50 (inclusive)", não um identificador. Quem
    tratar `errorcode` como enum quebra aqui. O cliente sobrevive porque só
    compara por igualdade exata com `invalidtoken` — este teste trava esse
    critério, e a mensagem crua chega inteira a quem lê.
    """
    assert " " in erro_limite_fora_da_faixa["errorcode"], "virou código estável?"
    c = _cliente(lambda **kw: erro_limite_fora_da_faixa)
    with pytest.raises(ErroMoodle) as e:
        c.chamar("core_calendar_get_action_events_by_timesort")
    assert not isinstance(e.value, TokenInvalido)
    assert "between 1 and 50" in str(e.value)


@pytest.mark.politica
def test_t82_o_timeout_cobre_a_chamada_mais_pesada_medida():
    """A `get_users_courses` levou 14,7 s ao vivo em 31/08 e estourou o teto de
    15 s que estava aqui — com a suíte inteira verde, porque nenhum teste
    alcança o transporte real.

    O piso é 3x a medição, não o valor exato: rede de universidade em dia ruim
    não é o mesmo dia. Se alguém baixar isto para "falhar rápido", a ferramenta
    `material` volta a quebrar na primeira pergunta.
    """
    assert mod_cliente._TIMEOUT_PADRAO_SEGUNDOS >= 45, (
        "timeout abaixo do medido: get_users_courses levou 14,7 s ao vivo"
    )


# --- T91, T93, T94, T99: o download ---------------------------------------

TOKEN_DE_TESTE = "TOKEN-SINTETICO-NAO-E-CREDENCIAL"
URL_TESTE = "https://edisciplinas.usp.br"
URL_ARQUIVO = f"{URL_TESTE}/webservice/pluginfile.php/9599792/mod_resource/content/26/a.pdf"


class _DownloadFalso:
    """Grava o que recebeu e devolve (content_type, bytes) combinados."""

    def __init__(self, content_type="application/pdf", corpo=b"%PDF-1.4 conteudo"):
        self.chamadas: list[dict] = []
        self._content_type = content_type
        self._corpo = corpo

    def __call__(self, *, url, dados, teto_bytes):
        self.chamadas.append({"url": url, "dados": dados, "teto_bytes": teto_bytes})
        return self._content_type, self._corpo


def _cliente_com(download):
    return ClienteMoodle(
        token=TOKEN_DE_TESTE,
        url=URL_TESTE,
        transporte=lambda **k: {},
        transporte_download=download,
    )


def test_T91_url_de_outro_host_e_recusada_antes_de_qualquer_io():
    """A credencial vai no CORPO do POST: outro host receberia o token."""
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    with pytest.raises(FuncaoBloqueada) as erro:
        cliente.baixar("https://evil.example.com/webservice/pluginfile.php/1/x.pdf")

    # O que prova a regra é o transporte NÃO ter sido chamado — não a mensagem.
    assert download.chamadas == []
    assert "evil.example.com" in str(erro.value)


def test_T91b_url_no_host_certo_mas_fora_do_pluginfile_e_recusada():
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    with pytest.raises(FuncaoBloqueada):
        cliente.baixar(f"{URL_TESTE}/login/token.php")

    assert download.chamadas == []


def test_T93_json_com_http_200_vira_erro_legivel():
    """Falha de credencial no pluginfile.php NÃO vem como 4xx (§9, 01/09)."""
    download = _DownloadFalso(
        content_type="application/json; charset=utf-8",
        corpo=b'{"errorcode":"invalidtoken","error":"Token invalido"}',
    )
    cliente = _cliente_com(download)

    with pytest.raises(TokenInvalido):
        cliente.baixar(URL_ARQUIVO)


def test_T93b_json_de_erro_generico_preserva_o_errorcode():
    download = _DownloadFalso(
        content_type="application/json",
        corpo=b'{"errorcode":"missingparam","error":"faltou"}',
    )
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO)

    assert "missingparam" in str(erro.value)


def test_T94_tamanho_divergente_do_esperado_vira_erro():
    """Entregar arquivo truncado como bom é o pior resultado possível."""
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO, tamanho_esperado=999)

    assert "999" in str(erro.value) and "5" in str(erro.value)


def test_T94b_tamanho_batendo_devolve_os_bytes():
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    assert cliente.baixar(URL_ARQUIVO, tamanho_esperado=5) == b"12345"


class _RespostaHTTPFalsa:
    """Simula o objeto que `urllib.request.urlopen` devolve, com corpo maior
    que qualquer teto usado nos testes abaixo.

    Existe para exercitar o transporte REAL (`_transporte_download_padrao`) e
    não o dublê `_DownloadFalso` — só assim o `+ 1` de
    `resp.read(teto_bytes + 1)` fica sob teste. Um arquivo interno sem
    `filesize` utilizável não pode ser recusado por antecipação (não há como
    saber o tamanho antes de ler); o byte extra é o que permite ao download
    real notar que ultrapassou o teto, em vez de parar silenciosamente em
    exatamente `teto_bytes` e devolver um arquivo truncado como se fosse bom.
    """

    def __init__(self, corpo: bytes, content_type: str = "application/pdf"):
        self._corpo = corpo
        self._content_type = content_type
        self.pedidos_de_leitura: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def headers(self):
        return {"Content-Type": self._content_type}

    def read(self, n):
        self.pedidos_de_leitura.append(n)
        return self._corpo[:n]


def test_T94c_corpo_acima_do_teto_levanta_mesmo_sem_tamanho_esperado(monkeypatch):
    """Caso real: arquivo sem `filesize` conhecido de antemão. A única forma
    de saber que ele passa do teto é o byte extra que sobra na leitura.
    """
    resposta_falsa = _RespostaHTTPFalsa(b"x" * 20)
    monkeypatch.setattr(
        mod_cliente.urllib.request, "urlopen", lambda *a, **k: resposta_falsa
    )
    cliente = ClienteMoodle(
        token=TOKEN_DE_TESTE, url=URL_TESTE, transporte=lambda **k: {}
    )

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO, teto_bytes=5)

    assert "5" in str(erro.value)
    # A prova de que o "+1" foi o que permitiu detectar: só 6 bytes foram
    # pedidos ao transporte real — nunca os 20 disponíveis no corpo falso.
    assert resposta_falsa.pedidos_de_leitura == [6]


def test_T94d_corpo_exatamente_no_teto_nao_levanta_e_devolve_os_bytes():
    """O que separa `>` de `>=`: no limite exato, o arquivo é bom e não pode
    ser recusado."""
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    assert cliente.baixar(URL_ARQUIVO, teto_bytes=5) == b"12345"


def test_T94e_o_teto_bytes_chega_ao_transporte_de_download():
    """Asserte sobre o que foi ENVIADO: sem isso, o teto poderia ser ignorado
    na leitura e o teste ainda passaria — o dublê devolve o que o teste
    mandou, não o que a implementação de fato repassou."""
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    cliente.baixar(URL_ARQUIVO, teto_bytes=999)

    assert download.chamadas[0]["teto_bytes"] == 999


def test_T99_o_token_vai_no_corpo_e_nunca_na_url():
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    cliente.baixar(URL_ARQUIVO)

    enviado = download.chamadas[0]
    assert enviado["dados"]["token"] == TOKEN_DE_TESTE
    assert TOKEN_DE_TESTE not in enviado["url"]


def test_T99b_o_token_nao_aparece_em_nenhuma_mensagem_de_erro():
    download = _DownloadFalso(
        content_type="application/json", corpo=b'{"errorcode":"invalidtoken"}'
    )
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO)

    assert TOKEN_DE_TESTE not in str(erro.value)
