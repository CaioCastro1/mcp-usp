"""QO8-QO27 — o questionário como objeto: "já fiz?", "ainda dá?", "perdi algum?".

Offline inteiro. Os insumos têm procedências diferentes, e a diferença está
dita: a lista de matrículas é a fixture REAL (`users_courses.json`); os treze
pares (nome, `quizid`) de PTC3314 são reais, vindos do boletim capturado em
15/09; os prazos, o `attempts` permitido e as tentativas são ESCRITOS À MÃO a
partir da forma declarada no core — este worktree não tem token, e a captura
das duas funções de quiz é a medição pendente do spec.

O caso que estes testes existem para não deixar passar tem duas caras:

1. **O campo não veio e a saída fingiu que sabia.** O spec nasceu antes da
   captura, e a hipótese principal (a conta de aluno recebe `attempts`) pode
   cair. QO12 e QO14 derrubam a hipótese no dublê e exigem que a ferramenta
   diga "não sei" em vez de "1 usada" (R2 lida ao contrário: afirmar a mais é
   pior do que perguntar a menos).
2. **Um identificador de tentativa saiu.** QO19 e QO20 são a fronteira do spec
   lida pela saída: se um `attemptid` ou um nome bloqueado aparecer no texto,
   a regra deixou de valer com tudo verde.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

from tests.moodle.conftest import (
    AUSENTE,
    CURSO_PTC3314,
    QUIZ_T12,
    QUIZZES_PTC3314,
    ClienteFalso,
    questionario_falso,
    questionarios_falsos,
    tentativa_falsa,
    tentativas_falsas,
)
from tests.moodle.test_forma_real import _chaves_lidas, _confere, _mapa, _real
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle import politica, server
from usp_mcp.moodle.erros import ErroMoodle
from usp_mcp.moodle.ja_entreguei import TETO_CONSULTAS
from usp_mcp.moodle.questionarios import (
    CAMPOS_LIDOS_DA_TENTATIVA,
    CAMPOS_LIDOS_DO_QUESTIONARIO,
    questionarios,
)
from usp_mcp.moodle.texto import formatar_data

pytestmark = pytest.mark.contrato

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "fixtures" / "moodle"
_QUESTIONARIOS = "usp_mcp/moodle/questionarios.py"

SP = timezone(timedelta(hours=-3))
USERID = 8214

# 14/09/2026, 10h — a mesma véspera de `test_ja_entreguei`: o Teste 11 fechou
# na quinta passada, o 12 fecha na sexta que vem, o 14 ainda não abriu.
AGORA = datetime(2026, 9, 14, 10, 0, tzinfo=SP)


def _ts(dia, mes, hora=23, minuto=59) -> int:
    return int(datetime(2026, mes, dia, hora, minuto, tzinfo=SP).timestamp())


FECHA_T13 = _ts(25, 9)
FECHA_T12 = _ts(18, 9)
FECHA_T11 = _ts(10, 9)
FECHA_T10 = _ts(3, 9)
ABRE_T14 = _ts(21, 9, 0, 0)
FEZ_T11 = _ts(9, 9, 21, 4)

NOME_T12 = QUIZZES_PTC3314[11][1]
NOME_T11 = QUIZZES_PTC3314[10][1]
QUIZ_T11 = QUIZZES_PTC3314[10][0]
QUIZ_T13 = QUIZZES_PTC3314[12][0]
QUIZ_T10 = QUIZZES_PTC3314[9][0]


def _q(indice, **kw):
    """O questionário de índice `indice` (0 = Teste 1) da lista real, com o
    prazo e o orçamento que o teste quiser."""
    quizid, nome = QUIZZES_PTC3314[indice]
    return questionario_falso(quizid, nome, **kw)


T13 = _q(12, timeclose=FECHA_T13)
T12 = _q(11, timeclose=FECHA_T12)
T11 = _q(10, timeclose=FECHA_T11)
T10 = _q(9, timeclose=FECHA_T10)


def _semestre_inteiro():
    """Os treze reais: 1-11 fechados, um por semana, 12 e 13 abertos."""
    return [
        _q(i, timeclose=int((AGORA - timedelta(weeks=11 - i)).timestamp()))
        for i in range(11)
    ] + [T12, T13]


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas, quizzes, tentativas_por_quiz=None):
    """Dublê com a cadeia inteira: sigla → courseid → questionários → tentativas.

    `tentativas_por_quiz` é consultado pelo `quizid` ENVIADO, e não por ordem
    de chamada — é o que faz QO9 provar que cada questionário foi consultado
    pelo id dele. Quem não está no mapa responde lista vazia, que é a hipótese
    do ponto 2 da medição pendente.
    """
    mapa = tentativas_por_quiz or {}

    def _tentativas(params):
        return mapa.get(params["quizid"], tentativas_falsas())

    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_quiz_get_quizzes_by_courses": quizzes,
            "mod_quiz_get_user_attempts": _tentativas,
        }
    )


def _de_quiz(cliente):
    return [(f, p) for f, p in cliente.chamadas if f.startswith("mod_quiz_")]


def _tentativas_pedidas(cliente):
    return [p["quizid"] for f, p in cliente.chamadas if f == "mod_quiz_get_user_attempts"]


def _linha_de(texto: str, nome: str) -> str:
    linhas = [l for l in texto.splitlines() if nome in l]
    assert len(linhas) == 1, f"{nome!r} devia ter exatamente uma linha:\n{texto}"
    return linhas[0]


# --------------------------------------------------------------------------
# Os parâmetros ENVIADOS — o dublê devolve o que o teste mandou, então é aqui
# que se prova o escopo, o `status` literal e o `userid` derivado
# --------------------------------------------------------------------------


def test_qo8_courseids_vai_explicito_e_uma_vez_so(disciplinas_brutas):
    """QO8 — sem `courseids[0]` a função devolve TODOS os cursos, e ninguém
    mediu o que isso custa em 74 matrículas."""
    c = _cliente(disciplinas_brutas, questionarios_falsos([T12]))

    questionarios(c, "PTC3314", agora=AGORA)

    listas = [p for f, p in c.chamadas if f == "mod_quiz_get_quizzes_by_courses"]
    assert len(listas) == 1
    assert listas[0] == {"courseids[0]": CURSO_PTC3314}, listas[0]


def test_qo9_toda_consulta_de_tentativa_envia_status_finished_literal(disciplinas_brutas):
    """QO9 — R2 pelo parâmetro enviado, mais o `userid` derivado e o `quizid`
    que veio da primeira resposta.

    `unfinished` e `all` devolvem tentativa em andamento, e "você tem uma
    aberta agora" é a deixa para "então termina para mim". `includepreviews`
    vai literal pelo mesmo motivo de sempre: default não verificado não é
    promessa.
    """
    c = _cliente(disciplinas_brutas, questionarios_falsos([T12, T11]))

    questionarios(c, "PTC3314", agora=AGORA)

    consultas = [p for f, p in c.chamadas if f == "mod_quiz_get_user_attempts"]
    assert len(consultas) == 2
    for params in consultas:
        assert params["status"] == "finished", params
        assert params["includepreviews"] == 0, params
        assert params["userid"] == USERID, "o userid não é o derivado do token"
    assert sorted(p["quizid"] for p in consultas) == sorted([QUIZ_T12, QUIZ_T11])


def test_qo10_sigla_que_nao_resolve_nao_gasta_chamada_de_quiz(disciplinas_brutas):
    c = _cliente(disciplinas_brutas, questionarios_falsos([T12]))

    with pytest.raises(ErroMoodle) as e:
        questionarios(c, "XYZ9999", agora=AGORA)

    assert "XYZ9999" in str(e.value)
    assert not _de_quiz(c), "gastou chamada para descobrir que a sigla estava errada"


# --------------------------------------------------------------------------
# Os quatro estados do objeto
# --------------------------------------------------------------------------


def test_qo11_os_quatro_estados_saem_certos_e_com_a_grafia_de_j18(disciplinas_brutas):
    """QO11 — aberto × fechado, com × sem tentativa finalizada.

    O quadrante fechado × sem tentativa é a linha que ninguém dava: `notas`
    imprime "-" tanto para "não fiz" quanto para "oculta".
    """
    feito = tentativas_falsas([tentativa_falsa(quizid=QUIZ_T11, timefinish=FEZ_T11)])
    feito_aberto = tentativas_falsas([tentativa_falsa(quizid=QUIZ_T13, timefinish=FEZ_T11)])
    c = _cliente(
        disciplinas_brutas,
        questionarios_falsos([T13, T12, T11, T10]),
        {QUIZ_T11: feito, QUIZ_T13: feito_aberto},
    )

    r = questionarios(c, "PTC3314", agora=AGORA)

    l12 = _linha_de(r.texto, NOME_T12)
    assert "SEM TENTATIVA FINALIZADA" in l12 and "ainda no prazo" in l12, l12
    assert formatar_data(datetime.fromtimestamp(FECHA_T12, SP)) in l12

    l13 = _linha_de(r.texto, QUIZZES_PTC3314[12][1])
    assert "FEITO" in l13 and "ainda no prazo" in l13, l13

    l11 = _linha_de(r.texto, NOME_T11)
    assert "FEITO" in l11 and "fechado" in l11, l11
    assert formatar_data(datetime.fromtimestamp(FEZ_T11, SP)) in l11, (
        "a data da última tentativa não sai, ou sai em outra grafia"
    )

    l10 = _linha_de(r.texto, QUIZZES_PTC3314[9][1])
    assert "SEM TENTATIVA FINALIZADA" in l10 and "PRAZO VENCIDO" in l10, l10

    assert r.total == 4 and r.consultados == 4 and not r.truncado


def test_qo12_attempts_ausente_nao_vira_orcamento_inventado(disciplinas_brutas):
    """QO12 — a hipótese principal do spec, derrubada no dublê.

    Se a conta de aluno não receber `attempts`, a ferramenta continua dizendo
    se você já fez, e diz que NÃO sabe quantas vezes ainda pode fazer. Um
    "1 usada" sem o "de 3" leria como ilimitadas, que é afirmar a mais.
    """
    sem_orcamento = [_q(11, timeclose=FECHA_T12, attempts=AUSENTE),
                     _q(10, timeclose=FECHA_T11, attempts=AUSENTE)]
    feito = tentativas_falsas([tentativa_falsa(quizid=QUIZ_T11, timefinish=FEZ_T11)])
    c = _cliente(disciplinas_brutas, questionarios_falsos(sem_orcamento), {QUIZ_T11: feito})

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert "SEM TENTATIVA FINALIZADA" in _linha_de(r.texto, NOME_T12)
    assert "FEITO" in _linha_de(r.texto, NOME_T11)
    for palavra in ("usadas", "disponíveis", "ilimitadas"):
        assert palavra not in r.texto, f"falou de orçamento sem ter o campo: {palavra!r}"
    assert "não informou" in r.texto and "quantas tentativas" in r.texto, (
        "a ausência do campo não foi dita:\n" + r.texto
    )


def test_qo13_attempts_zero_e_ilimitadas_e_tres_e_um_de_tres(disciplinas_brutas):
    ilimitado = _q(12, timeclose=FECHA_T13, attempts=0)
    tres = _q(11, timeclose=FECHA_T12, attempts=3)
    feito = tentativas_falsas([tentativa_falsa(quizid=QUIZ_T12, timefinish=FEZ_T11)])
    c = _cliente(disciplinas_brutas, questionarios_falsos([ilimitado, tres]), {QUIZ_T12: feito})

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert "ilimitadas" in _linha_de(r.texto, QUIZZES_PTC3314[12][1])
    l12 = _linha_de(r.texto, NOME_T12)
    assert "1 de 3 tentativas usadas" in l12, l12
    assert "não informou" not in r.texto, "acusou ausência de campo que veio"


def test_qo14_timeclose_ausente_e_zero_sao_coisas_diferentes_e_nenhuma_e_1970(
    disciplinas_brutas,
):
    """QO14 — `0` é "sem fechamento" (o Moodle aceita); chave ausente é "não
    sei", e "não sei" sai escrito. Nenhum dos dois vira 01/01/1970."""
    sem_fechamento = _q(11, timeclose=0)
    nao_informado = _q(10, timeclose=AUSENTE)
    c = _cliente(disciplinas_brutas, questionarios_falsos([sem_fechamento, nao_informado]))

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert "sem fechamento" in _linha_de(r.texto, NOME_T12)
    assert "prazo não informado" in _linha_de(r.texto, NOME_T11)
    assert "1970" not in r.texto and "01/01" not in r.texto
    assert "data de fechamento" in r.texto, "a ausência do campo não virou aviso"
    # Os dois foram consultados: sem prazo não é motivo para não perguntar.
    assert sorted(_tentativas_pedidas(c)) == sorted([QUIZ_T12, QUIZ_T11])


def test_qo15_questionario_que_ainda_nao_abriu_nao_gasta_chamada(disciplinas_brutas):
    futuro = questionario_falso(233479, "Teste semanal - 14", timeopen=ABRE_T14, timeclose=_ts(28, 9))
    c = _cliente(disciplinas_brutas, questionarios_falsos([futuro, T12]))

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert _tentativas_pedidas(c) == [QUIZ_T12], "consultou tentativa de quiz que nem abriu"
    l14 = _linha_de(r.texto, "Teste semanal - 14")
    assert "AINDA NÃO ABRIU" in l14, l14
    assert formatar_data(datetime.fromtimestamp(ABRE_T14, SP)) in l14


# --------------------------------------------------------------------------
# O teto, a ordem e o corte declarado
# --------------------------------------------------------------------------


def test_qo16_treze_questionarios_respeitam_o_teto_na_ordem_certa_e_ninguem_some(
    disciplinas_brutas,
):
    """QO16 — abertos primeiro (do que fecha antes para o que fecha depois),
    depois fechados do mais recente para o mais antigo; quem fica fora do teto
    continua na lista, com nome e prazo; e o corte diz o parâmetro que o evita."""
    c = _cliente(disciplinas_brutas, questionarios_falsos(_semestre_inteiro()))

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert len(_de_quiz(c)) <= 1 + TETO_CONSULTAS
    pedidos = _tentativas_pedidas(c)
    assert len(pedidos) == TETO_CONSULTAS
    # Abertos primeiro: 12 fecha antes de 13.
    assert pedidos[:2] == [QUIZ_T12, QUIZ_T13], pedidos
    # Depois os fechados, do mais recente (11) para trás.
    esperados_fechados = [QUIZZES_PTC3314[i][0] for i in range(10, 10 - (TETO_CONSULTAS - 2), -1)]
    assert pedidos[2:] == esperados_fechados, pedidos

    assert r.truncado and r.total == 13 and r.consultados == TETO_CONSULTAS
    # Os três mais antigos aparecem, sem estado e sem sumir.
    for i in range(3):
        linha = _linha_de(r.texto, QUIZZES_PTC3314[i][1])
        assert "não consultado" in linha, linha
        assert "FEITO" not in linha and "SEM TENTATIVA" not in linha
    assert "3 questionário" in r.texto and "`questionario`" in r.texto, (
        "o corte não foi declarado com a cura:\n" + r.texto
    )


def test_qo17_filtro_por_nome_consulta_so_o_que_casa_e_o_que_nao_casa_nao_gasta(
    disciplinas_brutas,
):
    c = _cliente(disciplinas_brutas, questionarios_falsos(_semestre_inteiro()))

    r = questionarios(c, "PTC3314", questionario="12", agora=AGORA)

    assert _tentativas_pedidas(c) == [QUIZ_T12]
    assert not r.truncado
    assert NOME_T12 in r.texto

    c2 = _cliente(disciplinas_brutas, questionarios_falsos([T12, T11]))
    r2 = questionarios(c2, "PTC3314", questionario="EP7", agora=AGORA)

    assert r2.vazio_por == "busca_sem_resultado"
    assert not _tentativas_pedidas(c2), "gastou chamada para um filtro que não casou"
    assert "EP7" in r2.texto and NOME_T12 in r2.texto and NOME_T11 in r2.texto
    assert "ja_entreguei" in r2.texto, "não disse onde a tarefa mora"


def test_qo18_disciplina_sem_questionario_diz_isso_e_aponta_para_a_tarefa(
    disciplinas_brutas,
):
    c = _cliente(disciplinas_brutas, questionarios_falsos([]))

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert r.vazio_por == "sem_questionarios"
    assert r.total == 0 and not _tentativas_pedidas(c)
    assert "nenhum questionário" in r.texto.lower()
    assert "ja_entreguei" in r.texto


# --------------------------------------------------------------------------
# A fronteira, lida pela saída
# --------------------------------------------------------------------------


def _todos_os_caminhos(disciplinas_brutas):
    """Com tentativa, sem tentativa, com teto batido — os três textos."""
    feito = tentativas_falsas(
        [tentativa_falsa(quizid=QUIZ_T11, attemptid=910001, timefinish=FEZ_T11, sumgrades=7.25)]
    )
    com = _cliente(disciplinas_brutas, questionarios_falsos([T12, T11]), {QUIZ_T11: feito})
    sem = _cliente(disciplinas_brutas, questionarios_falsos([T12]))
    teto = _cliente(disciplinas_brutas, questionarios_falsos(_semestre_inteiro()))
    return [
        questionarios(com, "PTC3314", agora=AGORA).texto,
        questionarios(sem, "PTC3314", agora=AGORA).texto,
        questionarios(teto, "PTC3314", agora=AGORA).texto,
    ]


def test_qo19_nenhum_identificador_nem_nota_bruta_sai_no_texto(disciplinas_brutas):
    """QO19 — R1 pela saída: o `attemptid` chega na resposta e não é
    projetado; o `quizid` nasce e morre na invocação; `sumgrades` é nota bruta
    e nota é assunto de `notas`."""
    for texto in _todos_os_caminhos(disciplinas_brutas):
        assert "910001" not in texto, "o attemptid saiu"
        assert "7.25" not in texto and "7,25" not in texto, "sumgrades saiu"
        for quizid, _ in QUIZZES_PTC3314:
            assert str(quizid) not in texto, f"o quizid {quizid} saiu"


def test_qo20_a_saida_diz_que_so_le_e_nao_nomeia_funcao_bloqueada(disciplinas_brutas):
    """QO20 — mesma regra de D5: não dar ao modelo o vocabulário que a
    política existe para negar. E a promessa de leitura sai escrita."""
    for texto in _todos_os_caminhos(disciplinas_brutas):
        assert "não abre" in texto and "configuração" in texto, texto
        nomeadas = [f for f in politica.BLOQUEIO_PERMANENTE if f in texto]
        assert not nomeadas, f"a saída nomeou funções bloqueadas: {nomeadas}"


def test_qo21_tentativa_em_andamento_nao_conta_e_o_aviso_diz(disciplinas_brutas):
    """QO21 — R2 do lado da projeção: mesmo que o site ignore o `status`
    enviado, só `finished` conta como feita."""
    misto = tentativas_falsas(
        [
            tentativa_falsa(quizid=QUIZ_T12, attemptid=1, attempt=1, timefinish=FEZ_T11),
            tentativa_falsa(quizid=QUIZ_T12, attemptid=2, attempt=2, state="inprogress"),
        ]
    )
    c = _cliente(disciplinas_brutas, questionarios_falsos([T12]), {QUIZ_T12: misto})

    r = questionarios(c, "PTC3314", agora=AGORA)

    l12 = _linha_de(r.texto, NOME_T12)
    assert "1 tentativa finalizada" in l12 and "1 de 3" in l12, l12
    assert "EM ANDAMENTO" in r.texto


def test_qo22_warnings_das_duas_chamadas_viram_avisos_separados(disciplinas_brutas):
    com_aviso = tentativas_falsas(com_warning=True)
    c = _cliente(
        disciplinas_brutas,
        questionarios_falsos([T12, T11], com_warning=True),
        {QUIZ_T12: com_aviso},
    )

    r = questionarios(c, "PTC3314", agora=AGORA)

    assert "fora desta lista" in r.texto, "o warning da lista foi engolido"
    assert "1 questionário(s) desta lista" in r.texto and "pode estar incompleto" in r.texto, (
        "o warning do estado foi engolido ou somado ao da lista:\n" + r.texto
    )


def test_qo23_erro_do_cliente_sobe_e_nao_vira_nao_fez_nenhum(disciplinas_brutas):
    def _explode(params):
        raise ErroMoodle("token recusado")

    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_quiz_get_quizzes_by_courses": questionarios_falsos([T12]),
            "mod_quiz_get_user_attempts": _explode,
        }
    )

    with pytest.raises(ErroMoodle):
        questionarios(c, "PTC3314", agora=AGORA)


# --------------------------------------------------------------------------
# O que a projeção lê — declarado, e conferido contra a captura quando ela vier
# --------------------------------------------------------------------------


def test_qo24_a_projecao_le_exatamente_as_chaves_declaradas():
    """QO24 — o espelho de F8 para uma família SEM captura: cada `.get` do
    fonte tem de estar na tabela da Decisão 4 do spec, e cada entrada da
    tabela tem de ser lida. Nem hipótese não declarada, nem promessa morta."""
    do_quiz = _chaves_lidas(_QUESTIONARIOS, "projetar_questionarios", "q")
    da_tentativa = _chaves_lidas(_QUESTIONARIOS, "projetar_tentativas", "a")

    assert do_quiz == set(CAMPOS_LIDOS_DO_QUESTIONARIO), (
        f"lidas: {sorted(do_quiz)}; declaradas: {sorted(CAMPOS_LIDOS_DO_QUESTIONARIO)}"
    )
    assert da_tentativa == set(CAMPOS_LIDOS_DA_TENTATIVA), (
        f"lidas: {sorted(da_tentativa)}; declaradas: {sorted(CAMPOS_LIDOS_DA_TENTATIVA)}"
    )
    # A fronteira, no fonte: nem o id da tentativa nem a nota bruta são lidos.
    assert not {"id", "sumgrades", "uniqueid"} & da_tentativa
    assert "intro" not in do_quiz and "grade" not in do_quiz


CAPTURA_QUIZZES = FIXTURES / "quizzes_ptc3314.json"
CAPTURA_TENTATIVAS = FIXTURES / "quiz_attempts_t12.json"

COMO_CAPTURAR = (
    "captura pendente — este worktree não tem token. Quem tem, roda:\n"
    "  ./scripts/capture.sh quizzes_ptc3314 mod_quiz_get_quizzes_by_courses "
    '"courseids[0]=142036"\n'
    "  ./scripts/capture.sh quiz_attempts_t12 mod_quiz_get_user_attempts "
    '"quizid=<id>" "userid=<id>" status=finished includepreviews=0\n'
    "  python3 scripts/higienizar.py ...   (a resposta de tentativas traz userid)\n"
    "e aí este teste passa a conferir forma em vez de pular."
)


def test_qo25_forma_real_quando_a_captura_existir():
    """QO25 — a ÚNICA exceção declarada à regra "fixture ausente é vermelho".

    Todas as outras fixturas do Moodle existem e podem sumir; esta nunca
    existiu, e este worktree não pode produzi-la. Pular com o comando na razão
    é a forma honesta de dizer "pendente"; falhar seria vermelho por decisão
    que não é deste código. No dia em que os dois arquivos entrarem, o skip
    some sozinho e o teste vira o F1-F6 e o F8 desta família.
    """
    if not (CAPTURA_QUIZZES.exists() and CAPTURA_TENTATIVAS.exists()):
        pytest.skip(COMO_CAPTURAR)

    # F1-F6 desta família: o construtor não inventa campo.
    _confere("quizzes_ptc3314", questionarios_falsos([T12]), "questionarios_falsos")
    _confere("quiz_attempts_t12", tentativas_falsas([tentativa_falsa()]), "tentativas_falsas")

    # F8 desta família: a projeção não lê campo que a captura não tem.
    real_quiz = _mapa(_real("quizzes_ptc3314"))
    assert "quizzes[]" in real_quiz, "a captura não tem questionário nenhum"
    sobrando = set(CAMPOS_LIDOS_DO_QUESTIONARIO) - real_quiz["quizzes[]"]
    assert not sobrando, (
        f"a conta de aluno NÃO recebe {sorted(sobrando)}: a hipótese do spec caiu, "
        "e a degradação de QO12/QO14 passa a ser o caminho normal — registre no §9"
    )
    real_tentativas = _mapa(_real("quiz_attempts_t12"))
    if "attempts[]" in real_tentativas:
        assert not set(CAMPOS_LIDOS_DA_TENTATIVA) - real_tentativas["attempts[]"]


# --------------------------------------------------------------------------
# O descritor e a fronteira MCP
# --------------------------------------------------------------------------


def test_qo27_o_descritor_fala_a_lingua_de_quem_pergunta_e_e_so_leitura():
    f = [x for x in server.listar_ferramentas() if x["name"] == "questionarios"][0]

    assert f["annotations"]["readOnlyHint"] is True
    assert f["annotations"]["destructiveHint"] is False
    assert "mod_quiz" not in f["description"]
    for palavra in ("questionário", "tentativa"):
        assert palavra in f["description"].lower()
    props = f["inputSchema"]["properties"]
    assert set(props) == {"disciplina", "questionario"}
    assert f["inputSchema"]["required"] == ["disciplina"]
    assert all(p.get("description") for p in props.values())


def test_qo27b_chamar_ferramenta_roteia_com_cliente_injetado(disciplinas_brutas):
    c = _cliente(disciplinas_brutas, questionarios_falsos([T12]))

    saida = server.chamar_ferramenta(
        "questionarios", {"disciplina": "PTC3314", "questionario": "12"}, cliente=c
    )

    assert NOME_T12 in saida
    assert _tentativas_pedidas(c) == [QUIZ_T12]
