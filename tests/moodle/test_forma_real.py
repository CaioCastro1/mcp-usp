"""F1-F9: nem o dublê monta, nem o código lê, campo que o e-Disciplinas não tem.

A suíte do Moodle monta as respostas com **construtores** (`conftest.py`), e não
com arquivo estático, porque cada teste precisa de um cenário próprio: com
`warning`, sem contagem de discussões, com prorrogação. Isso é bom desenho e
fica como está.

O preço é o que se pagou em 14/09/2026: as ferramentas do P2 nasceram numa
worktree sem token, os construtores foram escritos a partir do formato
documentado do core, e um deles inventou campo. O §9 chegou a registrar que
`notas` descartava `rank`, `maxrank` e `averageformatted` de
`gradereport_overview_get_course_grades` — a resposta real tem **três** campos
por item e nenhum desses existe. O código não dependia deles, então nada
quebrou; o que quebrou foi o que estava escrito, e a razão de projeção saiu
errada por mais do que o dobro.

Estes testes fecham essa porta sem tocar nos construtores. A regra é estreita:

    todo campo que o construtor produz tem de existir na resposta real.

O contrário **não** é exigido. O construtor pode omitir à vontade: o que ele não
monta é o que o teste não precisava, e exigir cobertura total transformaria cada
campo novo do Moodle num vermelho que não diz nada.

F8 e F9 fecham a porta do outro lado, descoberta em 15/09/2026. F1-F6 garantem
que o construtor não INVENTA campo; nada garantia que a PROJEÇÃO não LÊ um. E ela
lia: `projetar_itens` montava o máximo de cada item a partir de `grademax`, que
nenhum dos 20 itens da captura traz. `.get` de chave inexistente devolve `None`,
o renderizador degradava sozinho, a saída nunca mentiu — e por isso ninguém viu.
A regra espelhada é igualmente estreita:

    toda chave que a projeção lê tem de existir na resposta real.

As fixturas são captura real de 15/09/2026, higienizadas pelo §3.3. Elas não são
lidas pelos testes das ferramentas: existem só para esta conferência de forma,
que é o papel que a suíte irmã do Jupiter dá às dela.
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from tests.moodle import conftest as c

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "fixtures" / "moodle"

pytestmark = pytest.mark.contrato


def _real(nome: str):
    caminho = FIXTURES / f"{nome}.json"
    assert caminho.is_file(), (
        f"fixture capturada ausente: {caminho}. Ausência é FALHA e não skip — um "
        "skip aqui deixaria a conferência de forma verde sem ter conferido nada."
    )
    return json.loads(caminho.read_text(encoding="utf-8"))


def _mapa(no, caminho="", fundo=None):
    """`caminho do dicionário -> conjunto de chaves vistas ali`.

    Só entra caminho onde existe um dicionário DE VERDADE. Lista vazia ou `null`
    não geram entrada, e é essa ausência que separa "campo inventado" de "campo
    que esta captura não exercita".
    """
    if fundo is None:
        fundo = {}
    if isinstance(no, dict):
        fundo.setdefault(caminho, set()).update(no)
        for k, v in no.items():
            _mapa(v, f"{caminho}.{k}" if caminho else k, fundo)
    elif isinstance(no, list):
        for v in no:
            _mapa(v, f"{caminho}[]", fundo)
    return fundo


# Caminho que o construtor monta, a captura não exercita, e que é campo legítimo
# do core. Cada entrada precisa dizer POR QUE a captura não alcança — sem isso
# esta lista vira o lugar onde se esconde invenção.
EXCECOES = {
    "submission_status_ec1": {
        "lastattempt.submission.plugins[].editorfields":
            "a entrega do EC-1 é por arquivo: os dois plugins da captura são "
            "`file` e `comments`. `editorfields` só aparece em envio de texto "
            "online, que nenhuma entrega desta conta usa hoje.",
    },
}


def _confere(nome_fixture: str, montado, rotulo: str):
    real = _mapa(_real(nome_fixture))
    meu = _mapa(montado)

    inventados, sem_amostra = [], []
    for pai, chaves in sorted(meu.items()):
        if pai in real:
            perdoados = EXCECOES.get(nome_fixture, {})
            inventados += [
                caminho
                for k in sorted(chaves - real[pai])
                if (caminho := f"{pai}.{k}".lstrip(".")) not in perdoados
            ]
        else:
            sem_amostra.append(pai or "(raiz)")

    assert not inventados, (
        f"{rotulo} monta campo que `{nome_fixture}.json` não tem: {inventados}\n"
        "A fixture é captura real do e-Disciplinas, e o pai desses campos existe "
        "lá com amostra — então a ausência é informação, não falta de dado. "
        "Campo que só existe no dublê faz o teste afirmar forma contra um "
        "dicionário que ele mesmo inventou, e foi assim que o §9 passou a "
        "descrever descarte de campo inexistente.\n"
        "Se o campo existe de verdade e a captura é que está velha, recapture "
        "com `./scripts/capture.sh` e diga isso no §9."
    )
    # Invariante 7 aplicado ao próprio teste: o que ele NÃO conseguiu conferir
    # sai declarado, em vez de passar por conferido.
    return sem_amostra


def test_f1_notas_gerais():
    _confere("grades_overview", c.notas_gerais_falsas([(142036, "8,50")]),
             "notas_gerais_falsas")


def test_f2_itens_de_nota():
    _confere("grade_items_ptc3314", c.itens_de_nota_falsos(), "itens_de_nota_falsos")


def test_f3_status_de_entrega():
    _confere("submission_status_ec1", c.status_de_entrega(), "status_de_entrega")


def test_f4_foruns():
    _confere("forums_ptc3314", c.foruns_falsos(), "foruns_falsos")


def test_f5_discussoes():
    _confere("forum_discussions_avisos", c.discussoes_falsas(), "discussoes_falsas")


def test_f6_mudancas():
    _confere("updates_since_ptc3314", c.mudancas_falsas(), "mudancas_falsas")


def test_f7_a_conferencia_pega_campo_inventado():
    """F7 — sabotagem da própria conferência.

    Sem isto, um `_chaves` quebrado deixaria F1-F6 verdes sem comparar nada, que
    é o falso-verde que estes testes existem para impedir.
    """
    real = _mapa({"grades": [{"courseid": 1, "grade": "8"}]})
    assert real["grades[]"] == {"courseid", "grade"}, "a varredura não desceu na lista"

    montado = _mapa({"grades": [{"courseid": 1, "grade": "8", "rank": 3}]})
    assert montado["grades[]"] - real["grades[]"] == {"rank"}, (
        "a comparação não isolou o campo inventado"
    )

    # E o contrário: lista vazia no real não gera caminho, então não acusa.
    vazio = _mapa({"grades": []})
    assert "grades[]" not in vazio, (
        "lista vazia virou amostra: isso faria a conferência acusar campo que a "
        "captura apenas não exercita"
    )


# --------------------------------------------------------------------------
# O outro lado da regra: o CÓDIGO também não lê campo que a captura não tem
# --------------------------------------------------------------------------


def _chaves_lidas(modulo: str, funcao: str, variavel: str) -> set[str]:
    """Os literais de `<variavel>.get("X")` dentro de `<funcao>`, lidos do fonte.

    Vai ao fonte e não ao comportamento de propósito: `.get` de chave que não
    existe devolve `None` em silêncio, e é justamente esse silêncio que precisa
    virar vermelho. Um teste que só olhasse a SAÍDA veria a degradação correta e
    passaria, que foi o que aconteceu com `grademax` por um dia inteiro.
    """
    fonte = (RAIZ / modulo).read_text(encoding="utf-8")
    corpo = [
        no
        for no in ast.walk(ast.parse(fonte))
        if isinstance(no, ast.FunctionDef) and no.name == funcao
    ]
    assert len(corpo) == 1, f"`{funcao}` não é única em {modulo}: {len(corpo)} achadas"

    return {
        no.args[0].value
        for no in ast.walk(corpo[0])
        if isinstance(no, ast.Call)
        and isinstance(no.func, ast.Attribute)
        and no.func.attr == "get"
        and isinstance(no.func.value, ast.Name)
        and no.func.value.id == variavel
        and no.args
        and isinstance(no.args[0], ast.Constant)
        and isinstance(no.args[0].value, str)
    }


_NOTAS = "usp_mcp/moodle/notas.py"

# `caminho da captura -> (função da projeção, variável que percorre aquele nível)`
LEITURAS = {
    "grade_items_ptc3314": {
        "usergrades[]": ("projetar_itens", "bloco"),
        "usergrades[].gradeitems[]": ("projetar_itens", "item"),
    },
    "grades_overview": {
        "grades[]": ("projetar_visao_geral", "grade"),
    },
}


@pytest.mark.parametrize("nome_fixture", sorted(LEITURAS))
def test_f8_a_projecao_de_notas_nao_le_campo_que_a_captura_nao_tem(nome_fixture):
    """F8 — o espelho de F1-F6, do lado do código.

    O defeito medido em 15/09/2026: a projeção lia `grademax` para preencher o
    "máximo" de cada item e a captura não traz esse campo em nenhum dos 20 itens
    — nem com esse nome nem com outro. Das 26 chaves distintas, `graderaw`,
    `gradeformatted` e `percentageformatted` dizem QUANTO se tirou, e nenhuma diz
    de quanto era. O campo morto foi removido; este teste é o que impede que ele
    volte calado, aqui ou em qualquer chave nova que alguém suponha existir.

    A degradação do renderizador NÃO é a defesa: ela é o que esconde o defeito.
    """
    real = _mapa(_real(nome_fixture))

    inexistentes = {}
    for caminho, (funcao, variavel) in LEITURAS[nome_fixture].items():
        assert caminho in real, (
            f"a captura `{nome_fixture}.json` não tem amostra em `{caminho}`: "
            "sem amostra esta conferência ficaria verde sem conferir nada"
        )
        lidas = _chaves_lidas(_NOTAS, funcao, variavel)
        assert lidas, (
            f"nenhuma chave lida por `{funcao}` via `{variavel}.get(...)` — a "
            "varredura do fonte quebrou, e um verde aqui não vale nada"
        )
        if sobrando := sorted(lidas - real[caminho]):
            inexistentes[f"{funcao}/{variavel} em {caminho}"] = sobrando

    assert not inexistentes, (
        f"a projeção lê de `{nome_fixture}.json` chave que a captura real não "
        f"tem: {inexistentes}\n"
        "O pai dessas chaves existe na captura com amostra, então a ausência é "
        "informação e não falta de dado. `.get` de chave inexistente devolve "
        "`None`, o campo nasce vazio e o renderizador degrada sozinho: o defeito "
        "não aparece na saída, só no que o código promete e não entrega.\n"
        "Se a chave existe de verdade e a captura é que está velha, recapture "
        "com `./scripts/capture.sh` e diga isso no §9."
    )


def test_f9_a_conferencia_pega_leitura_de_campo_inexistente():
    """F9 — sabotagem de F8, pelo mesmo motivo de F7.

    Uma varredura de fonte quebrada devolve conjunto vazio, e conjunto vazio não
    sobra nada em comparação nenhuma: F8 ficaria verde sem ter lido o código.
    """
    lidas = _chaves_lidas(_NOTAS, "projetar_itens", "item")
    assert "gradeformatted" in lidas and "gradeishidden" in lidas, (
        f"a varredura não achou as leituras que existem em `projetar_itens`: {lidas}"
    )
    assert "grademax" not in lidas, (
        "`grademax` voltou a ser lido: a captura de 15/09 não tem esse campo em "
        "item nenhum, e o renderizador esconde a falta em vez de acusá-la"
    )

    # E o isolamento: uma variável que aquela função não percorre não traz chave
    # emprestada de outra, o que faria F8 acusar campo no caminho errado.
    assert not _chaves_lidas(_NOTAS, "projetar_itens", "grade"), (
        "a varredura não separou por variável: `grade` é de `projetar_visao_geral`"
    )
