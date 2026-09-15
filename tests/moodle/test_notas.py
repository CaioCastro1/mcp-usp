"""N1-N18 — "como estou de nota?", nas duas visões que o e-Disciplinas tem.

UMA ferramenta com parâmetro opcional, e não duas: a justificativa está no §9 e
no módulo. O que estes testes travam é a consequência dela — **uma função por
invocação, escolhida pelo código e não varrida** (§3.1). Com disciplina vai
`gradereport_user_get_grade_items`; sem disciplina vai
`gradereport_overview_get_course_grades`. Nunca as duas (N3).

Os `courseid` vêm da fixture real de matrículas; as respostas de nota são
escritas à mão a partir da forma documentada, com a ressalva de procedência no
`conftest` e no §9. Nota é dado pessoal do §3.3, e é por isso que metade deste
arquivo é sobre o que NÃO pode sair: nome de pessoa, comentário do professor, e
nota de terceiro.
"""
from __future__ import annotations

import json

import pytest

from tests.moodle.conftest import (
    ClienteFalso,
    _item_de_nota,
    itens_de_nota_falsos,
    notas_gerais_falsas,
)
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle
from usp_mcp.moodle.notas import notas

pytestmark = pytest.mark.contrato

USERID = 8214
PTC3314 = 142036
PSI3323 = 142033


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas, *, geral=None, itens=None):
    respostas = {
        "core_webservice_get_site_info": {"userid": USERID},
        "core_enrol_get_users_courses": disciplinas_brutas,
    }
    if geral is not None:
        respostas["gradereport_overview_get_course_grades"] = geral
    if itens is not None:
        respostas["gradereport_user_get_grade_items"] = itens
    return ClienteFalso(respostas)


def _funcoes(cliente):
    return [f for f, _ in cliente.chamadas]


# --------------------------------------------------------------------------
# A escolha da função — §3.1, e o default que o catálogo registra como incógnita
# --------------------------------------------------------------------------


def test_n1_sem_disciplina_usa_a_visao_geral_e_so_ela(disciplinas_brutas):
    """N1 — "como estou de nota?" sem disciplina nomeada é a pergunta do
    `overview`: todos os cursos, três campos por linha."""
    c = _cliente(
        disciplinas_brutas, geral=notas_gerais_falsas([(PTC3314, "8,50")])
    )

    notas(c)

    assert "gradereport_overview_get_course_grades" in _funcoes(c)
    assert "gradereport_user_get_grade_items" not in _funcoes(c)


def test_n2_com_disciplina_usa_a_visao_de_item_e_so_ela(disciplinas_brutas):
    """N2 — "como estou em PTC3314?" é a outra função, com o `courseid`
    resolvido da sigla. Asserção sobre o parâmetro ENVIADO: o dublê devolveria a
    mesma resposta para qualquer id."""
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())

    notas(c, disciplina="PTC3314")

    assert "gradereport_user_get_grade_items" in _funcoes(c)
    assert "gradereport_overview_get_course_grades" not in _funcoes(c)
    assert c.params_de("gradereport_user_get_grade_items")["courseid"] == PTC3314


def test_n3_uma_funcao_de_nota_por_invocacao(disciplinas_brutas):
    """N3 — a Regra de Ouro (§3.1) aplicada ao parâmetro opcional: ele escolhe
    entre duas funções, nunca chama as duas "para ter as duas visões"."""
    c = _cliente(
        disciplinas_brutas,
        geral=notas_gerais_falsas([(PTC3314, "8,50")]),
        itens=itens_de_nota_falsos(),
    )

    notas(c, disciplina="PTC3314")

    de_nota = [f for f in _funcoes(c) if f.startswith("gradereport_")]
    assert len(de_nota) == 1, f"chamou {de_nota}"


def test_n4_o_userid_vai_explicito_e_e_o_derivado_do_token(disciplinas_brutas):
    """N4 — as duas funções têm `userid [opt=0]`, e o que o 0 faz **não foi
    verificado** (catálogo, Apêndice B item 4). Depender de um default não
    verificado é prometer o que não se sabe.

    Pior: `gradereport_user_get_grade_items` devolve "a lista de itens de nota
    para os usuários de um curso" — com capacidade de correção e sem `userid`,
    ela traria terceiros. O id derivado do token fecha as duas portas de uma vez,
    e ele não custa chamada nova: `carregar` já o buscou para resolver a sigla.
    """
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())
    notas(c, disciplina="PTC3314")
    assert c.params_de("gradereport_user_get_grade_items")["userid"] == USERID

    dis.limpar_cache()
    c2 = _cliente(disciplinas_brutas, geral=notas_gerais_falsas([(PTC3314, "8,50")]))
    notas(c2)
    assert c2.params_de("gradereport_overview_get_course_grades")["userid"] == USERID


def test_n5_courseid_zero_nunca_e_enviado(disciplinas_brutas):
    """N5 — o outro default que o catálogo marca como incógnita: `courseid=0`
    em `grade_items` "pode ser erro, pode ser todos os cursos e uma resposta
    gigante". Este projeto nunca vai descobrir por acidente."""
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())

    notas(c, disciplina="PTC3314")

    assert c.params_de("gradereport_user_get_grade_items")["courseid"] != 0


def test_n6_sigla_que_nao_resolve_nao_gasta_chamada_de_nota(disciplinas_brutas):
    """N6 — mesma regra de `material` e de `ja_entreguei`."""
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())

    with pytest.raises(ErroMoodle) as e:
        notas(c, disciplina="XYZ9999")

    assert "XYZ9999" in str(e.value)
    assert not [f for f in _funcoes(c) if f.startswith("gradereport_")]


# --------------------------------------------------------------------------
# A visão geral
# --------------------------------------------------------------------------


def test_n7_a_visao_geral_traduz_courseid_em_sigla(disciplinas_brutas):
    """N7 — `overview` devolve `courseid` e nota, e mais nada: sem a tradução,
    a resposta é uma tabela de números contra números."""
    c = _cliente(
        disciplinas_brutas,
        geral=notas_gerais_falsas([(PTC3314, "8,50"), (PSI3323, "7,00")]),
    )

    r = notas(c)

    assert "PTC3314" in r.texto and "8,50" in r.texto
    assert "PSI3323" in r.texto and "7,00" in r.texto
    assert str(PTC3314) not in r.texto, "o courseid cru vazou para a saída"


def test_n8_curso_sem_nota_lancada_e_contado_e_nao_listado(disciplinas_brutas):
    """N8 — Invariante 7. O e-Disciplinas devolve as matrículas TODAS, e a
    maioria do semestre em andamento ainda não tem nota: listar 70 linhas de
    "-" enterra as que têm resposta, e omiti-las caladas mente sobre o total."""
    c = _cliente(
        disciplinas_brutas,
        geral=notas_gerais_falsas(
            [(PTC3314, "8,50"), (PSI3323, None), (142034, None)]
        ),
    )

    r = notas(c)

    assert "PSI3323" not in r.texto
    assert "2" in r.texto, "não disse quantas ficaram de fora"
    assert "não têm nota lançada" in r.texto


def test_n9_nenhuma_nota_lancada_e_resposta_rotulada(disciplinas_brutas):
    """N9 — o bug do §9 de 28/08 aplicado a nota: "nenhuma nota lançada ainda" e
    "a credencial não leu nada" são indistinguíveis se a saída não rotula."""
    c = _cliente(
        disciplinas_brutas, geral=notas_gerais_falsas([(PTC3314, None)])
    )

    r = notas(c)

    assert r.vazio_por == "sem_nota_lancada"
    assert "nenhuma" in r.texto.lower()


# --------------------------------------------------------------------------
# A visão de uma disciplina
# --------------------------------------------------------------------------


def test_n10_item_a_item_com_nota_e_peso(disciplinas_brutas):
    """N10 — é a única visão que responde "como estou NESSA disciplina": nota de
    8,5 em algo que vale 25% e nota de 8,5 em algo que vale 5% não são a mesma
    resposta."""
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())

    r = notas(c, disciplina="PTC3314")

    assert "EC-1 - Transitórios em LT" in r.texto
    assert "8,50" in r.texto
    assert "25,00 %" in r.texto, "não disse quanto o item pesa"

    # De quanto era a nota, esta ferramenta não diz: o e-Disciplinas não manda o
    # máximo do item (captura de 15/09, 20 itens, nenhum com `grademax` — F8
    # trava a leitura e F2 trava a montagem). O que este teste guarda é que a
    # saída não INVENTA o máximo, seja lendo campo que não existe, seja
    # derivando um de `percentageformatted`.
    assert " de " not in r.texto.split("peso")[0], (
        "apareceu um máximo que o e-Disciplinas não mandou:\n" + r.texto
    )


def test_n11_o_total_do_curso_e_rotulado(disciplinas_brutas):
    """N11 — o item `itemtype: "course"` chega com `itemname` VAZIO: é a nota
    final da disciplina, e sem rótulo ela vira uma linha sem nome, que é a mais
    importante da lista."""
    c = _cliente(
        disciplinas_brutas,
        itens=itens_de_nota_falsos(
            [
                _item_de_nota(),
                _item_de_nota(
                    itemname="", itemtype="course", gradeformatted="7,80",
                    weightformatted="-", feedback="",
                ),
            ]
        ),
    )

    r = notas(c, disciplina="PTC3314")

    assert "7,80" in r.texto
    assert "total" in r.texto.lower() or "final" in r.texto.lower()


def test_n12_nota_oculta_pelo_professor_nao_vira_sem_nota(disciplinas_brutas):
    """N12 — Invariante 6. `gradeishidden` é o professor escondendo a nota até
    liberar; "ainda não corrigiram" e "corrigiram e não liberaram" têm curas
    diferentes, e a segunda não é perguntar de novo amanhã."""
    c = _cliente(
        disciplinas_brutas,
        itens=itens_de_nota_falsos(
            [_item_de_nota(gradeishidden=True, gradeformatted="-", graderaw=None)]
        ),
    )

    r = notas(c, disciplina="PTC3314")

    assert "ocult" in r.texto.lower()


# --------------------------------------------------------------------------
# Dado pessoal (§3.3) e projeção medida
# --------------------------------------------------------------------------


def test_n13_nome_de_pessoa_nunca_sai(disciplinas_brutas):
    """N13 — `userfullname` e `useridnumber` (o número USP) vêm no payload e não
    respondem nota nenhuma. Quem perguntou já sabe o próprio nome."""
    c = _cliente(disciplinas_brutas, itens=itens_de_nota_falsos())

    r = notas(c, disciplina="PTC3314")

    assert "Gunthen" not in r.texto
    assert "12345678" not in r.texto


def test_n14_nota_de_terceiro_nao_e_impressa(disciplinas_brutas):
    """N14 — um token com capacidade de correção (monitoria, PAE — o Apêndice B
    registra que ninguém verificou se é o caso) recebe um bloco `usergrades` por
    aluno. Imprimir o dos outros seria vazar nota alheia pelo contexto de um
    modelo. O `userid` explícito já fecha essa porta; isto trava a segunda.
    """
    outro = {
        "courseid": PTC3314,
        "userid": 9999,
        "userfullname": "Colega de Turma",
        "useridnumber": "87654321",
        "maxdepth": 2,
        "gradeitems": [_item_de_nota(gradeformatted="10,00")],
    }
    c = _cliente(
        disciplinas_brutas, itens=itens_de_nota_falsos(extras=[outro])
    )

    r = notas(c, disciplina="PTC3314")

    assert "Colega de Turma" not in r.texto
    assert "10,00" not in r.texto
    assert "1" in r.texto and "outro" in r.texto.lower(), (
        "ignorou o bloco de terceiro em SILÊNCIO — Invariante 7:\n" + r.texto
    )


def test_n15_a_projecao_descarta_o_comentario_do_professor_declarando(
    disciplinas_brutas,
):
    """N15 — a medida que justifica a fronteira.

    O campo gordo de `grade_items` é o `feedback`: o comentário do professor em
    HTML, que responde "o que eu errei" e não "como estou de nota". Ele é
    descartado **com contagem**, porque sumir com ele calado faria a ferramenta
    esconder que existe comentário para ler.
    """
    itens = [_item_de_nota(id=i, iteminstance=i) for i in range(5)]
    bruto = itens_de_nota_falsos(itens)
    c = _cliente(disciplinas_brutas, itens=bruto)

    r = notas(c, disciplina="PTC3314")

    cru = len(json.dumps(bruto, ensure_ascii=False).encode())
    projetado = len(r.texto.encode())
    assert projetado <= cru // 5, f"{projetado} B sobre {cru} B crus"
    assert "coeficiente de reflexão" not in r.texto, "o comentário atravessou"
    assert "<p" not in r.texto
    assert "5" in r.texto and "coment" in r.texto.lower(), (
        "descartou o comentário sem dizer que ele existe:\n" + r.texto
    )


def test_n16_warning_do_moodle_vira_aviso(disciplinas_brutas):
    """N16 — Invariante 7: item que a credencial não pôde ler não desaparece da
    contagem. Mesma regra dos `warnings` de `mod_assign_get_assignments`."""
    c = _cliente(
        disciplinas_brutas, itens=itens_de_nota_falsos(com_warning=True)
    )

    r = notas(c, disciplina="PTC3314")

    assert "⚠" in r.texto
    assert "não pôde" in r.texto or "não puderam" in r.texto


def test_n17_erro_do_cliente_nao_vira_sem_nota(disciplinas_brutas):
    """N17 — o outro lado do bug do §9 de 28/08."""

    def _explode(params):
        raise ErroMoodle("token recusado")

    c = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": USERID},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "gradereport_overview_get_course_grades": _explode,
        }
    )

    with pytest.raises(ErroMoodle):
        notas(c)


def test_n18_saida_curta_e_sem_escrita_nem_com_a_flag(disciplinas_brutas, monkeypatch):
    """N18 — critério 3 do §5 mais o Invariante 1: a família `gradereport_` tem
    duas funções de ESCRITA (`*_view_grade_report`, que dispara evento), e o que
    as separa das nossas é o pedaço `get_`."""
    monkeypatch.setenv("USP_MCP_ALLOW_WRITES", "1")
    c = _cliente(
        disciplinas_brutas,
        geral=notas_gerais_falsas([(PTC3314, "8,50"), (PSI3323, "7,00")]),
    )

    r = notas(c)

    assert len(r.texto) < 2_000
    assert set(_funcoes(c)) == {
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "gradereport_overview_get_course_grades",
    }
