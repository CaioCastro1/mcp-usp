"""AT1-AT18 — "o que venceu e eu não entreguei?".

`o_que_vence` olha para a frente; esta olha para trás **e** cruza com o estado
de entrega, que é o que nenhuma das duas metades sabe sozinha:
`mod_assign_get_assignments` diz o prazo e nunca o que foi feito, e
`mod_assign_get_submission_status` diz o que foi feito e nunca por disciplina.
As duas já estão na allowlist desde `ja_entreguei` (12 e 14/09) — **nenhuma
função nova**, e AT18 trava isso.

**O tom é requisito, não acabamento.** Esta é a primeira ferramenta do projeto
cuja saída ACUSA alguém, e o Invariante 6 vale em dobro aqui: o e-Disciplinas
sabe o que foi *registrado* nele, e não o que a pessoa fez. Entrega no papel,
por e-mail, em outro sistema, ou que o professor recebeu e nunca lançou, é
invisível para esta consulta — e "você não entregou" sobre uma dessas é uma
afirmação falsa dita com a autoridade de um sistema. AT7 e AT8 são os dois
testes que travam isso, e AT8 é o caso que a API deixa detectar: nota lançada
sem envio registrado é entrega que aconteceu fora do Moodle.

Procedência dos insumos, separada de propósito:

- `assign_ptc3314.json` é **fixture REAL** (12/09, higienizada), e é ela que
  sustenta os casos centrais: o EC-1 venceu em 13/09 23:59 e as duas provas
  presenciais têm `nosubmissions: 1`.
- a resposta de `mod_assign_get_submission_status` e o payload de VÁRIOS cursos
  (`entregas_falsas`) são **escritos à mão**, com a ressalva inteira no
  `conftest`. A worktree não tem token.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from tests.moodle.conftest import ClienteFalso, entregas_falsas, status_de_entrega
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.atrasadas import TETO_DISCIPLINAS, atrasadas
from usp_mcp.moodle.erros import ErroMoodle, MoodleIndisponivel
from usp_mcp.moodle.ja_entreguei import TETO_CONSULTAS
from usp_mcp.moodle.texto import formatar_data

pytestmark = pytest.mark.contrato

SP = timezone(timedelta(hours=-3))

# Os quatro `assign` reais de PTC3314 (courseid 142036), pelos ids da fixture.
EC1 = 577509
PROVA_1 = 577510
EC2 = 577511
PROVA_2 = 577514
PTC3314 = 142036

PRAZO_EC1 = datetime(2026, 9, 13, 23, 59, tzinfo=SP)

# 14/09, um dia depois do prazo do EC-1: só ele está vencido na fixture real.
AGORA = datetime(2026, 9, 14, 10, 0, tzinfo=SP)
# 01/10, depois também da Prova Presencial - 1 (28/09), que é o `assign` que
# NÃO aceita envio. Mesma fixture real, outro instante da pergunta.
DEPOIS = datetime(2026, 10, 1, 10, 0, tzinfo=SP)

# Os dez courseid do semestre em andamento na fixture de matrículas, na ordem em
# que `users_courses.json` os traz.
EM_ANDAMENTO = {
    142259,  # PME3344
    143454,  # PRO3811
    142323,  # PRO3821
    142478,  # PSI3472
    142033,  # PSI3323
    143374,  # PTC3313
    143352,  # PTC3312
    142979,  # PTC3360
    142358,  # PTC3361
    142036,  # PTC3314
}


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas, entregas, status_por_assign=None):
    mapa = status_por_assign or {}

    def _status(params):
        valor = mapa[params["assignid"]]
        # Chamável = o teste quer simular uma FALHA daquela consulta, e não
        # devolver a função como se fosse resposta. Mesma convenção do
        # `ClienteFalso.baixar` no conftest.
        return valor(params) if callable(valor) else valor

    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 8214},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_assign_get_assignments": entregas,
            "mod_assign_get_submission_status": _status,
        }
    )


def _consultados(cliente):
    return [p["assignid"] for f, p in cliente.chamadas if f.endswith("submission_status")]


def _nada_enviado(**kw):
    return status_de_entrega(com_lastattempt=False, **kw)


# --------------------------------------------------------------------------
# O escopo, e o que ele custa
# --------------------------------------------------------------------------


def test_at1_sem_disciplina_o_escopo_e_o_semestre_em_andamento(
    disciplinas_brutas, entregas_ptc3314
):
    """AT1 — "o que eu devo?" é pergunta de todas as matérias de uma vez.

    Escopo vazio devolveria as 74 matrículas, 1 MB, ~251k tokens (§9, 28/08), e
    escopo de uma disciplina só faria quem pergunta repetir a pergunta dez
    vezes — que é justamente o que `ja_entreguei` já faz bem. O meio-termo é
    mandar os `courseid` das que estão em andamento, que `disciplinas` já sabe
    quais são sem gastar chamada.

    Asserção sobre o que foi ENVIADO: o dublê devolveria a mesma fixture para
    qualquer conjunto de ids.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    atrasadas(c, agora=AGORA)

    params = c.params_de("mod_assign_get_assignments")
    assert set(params.values()) == EM_ANDAMENTO, params
    assert sorted(params) == [f"courseids[{i}]" for i in range(len(EM_ANDAMENTO))]


def test_at2_com_disciplina_o_escopo_e_so_ela(disciplinas_brutas, entregas_ptc3314):
    """AT2 — a pergunta estreita continua valendo, e não custa as dez."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    atrasadas(c, "PTC3314", agora=AGORA)

    assert c.params_de("mod_assign_get_assignments") == {"courseids[0]": PTC3314}


def test_at3_sigla_que_nao_resolve_nao_gasta_chamada(disciplinas_brutas):
    """AT3 — mesma regra de `material` e `ja_entreguei`: perguntar ao Moodle
    para descobrir que a pergunta estava errada gasta chamada da conta do dono
    à toa, e cada uma fica no log."""
    c = _cliente(disciplinas_brutas, entregas_falsas([]))

    with pytest.raises(ErroMoodle) as e:
        atrasadas(c, "PSI9999", agora=AGORA)

    assert "PSI9999" in str(e.value)
    assert "mod_assign_get_assignments" not in [f for f, _ in c.chamadas]


def test_at18_nenhuma_funcao_nova_e_chamada(disciplinas_brutas, entregas_ptc3314):
    """AT18 — as quatro funções desta ferramenta já estavam na allowlist.

    Duas vieram da resolução de sigla (31/08) e duas de `ja_entreguei` (12 e
    14/09). Uma quinta entrando aqui seria decisão de §9, e o vermelho tem de
    aparecer antes disso.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    atrasadas(c, agora=AGORA)

    assert sorted(set(f for f, _ in c.chamadas)) == [
        "core_enrol_get_users_courses",
        "core_webservice_get_site_info",
        "mod_assign_get_assignments",
        "mod_assign_get_submission_status",
    ]


# --------------------------------------------------------------------------
# Olhar para trás: o que entra na lista e o que não entra
# --------------------------------------------------------------------------


def test_at4_entrega_com_prazo_no_futuro_nao_e_consultada(
    disciplinas_brutas, entregas_ptc3314
):
    """AT4 — esta ferramenta olha para TRÁS, e a metade da frente já tem dona.

    O EC-2 vence em novembro: consultar o status dele aqui gastaria uma ida ao
    Moodle para descobrir que ainda nem era para ter sido entregue.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert _consultados(c) == [EC1]
    assert "EC - 2" not in r.texto


def test_at5_vencida_que_nao_aceita_envio_nao_gasta_chamada_nem_vira_acusacao(
    disciplinas_brutas, entregas_ptc3314
):
    """AT5 — a Prova Presencial - 1 venceu em 28/09 e `nosubmissions: 1`.

    É o `nosubmissions` de `ja_entreguei` (J3) num contexto pior: lá "não
    entregou" sobre uma prova presencial era ruído, aqui seria uma acusação
    sobre algo que **não tem como ser entregue** pelo e-Disciplinas. Ela não
    some (Invariante 7), aparece com o motivo — e sem gastar ida.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    r = atrasadas(c, "PTC3314", agora=DEPOIS)

    assert _consultados(c) == [EC1], "gastou consulta numa atividade sem envio"
    assert "Prova Presencial - 1" in r.texto
    assert r.faltando == 1, "a prova presencial entrou na conta do que falta"


def test_at6_rascunho_vencido_aparece_como_nao_enviado(
    disciplinas_brutas, entregas_ptc3314
):
    """AT6 — o caso que `ja_entreguei` existe para separar, agora com prazo
    vencido: o arquivo está lá, a tela mostra o arquivo lá, e o professor não
    recebeu nada. É a linha mais urgente que esta ferramenta pode imprimir.
    """
    c = _cliente(
        disciplinas_brutas, entregas_ptc3314, {EC1: status_de_entrega(status="draft")}
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert r.faltando == 1
    assert "RASCUNHO" in r.texto
    assert "EC-1" in r.texto


def test_at7_a_saida_nao_acusa_e_diz_que_e_registro(
    disciplinas_brutas, entregas_ptc3314
):
    """AT7 — o Invariante 6 quando a resposta é má notícia.

    A ferramenta sabe o que o e-Disciplinas REGISTRA. Entrega no papel, por
    e-mail ou em outro sistema não chega até aqui, e dizer "você não entregou"
    sobre uma delas é afirmar o que não se sabe, com a autoridade de um
    sistema. A saída diz de onde vem o dado e manda confirmar.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert "não entregou" not in r.texto.lower()
    assert "registra" in r.texto.lower(), "não disse que é o registro, não o fato"
    assert "confirme" in r.texto.lower(), "não disse o que fazer antes de concluir"


def test_at8_nota_lancada_sem_envio_registrado_nao_vira_falta(
    disciplinas_brutas, entregas_ptc3314
):
    """AT8 — o caso em que a própria API deixa desmentir a acusação.

    `gradingstatus: "graded"` sem envio registrado é, quase sempre, entrega que
    aconteceu FORA do Moodle e nota que o professor lançou à mão. Contá-la como
    faltando seria o erro mais caro desta ferramenta: alarme falso sobre algo
    que já foi feito **e já foi corrigido**.
    """
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: _nada_enviado(gradingstatus="graded")},
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert r.faltando == 0
    assert "corrigida" in r.texto.lower()
    assert r.vazio_por == "nada_em_atraso"


def test_at9_entregue_depois_do_prazo_nao_entra_no_que_falta(
    disciplinas_brutas, entregas_ptc3314
):
    """AT9 — "venceu e eu não entreguei" não é "venceu e eu entreguei atrasado".

    A segunda é resposta de `ja_entreguei`, que marca a entrega como feita
    depois do prazo. Aqui ela é contada e não listada: listar tudo o que venceu
    faria a lista do que FALTA ficar enterrada no que já foi feito.
    """
    c = _cliente(
        disciplinas_brutas, entregas_ptc3314, {EC1: status_de_entrega(status="submitted")}
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert r.faltando == 0
    assert r.entregues == 1
    assert "1 entrega" in r.texto, "a entrega vencida e feita sumiu da contagem"


def test_at10_prorrogacao_individual_no_futuro_tira_do_atraso(
    disciplinas_brutas, entregas_ptc3314
):
    """AT10 — J8 um passo adiante: a prorrogação existe para este aluno, e
    ignorá-la faria a ferramenta cobrar uma entrega que o professor liberou.

    O prazo da turma já passou; o dele, não. Não é falta, e a saída diz por quê.
    """
    prorrogado = int(datetime(2026, 9, 30, 23, 59, tzinfo=SP).timestamp())
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: _nada_enviado(extensionduedate=prorrogado)},
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert r.faltando == 0
    assert "prorrog" in r.texto.lower()


# --------------------------------------------------------------------------
# Os tetos, e o Invariante 7
# --------------------------------------------------------------------------


def test_at11_teto_de_consultas_fica_com_as_mais_recentes_e_declara(
    disciplinas_brutas,
):
    """AT11 — uma ida ao Moodle por entrega vencida, e para em `TETO_CONSULTAS`.

    O corte fica com as de prazo MAIS RECENTE: entrega de março não é o que se
    procura em setembro, e o que venceu ontem ainda dá para correr atrás. O
    corte é declarado com a contagem e com a cura (`disciplina`).
    """
    quinze = [
        (
            700 + i,
            f"EP{i}",
            int((AGORA - timedelta(days=30 - i)).timestamp()),
            0,
        )
        for i in range(15)
    ]
    c = _cliente(
        disciplinas_brutas,
        entregas_falsas([(PTC3314, quinze)]),
        {700 + i: _nada_enviado() for i in range(15)},
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert len(_consultados(c)) == TETO_CONSULTAS
    assert set(_consultados(c)) == {700 + i for i in range(5, 15)}, (
        "o corte não ficou com as de prazo mais recente"
    )
    assert r.truncado
    assert "5 entrega" in r.texto, "o corte não disse quantas ficaram de fora"
    assert "disciplina" in r.texto, "o corte não disse como ver o resto"


def test_at12_teto_de_disciplinas_por_invocacao_e_declarado(disciplinas_brutas):
    """AT12 — o outro teto, e este é de BYTES e não de latência.

    A chamada é uma só, mas o payload cresce com o número de `courseid`: a
    fixture real de PTC3314 tem 8.571 B para quatro `assign`, e o item 8 do
    `CLAUDE.md` proíbe ler resposta crua acima de ~200 kB. O teto é o que
    mantém a conta longe disso quando alguém cursa mais matérias do que o dono.

    O payload deste caso é escrito à mão (a fixture real cobre um curso só).
    """
    muitas = [
        {
            "id": 900000 + i,
            "shortname": f"XYZ{i:04d}-2026",
            "fullname": f"Disciplina {i}",
            "startdate": int(datetime(2026, 8, 3, tzinfo=SP).timestamp()),
            "enddate": int(datetime(2026, 12, 12, tzinfo=SP).timestamp()),
        }
        for i in range(TETO_DISCIPLINAS + 3)
    ]
    c = _cliente(muitas, entregas_falsas([]))

    r = atrasadas(c, agora=AGORA)

    params = c.params_de("mod_assign_get_assignments")
    assert len(params) == TETO_DISCIPLINAS
    assert r.disciplinas_de_fora == 3
    assert "3 disciplina" in r.texto, "o corte de disciplinas não foi declarado"


def test_at13_warning_da_api_vira_aviso_em_vez_de_sumir(
    disciplinas_brutas, entregas_ptc3314
):
    """AT13 — Invariante 7 no ponto mais perigoso desta ferramenta.

    A fixture REAL traz dois `warnings` de "sem direito de acesso" a módulos da
    disciplina. Engoli-los aqui faria a resposta dizer "nada em atraso" sobre
    uma lista que o próprio Moodle avisou estar incompleta — e é exatamente
    sobre esta ferramenta que quem lê tomaria a decisão de não olhar mais.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: status_de_entrega()})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert "2 atividade" in r.texto, "os warnings do e-Disciplinas foram engolidos"


# --------------------------------------------------------------------------
# Os vazios e os erros
# --------------------------------------------------------------------------


def test_at14_nada_em_atraso_nao_sai_mudo(disciplinas_brutas, entregas_ptc3314):
    """AT14 — a boa notícia também é rotulada.

    "Nada em atraso" e "a consulta não achou o que procurar" são a mesma tela
    para quem lê, e esta é a ferramenta em que confundir as duas faz alguém
    parar de procurar. O vazio vem com o que a consulta cobre e com o que ela
    não sabe.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: status_de_entrega()})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert r.faltando == 0
    assert r.vazio_por == "nada_em_atraso"
    assert "questionário" in r.texto.lower(), "não disse o que não cobre"


def test_at15_sem_disciplina_em_andamento_diz_o_que_fazer(disciplinas_brutas):
    """AT15 — férias, ou conta só com semestres passados.

    Sem disciplina em andamento não há escopo, e escopo vazio traria as 74
    matrículas. A resposta é erro legível com a cura (passar a disciplina), e
    não uma lista vazia que parece "você não deve nada".
    """
    encerradas = [
        {
            "id": 900001,
            "shortname": "XYZ0001-2023",
            "fullname": "Disciplina encerrada",
            "startdate": int(datetime(2023, 3, 1, tzinfo=SP).timestamp()),
            "enddate": int(datetime(2023, 7, 1, tzinfo=SP).timestamp()),
        }
    ]
    c = _cliente(encerradas, entregas_falsas([]))

    with pytest.raises(ErroMoodle) as e:
        atrasadas(c, agora=AGORA)

    assert "disciplina" in str(e.value).lower()
    assert "mod_assign_get_assignments" not in [f for f, _ in c.chamadas]


def test_at16_erro_do_cliente_sobe_e_nao_vira_nada_em_atraso(
    disciplinas_brutas, entregas_ptc3314
):
    """AT16 — falha de credencial virando "você está em dia" é a pior tradução
    possível: as duas leem igual e só uma manda dormir tranquilo."""
    def _explode(_params):
        raise MoodleIndisponivel("o e-Disciplinas não respondeu")

    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _explode})

    with pytest.raises(ErroMoodle):
        atrasadas(c, "PTC3314", agora=AGORA)


# --------------------------------------------------------------------------
# A forma da saída
# --------------------------------------------------------------------------


def test_at17_a_data_tem_a_mesma_grafia_das_irmas(
    disciplinas_brutas, entregas_ptc3314
):
    """AT17 — J18: `o_que_vence`, `ja_entreguei` e esta respondem sobre o MESMO
    prazo, e duas grafias fariam quem lê as três não reconhecer que é ele."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: _nada_enviado()})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert formatar_data(PRAZO_EC1) in r.texto


def test_at19_nenhuma_url_interna_sai(disciplinas_brutas, entregas_ptc3314):
    """AT19 — Invariante 3: o nome do arquivo do rascunho sai, o endereço não."""
    c = _cliente(
        disciplinas_brutas, entregas_ptc3314, {EC1: status_de_entrega(status="draft")}
    )

    r = atrasadas(c, "PTC3314", agora=AGORA)

    assert "pluginfile.php" not in r.texto


def test_at20_a_projecao_descarta_o_que_nao_responde(
    disciplinas_brutas, entregas_ptc3314
):
    """AT20 — a medida da fronteira, e as duas metades do cru têm procedências
    diferentes: a lista de entregas é fixture REAL, a resposta de status é
    escrita à mão. O que a projeção descarta é o mesmo de `ja_entreguei`: o
    texto que o aluno entregou e o enunciado em HTML.
    """
    status = status_de_entrega(com_lastattempt=False)
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: status})

    r = atrasadas(c, "PTC3314", agora=AGORA)

    cru = len(json.dumps(entregas_ptc3314, ensure_ascii=False).encode()) + len(
        json.dumps(status, ensure_ascii=False).encode()
    )
    assert len(r.texto.encode()) < cru / 4
    for gordo in ("Tolerância: 48 h", "<p", "introattachments"):
        assert gordo not in r.texto
