"""A1-A20 — "o professor avisou alguma coisa?", que é o fórum e não o calendário.

O que o calendário do Moodle não sabe está no fórum: a `notas/fase1-moodle.md`
registra que o anúncio da "Prova Prática P1" de PSI3323 estava lá e a prova
**não** estava no calendário da disciplina. `o_que_vence` responde o que tem
prazo; esta responde o que foi dito.

**A armadilha que este arquivo trava primeiro.** O comparável `loyaniu/moodle-mcp`
chama `mod_forum_get_discussions`, que **não existe** no Moodle 5.0 da USP — a
função é `mod_forum_get_forum_discussions` (medido em 14/09, e registrado no
ROADMAP). Copiar a lista dele sem conferir dá erro em produção e verde na suíte,
porque um dublê responde a qualquer nome que o teste tenha previsto. A19 é a
asserção que impede isso de entrar por engano.

**Fórum é o lugar do projeto onde o payload é escrito por terceiros.** Cada
discussão chega com `userfullname`, `usermodifiedfullname` e duas URLs de foto.
Nada disso sai (A6), e a fixture os traz de propósito: uma projeção só prova que
descarta nome de gente se nome de gente chegar a estar na entrada.

Procedência: as duas respostas de fórum são **escritas à mão** — a ressalva
inteira está no `conftest`, ao lado dos construtores. O que é real são os `id` e
os `name` dos dois fóruns, que vêm de `course_contents_ptc3314.json`; é por isso
que o `forumid` ENVIADO é conferido contra um id de verdade.
"""
from __future__ import annotations

import json

import pytest

from tests.moodle.conftest import (
    CMID_AVISOS,
    FORUM_AVISOS,
    FORUM_DISCUSSAO,
    ClienteFalso,
    discussao_falsa,
    discussoes_falsas,
    foruns_falsos,
)
from usp_mcp.moodle import avisos as av
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle, MoodleIndisponivel

pytestmark = pytest.mark.contrato

USERID = 8214
PTC3314 = 142036


@pytest.fixture(autouse=True)
def _cache_limpo():
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(disciplinas_brutas, *, foruns=None, discussoes=None):
    """Dublê das três funções. `discussoes` é um dicionário forumid → resposta,
    porque a mesma função é chamada uma vez por fórum e responder o mesmo para
    todos esconderia um `forumid` trocado."""
    respostas = {
        "core_webservice_get_site_info": {"userid": USERID},
        "core_enrol_get_users_courses": disciplinas_brutas,
        "mod_forum_get_forums_by_courses": (
            foruns_falsos() if foruns is None else foruns
        ),
    }
    por_forum = (
        {FORUM_AVISOS: discussoes_falsas(), FORUM_DISCUSSAO: discussoes_falsas()}
        if discussoes is None
        else discussoes
    )
    respostas["mod_forum_get_forum_discussions"] = lambda p: por_forum[
        int(p["forumid"])
    ]
    return ClienteFalso(respostas)


def _funcoes(cliente):
    return [f for f, _ in cliente.chamadas]


def _forumids(cliente):
    return [
        int(p["forumid"])
        for f, p in cliente.chamadas
        if f == "mod_forum_get_forum_discussions"
    ]


# --------------------------------------------------------------------------
# A função certa, o escopo certo, e o id certo
# --------------------------------------------------------------------------


def test_a19_a_funcao_e_get_forum_discussions_e_nunca_get_discussions(
    disciplinas_brutas,
):
    """A19 — a armadilha medida em 14/09.

    `mod_forum_get_discussions` **não existe** no Moodle 5.0 da USP, e o
    comparável a chama. Um dublê não distingue as duas: quem escrever o nome
    errado no código e no teste tem verde aqui e erro na primeira pergunta real.
    Esta asserção é sobre o nome ENVIADO, contra o nome que o e-Disciplinas
    confirmou ter.
    """
    c = _cliente(disciplinas_brutas)

    av.avisos(c, "PTC3314")

    chamadas = _funcoes(c)
    assert "mod_forum_get_forum_discussions" in chamadas
    assert "mod_forum_get_discussions" not in chamadas, (
        "chamou a função do comparável, que não existe neste Moodle"
    )


def test_a1_o_escopo_e_a_disciplina_resolvida(disciplinas_brutas):
    """A1 — `courseids` é opcional na API (`[opt=[]]` → TODOS os cursos), e sem
    escopo esta chamada traria as 74 matrículas. Asserção sobre o parâmetro
    enviado: o dublê devolveria os mesmos dois fóruns para qualquer id."""
    c = _cliente(disciplinas_brutas)

    av.avisos(c, "PTC3314")

    assert c.params_de("mod_forum_get_forums_by_courses") == {
        "courseids[0]": PTC3314
    }


def test_a2_sigla_que_nao_resolve_nao_gasta_chamada_de_forum(disciplinas_brutas):
    """A2 — mesma regra de `material` e `ja_entreguei`: consultar o Moodle para
    descobrir que a pergunta estava errada é gastar chamada da conta do dono à
    toa, e cada chamada fica no log dela."""
    c = _cliente(disciplinas_brutas)

    with pytest.raises(ErroMoodle) as erro:
        av.avisos(c, "XYZ9999")

    assert "XYZ9999" in str(erro.value)
    assert "mod_forum_get_forums_by_courses" not in _funcoes(c)


def test_a3_o_forumid_enviado_e_o_id_do_forum_e_nao_o_cmid(disciplinas_brutas):
    """A3 — os dois números chegam lado a lado na mesma resposta (`id` e
    `cmid`), e trocar um pelo outro produz uma chamada que o Moodle aceita e
    responde sobre OUTRA coisa. A fixture usa os dois valores reais de PTC3314
    justamente para que a troca seja visível."""
    c = _cliente(disciplinas_brutas)

    av.avisos(c, "PTC3314")

    assert FORUM_AVISOS in _forumids(c)
    assert CMID_AVISOS not in _forumids(c), "mandou o cmid no lugar do forumid"


def test_a16_page_e_perpage_vao_explicitos(disciplinas_brutas):
    """A16 — `perpage [opt=0]` e `page [opt=-1]`, e o que esses defaults fazem
    **não foi verificado** (catálogo §3.6). Mesma decisão de `notas` com o
    `userid [opt=0]`: depender de default não verificado é prometer o que não se
    sabe, e aqui o modo de falha é trazer o fórum inteiro."""
    c = _cliente(disciplinas_brutas)

    av.avisos(c, "PTC3314")

    params = c.params_de("mod_forum_get_forum_discussions")
    assert params["perpage"] == av.DISCUSSOES_POR_FORUM
    assert params["page"] == 0


# --------------------------------------------------------------------------
# O que não gasta chamada, e o que não sai na saída
# --------------------------------------------------------------------------


def test_a4_forum_sem_topico_nao_gasta_chamada_mas_aparece(disciplinas_brutas):
    """A4 — `numdiscussions: 0` é o `nosubmissions` desta ferramenta: consultar
    gastaria uma ida para receber lista vazia. Não consultar não é sumir
    (Invariante 7) — o fórum aparece com o motivo."""
    vazio = foruns_falsos(com_discussao=False)
    vazio.append(
        {
            "id": 301999,
            "cmid": 6372999,
            "course": PTC3314,
            "type": "general",
            "name": "Dúvidas gerais",
            "numdiscussions": 0,
        }
    )
    # O dublê SABE responder pelo fórum vazio de propósito: se ele explodisse,
    # a sabotagem que consulta o fórum vazio reprovaria por KeyError do teste em
    # vez de pela asserção — vermelho pelo motivo errado ainda é vermelho fraco.
    c = _cliente(
        disciplinas_brutas,
        foruns=vazio,
        discussoes={
            FORUM_AVISOS: discussoes_falsas(),
            301999: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert 301999 not in _forumids(c), "gastou chamada num fórum sem tópico"
    assert "Dúvidas gerais" in r.texto
    assert "nenhum tópico" in r.texto.lower()


def test_a4b_site_que_nao_diz_a_contagem_e_consultado(disciplinas_brutas):
    """A4b — ausência de `numdiscussions` é "não sei", nunca zero.

    O erro tem de cair para o lado de gastar uma chamada, não para o lado de
    declarar vazio um fórum que ninguém leu — que é o falso "não tem nada" do
    Invariante 6.
    """
    c = _cliente(disciplinas_brutas, foruns=foruns_falsos(sem_contagem=True))

    av.avisos(c, "PTC3314")

    assert sorted(_forumids(c)) == sorted([FORUM_AVISOS, FORUM_DISCUSSAO])


def test_a6_nenhum_nome_de_pessoa_sai_e_a_saida_diz_que_omitiu(disciplinas_brutas):
    """A6 — §3.3: o fórum é conteúdo escrito por terceiros.

    Cada discussão chega com `userfullname` e `usermodifiedfullname`. Nenhum
    deles sai. E omitir calado seria a outra metade do erro: quem lê precisa
    saber que a autoria existe e ficou de fora, senão atribui o aviso a quem
    não o escreveu.
    """
    c = _cliente(
        disciplinas_brutas,
        discussoes={
            FORUM_AVISOS: discussoes_falsas(
                [discussao_falsa(nome_de_quem_postou="Ciclana Maria de Souza")]
            ),
            FORUM_DISCUSSAO: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert "Ciclana" not in r.texto
    assert "Souza" not in r.texto
    assert "quem escreveu" in r.texto.lower()


def test_a18_nenhuma_url_de_anexo_ou_de_foto_sai(disciplinas_brutas):
    """A18 — Invariante 3: `pluginfile.php` sem credencial não abre, e com ela
    exporia o token. Vale para o anexo do post e para a foto de perfil, que a
    resposta traz duas vezes por discussão."""
    c = _cliente(disciplinas_brutas)

    r = av.avisos(c, "PTC3314")

    assert "pluginfile.php" not in r.texto
    assert "http" not in r.texto


# --------------------------------------------------------------------------
# O texto do aviso — que aqui é a resposta, e não gordura de transporte
# --------------------------------------------------------------------------


def test_a7_o_html_do_post_vira_texto_legivel(disciplinas_brutas):
    """A7 — o corpo chega em HTML. Repassá-lo cru gastaria o orçamento com
    marcação e faria quem lê receber `<p dir="ltr">` no meio da frase.

    A entidade também é traduzida: `at&eacute;` lido literalmente é uma palavra
    que não existe em português.
    """
    c = _cliente(disciplinas_brutas)

    r = av.avisos(c, "PTC3314")

    assert "<p" not in r.texto and "</p>" not in r.texto
    assert "<strong>" not in r.texto
    assert "&eacute;" not in r.texto
    assert "até sexta" in r.texto
    assert "adiada" in r.texto, "o texto do aviso não chegou a sair"


def test_a8_texto_longo_e_cortado_e_o_corte_e_declarado(disciplinas_brutas):
    """A8 — Invariante 7 no campo que É a resposta.

    O catálogo (§3.6) registra o fórum como a resposta que menos comprime do
    projeto inteiro, porque ali o payload é o conteúdo. Cortar é decisão de
    custo; cortar calado faria o aviso terminar no meio de uma frase sem que
    quem lê soubesse que faltava metade.
    """
    longo = discussao_falsa(message="<p>" + "palavra " * 400 + "</p>")
    c = _cliente(
        disciplinas_brutas,
        discussoes={
            FORUM_AVISOS: discussoes_falsas([longo]),
            FORUM_DISCUSSAO: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert r.cortados == 1
    assert "…" in r.texto
    assert str(av.TETO_TEXTO) in r.texto, "cortou sem dizer em quanto"
    assert "e-Disciplinas" in r.texto, "cortou sem dizer onde está o resto"


def test_a9_topico_que_nao_coube_no_perpage_e_contado(disciplinas_brutas):
    """A9 — `numdiscussions` diz quantos existem e a resposta traz `perpage`.

    A diferença entre os dois números é o que o Invariante 7 exige declarar, e
    ela custa zero chamada: as duas grandezas já estão em mãos.
    """
    tres = [discussao_falsa(discussionid=910001 + i) for i in range(3)]
    foruns = foruns_falsos(com_discussao=False)
    foruns[0]["numdiscussions"] = 11
    c = _cliente(
        disciplinas_brutas,
        foruns=foruns,
        discussoes={FORUM_AVISOS: discussoes_falsas(tres)},
    )

    r = av.avisos(c, "PTC3314")

    assert "3" in r.texto and "11" in r.texto
    assert r.truncado


def test_a10_teto_de_foruns_por_invocacao_e_declarado(disciplinas_brutas):
    """A10 — uma ida por fórum, e o teto existe pelo mesmo motivo do de
    `ja_entreguei`: latência e log da conta (Invariante 5). O corte é declarado
    com a contagem."""
    muitos = foruns_falsos()
    muitos.extend(
        {
            "id": 302000 + i,
            "cmid": 6373000 + i,
            "course": PTC3314,
            "type": "general",
            "name": f"Fórum {i}",
            "numdiscussions": 1,
        }
        for i in range(av.TETO_FORUNS + 2)
    )
    por_forum = {f["id"]: discussoes_falsas([discussao_falsa()]) for f in muitos}
    c = _cliente(disciplinas_brutas, foruns=muitos, discussoes=por_forum)

    r = av.avisos(c, "PTC3314")

    assert len(_forumids(c)) == av.TETO_FORUNS
    assert r.truncado
    assert str(av.TETO_FORUNS) in r.texto


def test_a5_o_mural_de_avisos_vem_primeiro(disciplinas_brutas):
    """A5 — `type: "news"` é o mural onde só o professor posta, e é ele que
    responde à pergunta. A resposta do Moodle não garante ordem nenhuma; deixar
    a ordem da API decidir faria o aviso do professor sair depois da dúvida de
    um colega quando a disciplina tivesse muitos fóruns."""
    invertido = list(reversed(foruns_falsos()))
    assert invertido[0]["type"] == "general", "a fixture deixou de exercitar a ordem"
    c = _cliente(disciplinas_brutas, foruns=invertido)

    r = av.avisos(c, "PTC3314")

    assert _forumids(c)[0] == FORUM_AVISOS
    assert r.texto.index("Avisos") < r.texto.index("Discussão de Exercícios")


def test_a20_a_data_tem_a_mesma_grafia_de_o_que_vence(disciplinas_brutas):
    """A20 — mesma razão do J18: duas grafias do mesmo instante fazem quem lê as
    duas respostas não reconhecer que é o mesmo dia. `texto.formatar_data` é a
    única porta."""
    from datetime import datetime

    from usp_mcp.moodle.projecao import FUSO_SAO_PAULO
    from usp_mcp.moodle.texto import formatar_data

    quando = 1788910000
    c = _cliente(
        disciplinas_brutas,
        discussoes={
            FORUM_AVISOS: discussoes_falsas(
                [discussao_falsa(created=quando, timemodified=quando)]
            ),
            FORUM_DISCUSSAO: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert formatar_data(datetime.fromtimestamp(quando, FUSO_SAO_PAULO)) in r.texto


# --------------------------------------------------------------------------
# Vazio, erro e cobertura — o que a saída diz quando não tem o que dizer
# --------------------------------------------------------------------------


def test_a11_disciplina_sem_forum_nenhum_diz_por_que_esta_vazia(disciplinas_brutas):
    """A11 — zero fórum é resposta legítima e não pode virar silêncio: "esta
    disciplina não usa fórum" e "eu não consegui ler" têm curas diferentes."""
    c = _cliente(disciplinas_brutas, foruns=[], discussoes={})

    r = av.avisos(c, "PTC3314")

    assert r.vazio_por == "sem_forum"
    assert "não tem nenhum fórum" in r.texto
    assert "mod_forum_get_forum_discussions" not in _funcoes(c)


def test_a12_forum_sem_nenhum_topico_e_caso_proprio(disciplinas_brutas):
    """A12 — o fórum existe e está vazio, que é diferente de não haver fórum.
    Quem lê precisa da distinção: no primeiro caso vale voltar amanhã."""
    c = _cliente(
        disciplinas_brutas,
        foruns=foruns_falsos(sem_contagem=True),
        discussoes={
            FORUM_AVISOS: discussoes_falsas([]),
            FORUM_DISCUSSAO: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert r.vazio_por == "sem_topico"
    assert "nenhum tópico" in r.texto.lower()


def test_a13_warning_da_api_vira_aviso_em_vez_de_sumir(disciplinas_brutas):
    """A13 — mesma regra de `material` e `notas`: o que o Moodle recusou mostrar
    é dito, senão a lista parece completa."""
    c = _cliente(
        disciplinas_brutas,
        discussoes={
            FORUM_AVISOS: discussoes_falsas(com_warning=True),
            FORUM_DISCUSSAO: discussoes_falsas([]),
        },
    )

    r = av.avisos(c, "PTC3314")

    assert "não puderam ser lidos" in r.texto or "não puderam ser lidas" in r.texto


def test_a14_erro_do_cliente_sobe_e_nao_vira_sem_aviso(disciplinas_brutas):
    """A14 — o outro lado do bug do §9 de 28/08: falha de credencial ou de rede
    não pode virar "o professor não avisou nada". As duas têm curas diferentes,
    e a segunda faz quem lê parar de procurar."""

    def _explode(_params):
        raise MoodleIndisponivel("o e-Disciplinas não respondeu")

    c = _cliente(disciplinas_brutas)
    c._respostas["mod_forum_get_forum_discussions"] = _explode

    with pytest.raises(MoodleIndisponivel):
        av.avisos(c, "PTC3314")


def test_a15_a_saida_diz_o_que_o_forum_nao_cobre(disciplinas_brutas):
    """A15 — Invariante 6 na resposta: aviso dado em sala e não postado não
    existe aqui, e o que tem PRAZO é outra ferramenta. Sem isso a lista parece
    a agenda da disciplina."""
    c = _cliente(disciplinas_brutas)

    r = av.avisos(c, "PTC3314")

    assert "o_que_vence" in r.texto
    assert "sala" in r.texto


# --------------------------------------------------------------------------
# A projeção, em bytes
# --------------------------------------------------------------------------


def test_a17_a_projecao_descarta_a_maior_parte_do_payload(disciplinas_brutas):
    """A17 — a razão medida, **contra payload escrito à mão** (ver `conftest`).

    O número não é uma promessa sobre o que o e-Disciplinas devolve: ele mede o
    que a nossa projeção descarta de uma resposta DESTA FORMA. A asserção é
    frouxa de propósito — trava a ordem de grandeza, não o dígito, porque um
    dígito exato sobre payload inventado seria precisão emprestada.

    O fórum é o que menos comprime do projeto (§3.6 do catálogo): aqui o payload
    é o conteúdo, e a razão fica bem abaixo dos 63x do calendário.
    """
    c = _cliente(disciplinas_brutas)

    r = av.avisos(c, "PTC3314")

    cru = len(
        json.dumps(foruns_falsos(), ensure_ascii=False).encode("utf-8")
    ) + 2 * len(
        json.dumps(discussoes_falsas(), ensure_ascii=False).encode("utf-8")
    )
    projetado = len(r.texto.encode("utf-8"))

    assert projetado < cru, "a projeção não reduziu nada"
    assert cru / projetado > 1.5, (
        f"razão de {cru / projetado:.1f}x — a projeção parou de descartar"
    )
