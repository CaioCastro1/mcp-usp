"""J1-J17 — a pergunta da véspera: "eu já entreguei isso?".

Offline inteiro, e com um par de insumos de procedências diferentes, de
propósito: a lista de entregas é a fixture REAL de PTC3314 (`assign_ptc3314`,
12/09/2026, com os quatro `assign` e os dois que não aceitam envio), e a
resposta de `mod_assign_get_submission_status` é escrita à mão a partir da
forma documentada — a worktree não tem token e não devia ter. A procedência de
cada uma está no `conftest`; o que fica sem verificação ao vivo está dito lá e
no §9.

O caso que estes testes existem para não deixar acontecer é um só, e é caro:
**rascunho salvo não é entrega feita**. `status="draft"` e `status="submitted"`
são uma palavra de distância no payload e uma reprovação de distância na vida.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from tests.moodle.conftest import ClienteFalso, entregas_falsas, status_de_entrega
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle
from usp_mcp.moodle.ja_entreguei import TETO_CONSULTAS, ja_entreguei

pytestmark = pytest.mark.contrato

SP = timezone(timedelta(hours=-3))

# Os quatro `assign` reais de PTC3314, pelos ids da fixture. Os dois de prova
# presencial têm `nosubmissions: 1` — o professor os criou só para ter data.
EC1 = 577509
EC2 = 577511
PROVA_1 = 577510
PROVA_2 = 577514

# 14/09/2026, um dia depois do prazo do EC-1 (13/09 23:59) e sete semanas antes
# do EC-2. É a véspera invertida: a pergunta que se faz depois de entregar.
AGORA = datetime(2026, 9, 14, 10, 0, tzinfo=SP)


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Cache de processo compartilhado entre casos produz verde que nunca
    chamou nada — mesmo motivo de `disciplinas.limpar_cache` existir."""
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas, entregas, status_por_assign=None):
    """Dublê com a cadeia inteira: sigla → courseid → entregas → status.

    `status_por_assign` é consultado pelo `assignid` ENVIADO, e não por ordem de
    chamada: é o que faz J2 provar que cada entrega foi consultada pelo id dela
    em vez de pelo id da primeira (o dublê devolveria algo de qualquer jeito).
    """
    mapa = status_por_assign or {}

    def _status(params):
        return mapa[params["assignid"]]

    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 8214},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_assign_get_assignments": entregas,
            "mod_assign_get_submission_status": _status,
        }
    )


def _todos_entregues(**kw):
    return {
        EC1: status_de_entrega(**kw),
        EC2: status_de_entrega(**kw),
    }


# --------------------------------------------------------------------------
# A cadeia de chamadas — asserção sobre o que foi ENVIADO (item 11 do CLAUDE.md)
# --------------------------------------------------------------------------


def test_j1_a_lista_de_entregas_vem_escopada_por_courseid(
    disciplinas_brutas, entregas_ptc3314
):
    """J1 — `mod_assign_get_assignments` SEM escopo devolve as 74 matrículas,
    1 MB, ~251k tokens (§9, 28/08). O parâmetro tem default vazio, então
    esquecer o escopo é o modo de falha padrão, não a exceção."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    ja_entreguei(c, "PTC3314", agora=AGORA)

    params = c.params_de("mod_assign_get_assignments")
    assert params == {"courseids[0]": 142036}, (
        "a chamada de entregas perdeu o escopo — sem ele são 74 disciplinas"
    )


def test_j2_uma_consulta_de_status_por_entrega_com_o_assignid_dela(
    disciplinas_brutas, entregas_ptc3314
):
    """J2 — a Regra de Ouro (§3.1) do lado do parâmetro: uma função escolhida à
    mão, com id real, uma vez por entrega que aceita envio."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    ja_entreguei(c, "PTC3314", agora=AGORA)

    consultados = [p["assignid"] for f, p in c.chamadas if f.endswith("submission_status")]
    assert consultados == [EC1, EC2], (
        f"consultou {consultados}; esperado um status por entrega que aceita "
        "envio, na ordem do prazo"
    )


def test_j3_entrega_que_nao_aceita_envio_nao_gasta_chamada(
    disciplinas_brutas, entregas_ptc3314
):
    """J3 — medido na fixture real: 2 dos 4 `assign` de PTC3314 têm
    `nosubmissions: 1` (as duas provas presenciais, criadas só para ter data).

    Perguntar o status delas gastaria metade das chamadas desta ferramenta para
    receber "não entregou" sobre algo que **não tem como entregar** — e essa
    resposta seria uma acusação falsa, não uma informação.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    consultados = [p["assignid"] for f, p in c.chamadas if f.endswith("submission_status")]
    assert PROVA_1 not in consultados and PROVA_2 not in consultados
    # Invariante 7: não consultar não é sumir. Elas aparecem, com o motivo.
    assert "Prova Presencial - 1" in r.texto
    assert "não aceita envio" in r.texto.lower()


def test_j4_sigla_que_nao_resolve_nao_gasta_chamada_de_entrega(disciplinas_brutas):
    """J4 — mesma regra de `material`: consultar o Moodle para descobrir que a
    pergunta estava errada é gastar chamada da conta do dono à toa."""
    c = _cliente(disciplinas_brutas, {"courses": []})

    with pytest.raises(ErroMoodle) as e:
        ja_entreguei(c, "XYZ9999", agora=AGORA)

    assert "XYZ9999" in str(e.value)
    assert [f for f, _ in c.chamadas] == [
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
    ]


# --------------------------------------------------------------------------
# O que a ferramenta responde — e o erro caro que ela existe para não cometer
# --------------------------------------------------------------------------


def test_j5_rascunho_salvo_nao_e_entrega_feita(disciplinas_brutas, entregas_ptc3314):
    """J5 — o teste mais importante deste arquivo.

    `draft` é rascunho salvo e NÃO enviado para correção: o Moodle o guarda, a
    tela mostra o arquivo lá, e o prazo passa. Tratar `draft` como entregue
    transformaria esta ferramenta na causa exata do problema que ela responde.
    """
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: status_de_entrega(status="draft"), EC2: status_de_entrega()},
    )

    r = ja_entreguei(c, "PTC3314", entrega="EC-1", agora=AGORA)

    assert "rascunho" in r.texto.lower()
    assert "ENTREGUE" not in r.texto.split("EC-1")[1].split("\n")[0].upper(), (
        "rascunho foi rotulado como entregue:\n" + r.texto
    )


def test_j6_entregue_diz_quando_e_o_que_subiu(disciplinas_brutas, entregas_ptc3314):
    """J6 — "sim" sozinho não é resposta: a data e o nome do arquivo são o que
    deixam quem perguntou reconhecer que entregou **a coisa certa**."""
    quando = int(datetime(2026, 9, 13, 20, 26, tzinfo=SP).timestamp())
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {
            EC1: status_de_entrega(timemodified=quando, arquivos=("EC1-relatorio.pdf",)),
            EC2: status_de_entrega(),
        },
    )

    r = ja_entreguei(c, "PTC3314", entrega="EC-1", agora=AGORA)

    assert "ENTREGUE" in r.texto
    assert "13/09 20:26" in r.texto
    assert "EC1-relatorio.pdf" in r.texto


def test_j7_entrega_depois_do_prazo_e_dita(disciplinas_brutas, entregas_ptc3314):
    """J7 — entregue e entregue **em dia** são respostas diferentes. O prazo do
    EC-1 é 13/09 23:59; este envio é de 14/09 09:10, dentro da tolerância
    (`cutoffdate` 15/09 23:59) e ainda assim atrasado."""
    atrasado = int(datetime(2026, 9, 14, 9, 10, tzinfo=SP).timestamp())
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: status_de_entrega(timemodified=atrasado), EC2: status_de_entrega()},
    )

    r = ja_entreguei(c, "PTC3314", entrega="EC-1", agora=AGORA)

    assert "DEPOIS DO PRAZO" in r.texto


def test_j8_prorrogacao_individual_move_o_prazo(disciplinas_brutas, entregas_ptc3314):
    """J8 — `extensionduedate` é prorrogação dada a ESTE aluno. Ignorá-la faria
    a ferramenta chamar de atrasada uma entrega que o professor liberou."""
    atrasado = int(datetime(2026, 9, 14, 9, 10, tzinfo=SP).timestamp())
    prorrogado = int(datetime(2026, 9, 20, 23, 59, tzinfo=SP).timestamp())
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {
            EC1: status_de_entrega(
                timemodified=atrasado, extensionduedate=prorrogado
            ),
            EC2: status_de_entrega(),
        },
    )

    r = ja_entreguei(c, "PTC3314", entrega="EC-1", agora=AGORA)

    linha = [l for l in r.texto.splitlines() if "EC-1" in l][0]
    assert "DEPOIS DO PRAZO" not in linha, linha
    assert "20/09" in r.texto, "a prorrogação não foi dita:\n" + r.texto


def test_j9_nada_enviado_e_resposta_rotulada_nao_erro(
    disciplinas_brutas, entregas_ptc3314
):
    """J9 — Invariante 6: "você não entregou" é resposta legítima, e tem de ser
    distinguível de "não consegui ler o status"."""
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {
            EC1: status_de_entrega(com_lastattempt=False, status="new"),
            EC2: status_de_entrega(com_lastattempt=False, status="new"),
        },
    )

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "NADA ENVIADO" in r.texto.upper()
    assert r.vazio_por is None, "há entregas; o vazio não é da disciplina"


def test_j10_corrigida_e_dita_e_a_nota_nao_e_inventada(
    disciplinas_brutas, entregas_ptc3314
):
    """J10 — `gradingstatus` diz se já corrigiram, e **não** traz a nota: o
    catálogo (§3.5) registra que não há `feedback` no payload. Dizer "corrigida"
    é informação; imprimir um número que não veio seria invenção."""
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: status_de_entrega(gradingstatus="graded"), EC2: status_de_entrega()},
    )

    r = ja_entreguei(c, "PTC3314", entrega="EC-1", agora=AGORA)

    assert "corrigid" in r.texto.lower()
    assert "nota" in r.texto.lower(), "não disse que a nota não sai daqui"


# --------------------------------------------------------------------------
# Projeção medida, Invariante 3 e Invariante 7
# --------------------------------------------------------------------------


def test_j11_a_projecao_descarta_o_que_nao_responde_a_pergunta(
    disciplinas_brutas, entregas_ptc3314
):
    """J11 — a medida que justifica a fronteira.

    Os dois campos gordos do payload são o TEXTO que o aluno entregou
    (`plugins[].editorfields[].text`) e o ENUNCIADO em HTML
    (`assignmentdata.activity`). Nenhum dos dois responde "eu já entreguei
    isso?" — o primeiro é o trabalho, o segundo já é resposta de `material`.

    Os tetos são por entrega e generosos de propósito: o cru varia com a forma
    da entrega (com texto online ou só arquivo), e o lado projetado é o que tem
    de ficar estável.
    """
    com_texto = status_de_entrega()
    so_arquivo = status_de_entrega(com_texto_online=False)
    c = _cliente(disciplinas_brutas, entregas_ptc3314, {EC1: com_texto, EC2: so_arquivo})

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    def _bytes(o):
        return len(json.dumps(o, ensure_ascii=False).encode())

    cru = _bytes(com_texto) + _bytes(so_arquivo)
    projetado = len(r.texto.encode())
    assert projetado <= cru // 4, (
        f"projeção de {projetado} B sobre {cru} B crus (duas consultas) — pouco "
        "corte para uma resposta que é uma linha por entrega"
    )
    # Quatro linhas: as duas consultadas mais as duas provas presenciais.
    assert projetado / 4 <= 260, f"{projetado / 4:.0f} B por entrega é texto demais"
    for gordo in ("ATP", "parâmetros distribuídos", "Tolerância: 48 h", "<p"):
        assert gordo not in r.texto, f"{gordo!r} atravessou a projeção"


def test_j12_nenhuma_url_de_arquivo_interno_sai(disciplinas_brutas, entregas_ptc3314):
    """J12 — Invariante 3, a mesma regra de `material`: o nome do arquivo sai,
    o endereço dele não. O payload de status traz `fileurl` do que o aluno
    enviou E do enunciado, e as duas são do webservice."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto


def test_j13_mais_entregas_que_o_teto_e_truncamento_declarado(disciplinas_brutas):
    """J13 — Invariante 7 do lado do CUSTO: são `TETO_CONSULTAS` idas ao Moodle
    por invocação, e PSI3472 tem 11 entregas (§9, 12/09). Cortar é legítimo;
    cortar calado não é."""
    muitas = {
        "courses": [
            {
                "id": 142036,
                "assignments": [
                    {
                        "id": 900_000 + i,
                        "cmid": 6_000_000 + i,
                        "name": f"Lição aulas {i}",
                        "duedate": 1789354740 + i * 86400,
                        "cutoffdate": 0,
                        "nosubmissions": 0,
                    }
                    for i in range(TETO_CONSULTAS + 3)
                ],
            }
        ],
        "warnings": [],
    }
    status = {900_000 + i: status_de_entrega() for i in range(TETO_CONSULTAS + 3)}
    c = _cliente(disciplinas_brutas, muitas, status)

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    consultas = [f for f, _ in c.chamadas if f.endswith("submission_status")]
    assert len(consultas) == TETO_CONSULTAS, f"{len(consultas)} idas ao Moodle"
    assert r.truncado is True
    assert str(TETO_CONSULTAS) in r.texto
    assert "3" in r.texto, "não disse quantas ficaram de fora"


def test_j14_sem_truncamento_nao_inventa_aviso(disciplinas_brutas, entregas_ptc3314):
    """J14 — o par do anterior: o aviso não pode ser decorativo."""
    r = ja_entreguei(
        _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues()),
        "PTC3314",
        agora=AGORA,
    )
    assert r.truncado is False


def test_j15_busca_sem_resultado_nao_vira_disciplina_vazia(
    disciplinas_brutas, entregas_ptc3314
):
    """J15 — Invariante 6: "nada com esse nome" e "nada para entregar" têm curas
    diferentes. Dizer o total é o que permite distinguir as duas."""
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    r = ja_entreguei(c, "PTC3314", entrega="EP7", agora=AGORA)

    assert r.vazio_por == "busca_sem_resultado"
    assert "EP7" in r.texto
    assert "4" in r.texto, "não disse quantas entregas a disciplina tem"
    assert not [f for f, _ in c.chamadas if f.endswith("submission_status")], (
        "gastou chamada de status para um filtro que não casou com nada"
    )


def test_j16_disciplina_sem_entrega_diz_o_que_nao_cobre(disciplinas_brutas):
    """J16 — 6 das 10 disciplinas do semestre não têm `assign` nenhum (§9,
    12/09). Vazio é comum aqui, e vazio mudo seria o falso "não tem nada"."""
    c = _cliente(disciplinas_brutas, {"courses": [], "warnings": []})

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert r.vazio_por == "sem_entregas"
    assert "questionário" in r.texto.lower(), (
        "não disse que quiz não passa por aqui — o calendário vê 6 disciplinas "
        "e `get_assignments` vê 4 (§9, 28/08)"
    )


def test_j17_erro_do_cliente_nao_vira_nao_entreguei(disciplinas_brutas, entregas_ptc3314):
    """J17 — o outro lado do bug do §9 de 28/08: falha de credencial não pode
    virar "você não entregou nada"."""

    def _explode(params):
        raise ErroMoodle("token recusado")

    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 8214},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "mod_assign_get_assignments": entregas_ptc3314,
            "mod_assign_get_submission_status": _explode,
        }
    )

    with pytest.raises(ErroMoodle):
        ja_entreguei(c, "PTC3314", agora=AGORA)


def test_j18_a_data_e_escrita_igual_a_do_o_que_vence(disciplinas_brutas, entregas_ptc3314):
    """J18 — o encaixe com a ferramenta que já existe.

    As duas respondem a mesma véspera: `o_que_vence` diz o que vence,
    `ja_entreguei` diz o que disso já foi. Se cada uma escrever a mesma data de
    um jeito, quem lê as duas respostas não sabe que falam do mesmo prazo.
    """
    from usp_mcp.moodle.o_que_vence import o_que_vence

    evento = {
        "events": [
            {
                "activityname": "EC-1 - Transitórios em LT",
                "timesort": 1789354740,
                "course": {"shortname": "PTC3314-2026"},
                "modulename": "assign",
                "url": "",
            }
        ]
    }
    vence = o_que_vence(ClienteFalso({"core_calendar_get_action_events_by_timesort": evento}))
    entregue = ja_entreguei(
        _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues()),
        "PTC3314",
        agora=AGORA,
    )

    assert "dom 13/09 23:59" in vence.texto
    assert "dom 13/09 23:59" in entregue.texto


def test_j19_a_saida_e_texto_curto(disciplinas_brutas, entregas_ptc3314):
    """J19 — critério 3 do §5: cabe em pouco contexto."""
    r = ja_entreguei(
        _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues()),
        "PTC3314",
        agora=AGORA,
    )
    assert len(r.texto) < 2_000
    assert not r.texto.lstrip().startswith(("{", "["))


def test_j20_nenhuma_escrita_e_emitida_nem_com_a_flag(
    disciplinas_brutas, entregas_ptc3314, monkeypatch
):
    """J20 — Invariante 1 na ferramenta: a vizinhança de nome desta função é
    `mod_assign_submit_for_grading`, e o que separa as duas é uma palavra."""
    monkeypatch.setenv("USP_MCP_ALLOW_WRITES", "1")
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    ja_entreguei(c, "PTC3314", agora=AGORA)

    assert set(f for f, _ in c.chamadas) == {
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "mod_assign_get_assignments",
        "mod_assign_get_submission_status",
    }


# --------------------------------------------------------------------------
# Invariante 7 no `warnings` da API — e a razão de os dois avisos serem
# CONTADOS SEPARADO, por origem.
#
# Esta ferramenta faz duas chamadas diferentes, e as duas devolvem `warnings`:
# `mod_assign_get_assignments` (a captura real de PTC3314 traz dois, de "sem
# direito de acesso") e `mod_assign_get_submission_status` (a captura de 15/09
# traz a chave no topo, vazia nesta conta). Os dois avisos NÃO dizem a mesma
# coisa, e é por isso que somá-los num número só seria perder informação:
#
#   - aviso da LISTA: pode existir entrega que nem apareceu. O que falta está
#     fora da tela, e quem lê tem de ir ao site.
#   - aviso do STATUS: a entrega apareceu, e o estado impresso na linha dela é
#     que pode estar incompleto. Quem lê tem de conferir AQUELA entrega.
#
# Um "3 atividade(s) não puderam ser lidas" juntaria "sumiu da lista" com "está
# na lista e o veredito é duvidoso" — que é exatamente o colapso que esta
# ferramenta existe para não cometer.
# --------------------------------------------------------------------------


def test_j21_warning_da_lista_de_entregas_vira_aviso(
    disciplinas_brutas, entregas_ptc3314
):
    """J21 — a fixture REAL traz dois `warnings` de "sem direito de acesso".

    Engoli-los faz a resposta listar 4 entregas como se fossem todas, na
    ferramenta em que quem lê decide ir dormir. "Não entreguei nada" e "não
    consegui ver" não podem sair como a mesma frase.
    """
    c = _cliente(disciplinas_brutas, entregas_ptc3314, _todos_entregues())

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "2 atividade" in r.texto, "os warnings da lista foram engolidos"
    assert "fora desta lista" in r.texto, (
        "disse que houve aviso mas não disse o que ele muda para quem lê"
    )


def test_j22_warning_do_status_de_uma_entrega_vira_aviso(disciplinas_brutas):
    """J22 — o lado que só esta ferramenta e `atrasadas` têm: o aviso que vem
    na resposta de UMA entrega, e que põe em dúvida a linha dela, não a lista."""
    limpas = entregas_falsas(
        [(142036, [(EC1, "EC-1", 1789354740, 0), (EC2, "EC-2", 1793500000, 0)])]
    )
    c = _cliente(
        disciplinas_brutas,
        limpas,
        {EC1: status_de_entrega(com_warning=True), EC2: status_de_entrega()},
    )

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "1 entrega" in r.texto, "o warning do status foi engolido"
    assert "não deu para ler" in r.texto, (
        "não disse que um estado lido pela metade pode virar veredito errado"
    )


def test_j23_os_dois_warnings_sao_contados_separado_e_nao_somados(
    disciplinas_brutas, entregas_ptc3314
):
    """J23 — o ponto da decisão. Dois avisos de origens diferentes, duas
    contagens. Um "3 atividade(s)" somado esconderia que uma das três é de
    outra natureza e tem outra cura."""
    c = _cliente(
        disciplinas_brutas,
        entregas_ptc3314,
        {EC1: status_de_entrega(com_warning=True), EC2: status_de_entrega()},
    )

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "2 atividade" in r.texto, "sumiu o aviso da lista"
    assert "1 entrega" in r.texto, "sumiu o aviso do status"
    assert "3 atividade" not in r.texto, (
        "as duas contagens foram somadas: 'não apareceu na lista' e 'apareceu "
        "e o estado é duvidoso' viraram o mesmo número"
    )


def test_j24_disciplina_sem_entrega_com_warning_nao_diz_que_nao_ha_nada(
    disciplinas_brutas,
):
    """J24 — o vazio é o caso mais perigoso dos três.

    `courses` vazio com `warnings` cheio é literalmente "o token não alcançou
    esta disciplina", e a resposta de hoje é "esta disciplina não tem nenhuma
    tarefa de entrega". Lista vazia que parece "não tem nada" é o que o
    Invariante 7 proíbe pelo nome.
    """
    vazio_com_aviso = entregas_falsas([], com_warning=True)
    c = _cliente(disciplinas_brutas, vazio_com_aviso)

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert r.vazio_por == "sem_entregas"
    assert "1 atividade" in r.texto, (
        "o vazio saiu mudo: quem lê entende 'não tem nada para entregar' onde "
        "o Moodle disse 'não te deixei ver'"
    )


def test_j25_sem_warning_nenhum_aviso_de_credencial_e_inventado(disciplinas_brutas):
    """J25 — o par dos quatro anteriores, pelo mesmo motivo de J14 existir: um
    aviso que aparece sempre não avisa nada, e treina quem lê a ignorá-lo."""
    limpas = entregas_falsas([(142036, [(EC1, "EC-1", 1789354740, 0)])])
    c = _cliente(disciplinas_brutas, limpas, {EC1: status_de_entrega()})

    r = ja_entreguei(c, "PTC3314", agora=AGORA)

    assert "credencial" not in r.texto, (
        "inventou aviso de credencial numa resposta em que a API não avisou nada"
    )
