"""DI1-DI14 — "quais matérias eu tenho?".

Até 14/09/2026 este servidor não respondia essa pergunta, e o único jeito de
alguém ver as próprias siglas era **provocar um erro**: pedir `material` de uma
sigla que não existe, para o Invariante 7 de `resolver` cuspir a lista inteira.

A ferramenta é a mais barata do projeto porque `disciplinas.carregar` já busca e
já cacheia essa lista para traduzir sigla em `courseid` — **nenhuma função nova
entra na allowlist**, e DI1 é a asserção que trava isso.

**A decisão que este arquivo pede para julgar é o que fazer com as matrículas
antigas.** A fixture real tem 74, e só 10 são do semestre em andamento; ao vivo,
em 14/09, o dono mediu 45 matrículas com 7 notas lançadas. Os dois números
discordam e nenhum dos dois muda o desenho: em qualquer um deles a maioria é de
semestre passado, e despejar a lista inteira com nome e período responde mal a
"quais matérias eu tenho?". O corte é de DETALHE e nunca de EXISTÊNCIA — DI4 é
quem garante que nenhuma sigla some, e DI5 que o corte é declarado com a cura.

Procedência do insumo: `users_courses.json` é **fixture REAL**, capturada e
higienizada (§3.3). Por causa da higienização, `fullname` vem embaralhado — daí
nenhum teste daqui afirmar o nome de uma disciplina; o que se afirma é a sigla,
o rótulo e o período, que a higienização preserva.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from tests.moodle.conftest import FIXTURE_DISCIPLINAS, ClienteFalso
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle, MoodleIndisponivel
from usp_mcp.moodle.projecao import FUSO_SAO_PAULO

pytestmark = pytest.mark.contrato

USERID = 8214
# No meio do segundo semestre de 2026: as 10 matrículas com `enddate` em
# dezembro estão em andamento, e as 62 com `enddate` no passado, encerradas.
AGORA = datetime(2026, 9, 14, 16, 0, tzinfo=FUSO_SAO_PAULO)

# Os dois casos que a fixture real tem e que nenhum payload escrito à mão teria
# pensado em ter: matrícula com `enddate: 0`. Uma delas nem segue o formato
# "SIGLA-ano" do `shortname` (é uma atividade de extensão).
SEM_PERIODO = ("AEX-IF-00020.01", "MAT3457-2024")


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas):
    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": disciplinas_brutas,
        }
    )


def _funcoes(cliente):
    return [f for f, _ in cliente.chamadas]


# --------------------------------------------------------------------------
# O que a ferramenta custa
# --------------------------------------------------------------------------


def test_di1_nenhuma_funcao_nova_e_chamada(disciplinas_brutas):
    """DI1 — a ferramenta inteira sai das duas chamadas que a resolução de sigla
    já fazia.

    Asserção sobre as funções ENVIADAS, e não sobre a saída: o dublê responderia
    igual a qualquer terceira função, e é justamente uma terceira função que esta
    ferramenta não pode ter. Se alguém acrescentar uma, o vermelho aparece aqui
    antes de aparecer na allowlist.
    """
    c = _cliente(disciplinas_brutas)

    dis.minhas_disciplinas(c, momento=AGORA)

    assert _funcoes(c) == [
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
    ]


def test_di2_a_segunda_pergunta_nao_gasta_chamada_nenhuma(disciplinas_brutas):
    """DI2 — o cache de `carregar` (TTL de um semestre) vale para esta também.

    Matrícula não muda entre duas perguntas, e o Invariante 5 pede TTL colado na
    taxa de mudança do dado. Sem isto, perguntar duas vezes "quais matérias eu
    tenho" rebaixaria 98 kB de novo.
    """
    c = _cliente(disciplinas_brutas)

    dis.minhas_disciplinas(c, momento=AGORA)
    dis.minhas_disciplinas(c, momento=AGORA)

    assert len(c.chamadas) == 2, [f for f, _ in c.chamadas]


# --------------------------------------------------------------------------
# A decisão: o que acontece com as matrículas antigas
# --------------------------------------------------------------------------


def test_di3_as_do_semestre_em_andamento_vem_primeiro_e_completas(disciplinas_brutas):
    """DI3 — quem pergunta "quais matérias eu tenho" está perguntando do agora.

    As 10 do semestre corrente saem com sigla, rótulo e período; é a seção que
    responde a pergunta, e ela vem antes de qualquer coisa sobre semestre
    passado.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert r.em_andamento == 10, r.texto
    assert r.total == 74
    cabeca = r.texto.split("Encerradas")[0]
    for sigla in ("PTC3314", "PSI3323", "PSI3472", "PME3344", "PTC3360"):
        assert sigla in cabeca, f"{sigla} não está na seção do semestre corrente"


def test_di4_nenhuma_sigla_some_da_resposta(disciplinas_brutas):
    """DI4 — Invariante 7 no ponto exato em que esta ferramenta poderia falhar.

    O corte é de DETALHE, nunca de EXISTÊNCIA: as 74 matrículas continuam
    nomeadas, as antigas em bloco compacto. Uma sigla que suma daqui é uma
    disciplina que quem pergunta não tem como descobrir que existe — e era
    exatamente esse o estado anterior à ferramenta, que obrigava a provocar um
    erro em `material` para ver a lista.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    faltando = [
        curso["shortname"]
        for curso in disciplinas_brutas
        if curso["shortname"] not in r.texto
    ]
    assert not faltando, f"rótulos que sumiram da resposta: {faltando}"


def test_di5_o_corte_de_detalhe_e_declarado_com_a_cura(disciplinas_brutas):
    """DI5 — Invariante 7 outra vez: cortou, declara, e diz como ver o resto.

    O que some das encerradas é o nome e o período, não a existência — e a
    resposta precisa dizer as duas coisas, senão quem lê conclui que o
    e-Disciplinas não sabe mais nada sobre aquelas matrículas.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert r.encerradas == 62
    assert "62" in r.texto
    assert "todas" in r.texto, "não nomeou o parâmetro que mostra o resto"


def test_di6_todas_abre_as_encerradas_e_o_padrao_nao(disciplinas_brutas):
    """DI6 — o parâmetro que a DI5 promete existe e faz o que promete.

    O nome sai da própria fixture em vez de escrito à mão: a fixture é
    higienizada e o `fullname` vem embaralhado (§3.3), então afirmar um nome
    literal aqui seria afirmar o embaralhamento.
    """
    antiga = [
        curso
        for curso in disciplinas_brutas
        if curso["shortname"] == "PMT3100-104-2023"
    ][0]

    c = _cliente(disciplinas_brutas)
    resumida = dis.minhas_disciplinas(c, momento=AGORA)
    completa = dis.minhas_disciplinas(c, todas=True, momento=AGORA)

    assert antiga["fullname"] not in resumida.texto
    assert antiga["fullname"] in completa.texto
    assert len(completa.texto) > len(resumida.texto)


def test_di7_matricula_sem_periodo_nao_vira_encerrada(disciplinas_brutas):
    """DI7 — `enddate: 0` é "o e-Disciplinas não declarou", nunca "acabou".

    As duas da fixture real são o caso que nenhum payload escrito à mão teria
    pensado em ter. Chamá-las de encerradas seria inventar um fato sobre a vida
    acadêmica de quem pergunta; escondê-las seria o falso vazio do Invariante 7.
    Elas saem em bloco próprio, com o motivo.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert r.sem_periodo == 2
    bloco = r.texto.split("sem período")[1]
    for rotulo in SEM_PERIODO:
        assert rotulo in bloco, f"{rotulo} não está no bloco de sem período"


def test_di8_a_saida_diz_de_onde_sai_o_em_andamento(disciplinas_brutas):
    """DI8 — Invariante 6: a resposta diz o que ela NÃO sabe.

    "Em andamento" aqui é a data que o e-Disciplinas declara para o espaço da
    disciplina, e não a matrícula oficial no JupiterWeb. Trancamento,
    cancelamento e disciplina que o professor nunca datou produzem divergência,
    e quem lê precisa saber disso antes de tratar a lista como matrícula.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert "e-Disciplinas" in r.texto
    assert "matrícula oficial" in r.texto.lower() or "jupiter" in r.texto.lower()


def test_di9_o_periodo_traz_o_ano(disciplinas_brutas):
    """DI9 — e por que aqui a grafia NÃO é a de `texto.formatar_data`.

    J18 pede uma grafia só para a mesma coisa, e esta não é a mesma coisa:
    `formatar_data` escreve prazo ("dom 06/09 23:59"), curto de propósito porque
    o prazo é de agora. Um período de vigência de 2023 sem o ano seria uma data
    que não localiza nada — a única coisa que distingue PMT3100 de PMT3130 numa
    lista de sete anos de matrícula é o ano.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, todas=True, momento=AGORA)

    assert "2023" in r.texto
    assert "/2026" in r.texto


# --------------------------------------------------------------------------
# Os modos de falha
# --------------------------------------------------------------------------


def test_di10_erro_do_cliente_sobe_e_nao_vira_lista_vazia(disciplinas_brutas):
    """DI10 — o bug do §9 de 28/08 aplicado a esta ferramenta.

    Token recusado e "você não tem matrícula nenhuma" são indistinguíveis para
    quem lê, e têm curas opostas. O erro sobe.
    """
    def _explode(_params):
        raise MoodleIndisponivel("o e-Disciplinas não respondeu")

    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": _explode,
        }
    )

    with pytest.raises(ErroMoodle):
        dis.minhas_disciplinas(c, momento=AGORA)


def test_di11_conta_sem_matricula_nenhuma_diz_por_que_esta_vazia():
    """DI11 — zero matrícula é resposta legítima, e rotulada.

    É o mesmo `vazio_por` de `o_que_vence`: lista vazia muda aqui seria
    exatamente o desfecho do userid errado de 28/08, que devolve `[]` com HTTP
    200.
    """
    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": [],
        }
    )

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert r.total == 0
    assert r.vazio_por == "sem_matriculas"
    assert len(r.texto) > 40, "vazio saiu mudo"


# --------------------------------------------------------------------------
# A projeção
# --------------------------------------------------------------------------


def test_di12_a_projecao_descarta_a_maior_parte_do_payload(disciplinas_brutas):
    """DI12 — 98 kB de cru viram alguns kB de texto, e o que sai é medido aqui.

    O cru é **fixture real** (98.171 B), então esta razão mede a resposta que o
    e-Disciplinas devolve de verdade — ao contrário das razões de `avisos` e
    `o_que_mudou`, que medem payload escrito à mão.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, momento=AGORA)

    cru = FIXTURE_DISCIPLINAS.stat().st_size
    assert len(r.texto.encode("utf-8")) < cru / 20, (
        f"{len(r.texto.encode('utf-8'))} B de texto para {cru} B de cru"
    )


def test_di13_o_que_a_projecao_descarta_nao_reaparece_no_texto(disciplinas_brutas):
    """DI13 — `summary`, `courseimage` e `progress` são quase todo o payload e
    não respondem nada da pergunta.

    A URL da imagem do curso é `pluginfile.php`, a mesma família de endereço que
    o Invariante 3 mantém fora de toda resposta deste servidor.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, todas=True, momento=AGORA)

    assert "pluginfile" not in r.texto
    assert "courseimage" not in r.texto
    # Um pedaço do `summary` da primeira matrícula: se ele aparecer, a projeção
    # deixou passar o campo mais gordo da resposta.
    assert disciplinas_brutas[0]["summary"][:40] not in r.texto


def test_di14_o_courseid_nao_vaza_para_quem_le(disciplinas_brutas):
    """DI14 — o número interno do Moodle não é vocabulário de quem pergunta.

    Quem lê responde à próxima pergunta com a SIGLA (é o que `material`,
    `notas`, `avisos` e as outras aceitam); o `courseid` só existiria na saída
    para ser copiado para um lugar que não o aceita.
    """
    c = _cliente(disciplinas_brutas)

    r = dis.minhas_disciplinas(c, todas=True, momento=AGORA)

    assert str(disciplinas_brutas[0]["id"]) not in r.texto


def test_di15_matricula_que_ainda_nao_comecou_nao_e_chamada_de_em_andamento():
    """DI15 — o quarto desfecho, e o único que a fixture real não tem.

    Matrícula para o semestre que vem existe antes de o semestre começar. Ela
    não está em andamento (a aula não começou), não está encerrada e tem período
    declarado — os três blocos anteriores estariam mentindo, cada um do seu
    jeito.

    O payload deste caso é **escrito à mão** e é minúsculo de propósito: só os
    quatro campos que a projeção lê. Os outros 25 já são exercitados contra a
    fixture real nos testes acima.
    """
    bruto = [
        {
            "id": 999001,
            "shortname": "PTC3450-2027",
            "fullname": "Disciplina do semestre que vem",
            "startdate": int(datetime(2027, 3, 1, tzinfo=FUSO_SAO_PAULO).timestamp()),
            "enddate": int(datetime(2027, 7, 1, tzinfo=FUSO_SAO_PAULO).timestamp()),
        }
    ]
    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": bruto,
        }
    )

    r = dis.minhas_disciplinas(c, momento=AGORA)

    assert r.em_andamento == 0
    assert r.encerradas == 0
    assert "PTC3450" in r.texto
